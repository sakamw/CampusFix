import logging
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
import re

logger = logging.getLogger('security')

class SecurityHeadersMiddleware:
    """Add security headers to all responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        
        return response


class InputValidationMiddleware:
    """Validate and sanitize input data."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Patterns for potentially malicious content (updated for better accuracy)
        self.malicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'eval\s*\(',   # eval() calls
            r'expression\s*\(',  # CSS expressions
            r'vbscript:',   # VBScript URLs
            r'data:text/html',  # Data URLs with HTML
        ]
    
    def __call__(self, request):
        # Skip validation for safe endpoints
        safe_paths = ['/health/', '/metrics/', '/api/notifications/', '/api/auth/', '/api/issues/']
        if any(request.path.startswith(path) for path in safe_paths):
            return self.get_response(request)
        
        # Validate request data
        if hasattr(request, 'body') and request.body:
            try:
                body_str = request.body.decode('utf-8')
                # Only check for actual malicious patterns, not common HTML attributes
                dangerous_patterns = [
                    r'<script[^>]*>.*?</script>',  # Script tags
                    r'javascript:',  # JavaScript URLs
                    r'eval\s*\(',   # eval() calls
                    r'expression\s*\(',  # CSS expressions
                    r'vbscript:',   # VBScript URLs
                    r'data:text/html',  # Data URLs with HTML
                ]
                
                for pattern in dangerous_patterns:
                    if re.search(pattern, body_str, re.IGNORECASE | re.DOTALL):
                        logger.warning(
                            f"Potentially malicious input detected from {request.META.get('REMOTE_ADDR')}: "
                            f"Path: {request.path}, Pattern: {pattern}"
                        )
                        return JsonResponse(
                            {
                                'error': 'Invalid input detected',
                                'message': 'The request contains potentially malicious content and has been blocked for security reasons.'
                            }, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
            except UnicodeDecodeError:
                pass
        
        return self.get_response(request)


class AuditLoggingMiddleware:
    """Log security-relevant events."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request details
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'method': request.method,
            'path': request.path,
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        # Add user info if authenticated
        try:
            if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
                log_data['user_id'] = request.user.id
                log_data['user_email'] = request.user.email
        except AttributeError:
            # User not authenticated or middleware not properly loaded
            pass
        
        response = self.get_response(request)
        
        # Log response status
        log_data['status_code'] = response.status_code
        
        # Log security-relevant events
        if self._is_security_event(request, response):
            logger.info(f"Security Event: {log_data}")
        
        return response
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def _is_security_event(self, request, response):
        """Determine if this is a security-relevant event."""
        security_paths = ['/login', '/logout', '/register', '/password-reset']
        security_methods = ['POST', 'PUT', 'DELETE']
        
        return (
            response.status_code >= 400 or
            any(request.path.startswith(path) for path in security_paths) or
            request.method in security_methods
        )
