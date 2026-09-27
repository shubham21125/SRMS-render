from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(role):
    """
    Decorator that checks user role.
    Allowed roles: 'admin', 'teacher', 'parent'
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if role == 'admin':
                if not request.user.is_superuser:
                    messages.error(request, 'You do not have admin access.')
                    return redirect('login')
            
            elif role == 'teacher':
                from resultapp.models import Teacher
                if not Teacher.objects.filter(user=request.user).exists():
                    messages.error(request, 'You do not have teacher access.')
                    return redirect('login')
            
            elif role == 'parent':
                from .parent import resolve_portal_viewer
                student, parent = resolve_portal_viewer(request.user)
                if student is None:
                    messages.error(request, 'No student/parent profile is linked to this account.')
                    return redirect('login')
                # Cache on the request object for easy usage inside views
                request.viewer_student = student
                request.viewer_parent = parent
                
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
