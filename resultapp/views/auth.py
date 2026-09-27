import logging
import urllib.parse
import urllib.request
import json
import secrets
import random
import time

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail

from resultapp.models import Teacher, Parent, Student
from .decorators import role_required
from .parent import resolve_portal_viewer

logger = logging.getLogger(__name__)

from django_ratelimit.decorators import ratelimit

def ip_username_key(group, request):
    ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    username = request.POST.get('username') or request.POST.get('email') or request.POST.get('otp') or 'anonymous'
    return f"{ip}:{username}"


_GOOGLE_AUTH_URL  = 'https://accounts.google.com/o/oauth2/v2/auth'
_GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
_GOOGLE_USER_URL  = 'https://www.googleapis.com/oauth2/v3/userinfo'


@ratelimit(key=ip_username_key, rate='5/10m', method='POST', block=False)
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    error = None
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            error = "Too many login attempts. Please try again after 10 minutes."
            return render(request, 'admin_login.html', {'error': error})
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            error = "Invalid credentials or not authorized."
    return render(request, 'admin_login.html', {'error': error})


def admin_logout(request):
    logout(request)
    return redirect('admin-login')


def resolve_teacher(user):
    """Return the Teacher profile for a user, or None."""
    return Teacher.objects.filter(user=user).select_related('user').first()


@ratelimit(key=ip_username_key, rate='5/10m', method='POST', block=False)
def login_page(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        if Teacher.objects.filter(user=request.user).exists():
            return redirect('teacher_dashboard')
        student, _parent = resolve_portal_viewer(request.user)
        if student is not None:
            return redirect('parent_dashboard')

    error = None
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            error = "Too many failed login attempts. Please try again after 10 minutes."
            return render(request, 'login.html', {'error': error})
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            elif Teacher.objects.filter(user=user).exists():
                login(request, user)
                messages.success(request, f'Welcome, {user.get_full_name() or user.username}!')
                return redirect('teacher_dashboard')
            else:
                student, _parent = resolve_portal_viewer(user)
                if student is not None:
                    login(request, user)
                    messages.success(request, f'Welcome {user.get_full_name()}!')
                    return redirect('parent_dashboard')
                else:
                    error = 'This account is not authorised to access the portal.'
        else:
            error = 'Invalid username or password.'

    return render(request, 'login.html', {'error': error})


def admin_google_login(request):
    """Redirect the admin browser to Google's consent screen."""
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    request.session.save()

    params = {
        'client_id':     settings.GOOGLE_OAUTH2_CLIENT_ID,
        'redirect_uri':  settings.GOOGLE_OAUTH2_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'openid email profile',
        'state':         state,
        'access_type':   'online',
        'prompt':        'select_account',
    }
    url = _GOOGLE_AUTH_URL + '?' + urllib.parse.urlencode(params)
    return redirect(url)


def admin_google_callback(request):
    """Handle the OAuth2 callback from Google."""
    state_in_session = request.session.pop('google_oauth_state', None)
    state_in_request = request.GET.get('state', '')

    if state_in_session and state_in_session != state_in_request:
        return render(request, 'login.html', {
            'error': 'Invalid OAuth state. Please try again.'
        })

    code = request.GET.get('code')
    if not code:
        error_desc = request.GET.get('error_description', request.GET.get('error', 'No code returned.'))
        return render(request, 'login.html', {'error': f'Google login failed: {error_desc}'})

    token_data = urllib.parse.urlencode({
        'code':          code,
        'client_id':     settings.GOOGLE_OAUTH2_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        'redirect_uri':  settings.GOOGLE_OAUTH2_REDIRECT_URI,
        'grant_type':    'authorization_code',
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            _GOOGLE_TOKEN_URL,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_json = json.loads(resp.read().decode('utf-8'))
    except Exception:
        logger.exception("Failed to fetch token from Google during callback")
        return render(request, 'login.html', {
            'error': 'Google authentication failed. Please try again.'
        })

    access_token = token_json.get('access_token')
    if not access_token:
        return render(request, 'login.html', {
            'error': 'Google did not return an access token.'
        })

    try:
        user_req = urllib.request.Request(
            _GOOGLE_USER_URL,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urllib.request.urlopen(user_req, timeout=10) as resp:
            user_info = json.loads(resp.read().decode('utf-8'))
    except Exception:
        logger.exception("Failed to fetch user info from Google during callback")
        return render(request, 'login.html', {
            'error': 'Google authentication failed. Please try again.'
        })

    google_email = user_info.get('email', '').lower().strip()
    google_name  = user_info.get('name', '')
    email_verified = user_info.get('email_verified', False)

    if not google_email or not email_verified:
        return render(request, 'login.html', {
            'error': 'Google account email is not verified. Please verify your Google account first.'
        })

    allowed_raw = getattr(settings, 'GOOGLE_ADMIN_ALLOWED_EMAILS', '')
    allowed_admins = {e.strip().lower() for e in allowed_raw.split(',') if e.strip()} if allowed_raw else set()

    existing_user = User.objects.filter(email__iexact=google_email).first()
    is_admin_email = google_email in allowed_admins or (existing_user and existing_user.is_superuser)

    if is_admin_email:
        user = existing_user
        if user is not None and not user.is_superuser:
            return render(request, 'login.html', {
                'error': f'The account "{google_email}" exists but does not have admin privileges.'
            })
        if user is None:
            username_base = google_email.split('@')[0]
            username = username_base
            counter  = 1
            while User.objects.filter(username=username).exists():
                username = f'{username_base}{counter}'
                counter += 1
            name_parts = google_name.split(' ', 1)
            user = User.objects.create_superuser(
                username=username,
                email=google_email,
                password=None,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
            )

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return redirect('admin_dashboard')

    if existing_user and Parent.objects.filter(user=existing_user).exists():
        existing_user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, existing_user)
        messages.success(request, f'Welcome {existing_user.get_full_name()}!')
        return redirect('parent_dashboard')

    if existing_user and Student.objects.filter(user=existing_user).exists():
        existing_user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, existing_user)
        messages.success(request, f'Welcome {existing_user.get_full_name() or existing_user.username}!')
        return redirect('parent_dashboard')

    unlinked_student = Student.objects.filter(email__iexact=google_email, user__isnull=True).first()
    if unlinked_student:
        if existing_user is None:
            username_base = google_email.split('@')[0]
            username = username_base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{username_base}{counter}'
                counter += 1
            name_parts = google_name.split(' ', 1) if google_name else [unlinked_student.name, '']
            existing_user = User.objects.create_user(
                username=username,
                email=google_email,
                password=None,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
            )
        unlinked_student.user = existing_user
        unlinked_student.save(update_fields=['user'])

        existing_user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, existing_user)
        messages.success(request, f'Welcome {unlinked_student.name}!')
        return redirect('parent_dashboard')

    return render(request, 'login.html', {
        'error': f'The Google account "{google_email}" is not linked to any admin, parent or '
                  'student record in SRMS. Please contact the administrator.'
    })


def parent_login(request):
    if request.user.is_authenticated:
        if Parent.objects.filter(user=request.user).exists():
            return redirect('parent_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if Parent.objects.filter(user=user).exists():
                login(request, user)
                messages.success(request, f'Welcome {user.get_full_name()}!')
                return redirect('parent_dashboard')
            else:
                messages.error(request, 'Invalid credentials.')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'login.html')


def parent_logout(request):
    logout(request)
    return redirect('login')


def teacher_logout(request):
    logout(request)
    return redirect('login')


@login_required
def change_password(request):
    if request.method == 'POST':
        old = request.POST.get('old_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        if new != confirm:
            messages.error(request, "New password and confirm password do not match.")
            return redirect('change_password')

        user = authenticate(username=request.user.username, password=old)
        if user:
            user.set_password(new)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('change_password')
        else:
            messages.error(request, "Old password is incorrect.")

    return render(request, 'change_password.html')


@ratelimit(key=ip_username_key, rate='5/10m', method='POST', block=False)
def admin_forgot_password(request):
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, "Too many password reset requests. Please try again after 10 minutes.")
            return render(request, 'admin_forgot_password.html')
        email = request.POST.get('email')
        user = User.objects.filter(email=email, is_superuser=True).first()
        if user:
            otp = str(random.randint(100000, 999999))
            request.session['reset_email'] = email
            request.session['reset_otp'] = otp
            request.session['reset_otp_expiry'] = time.time() + 600

            try:
                send_mail(
                    subject='Admin Password Reset OTP - SRMS',
                    message=(
                        f'Hello Admin,\n\n'
                        f'You requested to reset your password. Your 6-digit OTP is:\n\n'
                        f'   {otp}\n\n'
                        f'This OTP is valid for 10 minutes. If you did not request this, please ignore this email.\n\n'
                        f'Regards,\nSRMS Portal'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, "A 6-digit OTP has been sent to your email address.")
                return redirect('admin_verify_otp')
            except Exception:
                logger.exception("Failed to send admin forgot password OTP email")
                messages.error(request, "Failed to send email. Please contact support or try again.")
        else:
            messages.error(request, "No admin user found with this email address.")

    return render(request, 'admin_forgot_password.html')


@ratelimit(key=ip_username_key, rate='5/10m', method='POST', block=False)
def admin_verify_otp(request):
    reset_email = request.session.get('reset_email')
    reset_otp = request.session.get('reset_otp')
    reset_otp_expiry = request.session.get('reset_otp_expiry')

    if not reset_email or not reset_otp or not reset_otp_expiry:
        messages.error(request, "Session expired or invalid. Please start again.")
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, "Too many OTP verification attempts. Please try again after 10 minutes.")
            return render(request, 'admin_verify_otp.html')
        otp_entered = request.POST.get('otp')

        if time.time() > reset_otp_expiry:
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect('admin_forgot_password')

        if otp_entered == reset_otp:
            request.session['otp_verified'] = True
            messages.success(request, "OTP verified successfully. Please set a new password.")
            return redirect('admin_reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'admin_verify_otp.html')


def admin_reset_password(request):
    if not request.session.get('otp_verified') or not request.session.get('reset_email'):
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect('admin_forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('admin_reset_password')

        email = request.session.get('reset_email')
        user = User.objects.filter(email=email, is_superuser=True).first()
        if user:
            user.set_password(new_password)
            user.save()

            request.session.pop('reset_email', None)
            request.session.pop('reset_otp', None)
            request.session.pop('reset_otp_expiry', None)
            request.session.pop('otp_verified', None)

            messages.success(request, "Password reset successfully. You can now log in.")
            return redirect('admin-login')
        else:
            messages.error(request, "User not found.")
            return redirect('admin_forgot_password')

    return render(request, 'admin_reset_password.html')


@role_required('parent')
def parent_change_password(request):
    student = request.viewer_student
    parent = request.viewer_parent
    error = success = None
    if request.method == 'POST':
        current  = request.POST.get('current_password', '')
        new_pw   = request.POST.get('new_password', '')
        confirm  = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            error = 'Current password is incorrect.'
        elif len(new_pw) < 8:
            error = 'New password must be at least 8 characters.'
        elif new_pw != confirm:
            error = 'New passwords do not match.'
        elif current == new_pw:
            error = 'New password must be different from current password.'
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            success = 'Password changed successfully!'

    return render(request, 'parent/change_password.html', {
        'parent':  parent,
        'student': student,
        'error':   error,
        'success': success,
    })
