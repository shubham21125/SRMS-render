from contextvars import ContextVar

# Context variable to hold audit info
audit_context = ContextVar("audit_context", default=None)

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        data = {
            "user": request.user if (request.user and request.user.is_authenticated) else None,
            "ip_address": ip,
        }
        
        token = audit_context.set(data)
        try:
            response = self.get_response(request)
        finally:
            audit_context.reset(token)
            
        return response
