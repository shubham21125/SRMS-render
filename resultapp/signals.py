from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.cache import cache

from .models import Student, Result, AuditLog
from .middleware import audit_context

@receiver(post_save, sender=Student)
def log_student_save(sender, instance, created, **kwargs):
    ctx = audit_context.get()
    actor = ctx.get("user") if ctx else None
    ip = ctx.get("ip_address") if ctx else None
    action = 'CREATE' if created else 'UPDATE'
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_model='Student',
        target_id=str(instance.roll_id),
        ip_address=ip
    )
    # Invalidate analytics cache
    cache.delete('admin_analytics_data')

@receiver(post_delete, sender=Student)
def log_student_delete(sender, instance, **kwargs):
    ctx = audit_context.get()
    actor = ctx.get("user") if ctx else None
    ip = ctx.get("ip_address") if ctx else None
    AuditLog.objects.create(
        actor=actor,
        action='DELETE',
        target_model='Student',
        target_id=str(instance.roll_id),
        ip_address=ip
    )
    # Invalidate analytics cache
    cache.delete('admin_analytics_data')

@receiver(post_save, sender=Result)
def log_result_save(sender, instance, created, **kwargs):
    # Log audit record
    ctx = audit_context.get()
    actor = ctx.get("user") if ctx else None
    ip = ctx.get("ip_address") if ctx else None
    action = 'CREATE' if created else 'UPDATE'
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_model='Result',
        target_id=str(instance.id),
        ip_address=ip
    )
    # Invalidate analytics cache
    cache.delete('admin_analytics_data')

@receiver(post_delete, sender=Result)
def log_result_delete(sender, instance, **kwargs):
    # Log audit record
    ctx = audit_context.get()
    actor = ctx.get("user") if ctx else None
    ip = ctx.get("ip_address") if ctx else None
    AuditLog.objects.create(
        actor=actor,
        action='DELETE',
        target_model='Result',
        target_id=str(instance.id),
        ip_address=ip
    )
    # Invalidate analytics cache
    cache.delete('admin_analytics_data')
