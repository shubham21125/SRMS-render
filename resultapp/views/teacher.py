import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from resultapp.models import Teacher, Student, Result, Class, Subject
from .decorators import role_required
from .students import paginate
from .auth import resolve_teacher

logger = logging.getLogger(__name__)


@role_required('teacher')
def teacher_dashboard(request):
    teacher = resolve_teacher(request.user)
    assigned_classes = teacher.assigned_classes.all()
    assigned_subjects = teacher.assigned_subjects.all()
    student_count = Student.objects.filter(student_class__in=assigned_classes).count()
    result_count = Result.objects.filter(
        student_class__in=assigned_classes,
        subject__in=assigned_subjects
    ).count()
    recent_results = Result.objects.filter(
        student_class__in=assigned_classes
    ).select_related('student', 'subject').order_by('-posting_date')[:6]
    return render(request, 'teacher/dashboard.html', {
        'teacher': teacher,
        'assigned_classes': assigned_classes,
        'assigned_subjects': assigned_subjects,
        'student_count': student_count,
        'result_count': result_count,
        'recent_results': recent_results,
    })


@role_required('teacher')
def teacher_students(request):
    teacher = resolve_teacher(request.user)
    assigned_classes = teacher.assigned_classes.all()
    students = Student.objects.filter(
        student_class__in=assigned_classes
    ).select_related('student_class').order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        students = students.filter(
            Q(name__icontains=q) | Q(roll_id__icontains=q) | Q(email__icontains=q)
        )
    page_obj = paginate(request, students)
    return render(request, 'teacher/students.html', {
        'teacher': teacher,
        'students': page_obj,
        'page_obj': page_obj,
        'q': q,
        'assigned_classes': assigned_classes,
    })


@role_required('teacher')
def teacher_results(request):
    teacher = resolve_teacher(request.user)
    assigned_classes = teacher.assigned_classes.all()
    assigned_subjects = teacher.assigned_subjects.all()
    results = Result.objects.filter(
        student_class__in=assigned_classes,
        subject__in=assigned_subjects
    ).select_related('student', 'subject', 'student_class').order_by('student__name')
    q = request.GET.get('q', '').strip()
    if q:
        results = results.filter(
            Q(student__name__icontains=q) | Q(student__roll_id__icontains=q) |
            Q(subject__subject_name__icontains=q)
        )
    page_obj = paginate(request, results)
    return render(request, 'teacher/results.html', {
        'teacher': teacher,
        'results': page_obj,
        'page_obj': page_obj,
        'q': q,
        'assigned_subjects': assigned_subjects,
    })


@login_required
def create_teacher(request):
    """Admin creates and manages teacher accounts."""
    error = None
    classes = Class.objects.all().order_by('class_name')
    subjects = Subject.objects.all().order_by('subject_name')

    if request.method == 'POST':
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        username     = request.POST.get('username', '').strip()
        email        = request.POST.get('email', '').strip()
        password     = request.POST.get('password', '').strip()
        confirm_pass = request.POST.get('confirm_password', '').strip()
        phone        = request.POST.get('phone', '').strip()
        department   = request.POST.get('department', '').strip()
        class_ids    = request.POST.getlist('assigned_classes')
        subject_ids  = request.POST.getlist('assigned_subjects')

        if not all([first_name, username, email, password, confirm_pass]):
            error = 'All required fields must be filled.'
        elif password != confirm_pass:
            error = 'Passwords do not match.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif User.objects.filter(username=username).exists():
            error = f'Username "{username}" is already taken.'
        elif User.objects.filter(email=email).exists():
            error = f'An account with email "{email}" already exists.'
        else:
            try:
                new_user = User.objects.create_user(
                    username=username, email=email, password=password,
                    first_name=first_name, last_name=last_name,
                )
                teacher = Teacher.objects.create(
                    user=new_user, phone=phone, department=department,
                )
                if class_ids:
                    teacher.assigned_classes.set(Class.objects.filter(id__in=class_ids))
                if subject_ids:
                    teacher.assigned_subjects.set(Subject.objects.filter(id__in=subject_ids))
                messages.success(request, f'Teacher account created for {first_name} ({username}).')
                return redirect('create_teacher')
            except Exception:
                logger.exception("Failed to create teacher account")
                error = 'Could not create teacher. An unexpected error occurred.'

    teachers = Teacher.objects.select_related('user').order_by('user__first_name')
    return render(request, 'teacher/create_teacher.html', {
        'error': error,
        'teachers': teachers,
        'classes': classes,
        'subjects': subjects,
    })


@login_required
def delete_teacher(request, teacher_id):
    if request.method == 'POST':
        try:
            teacher_obj = get_object_or_404(Teacher, id=teacher_id)
            name = teacher_obj.user.get_full_name() or teacher_obj.user.username
            teacher_obj.user.delete()
            messages.success(request, f'Teacher account "{name}" deleted.')
        except Exception:
            logger.exception("Failed to delete teacher %s", teacher_id)
            messages.error(request, 'Could not delete teacher. An unexpected error occurred.')
    return redirect('create_teacher')
