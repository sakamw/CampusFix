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
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
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


class PathBasedSessionMiddleware:
    """
    Isolate sessions between /admin/ and /dashboard/ by rewriting the session cookie.

    We keep Django's built-in `django.contrib.sessions.middleware.SessionMiddleware`
    enabled (required by Django admin), but we:
    - ensure /admin/* only uses ADMIN_SESSION_COOKIE_NAME
    - ensure /dashboard/* only uses DASHBOARD_SESSION_COOKIE_NAME
    - rename any `Set-Cookie` for SESSION_COOKIE_NAME to the path-specific cookie
      and scope it to the matching path.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _cookie_name_for_request(self, request):
        path = request.path or "/"
        if path.startswith("/admin/"):
            return getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")
        if path.startswith("/dashboard/"):
            return getattr(settings, "DASHBOARD_SESSION_COOKIE_NAME", "dashboard_sessionid")
        return settings.SESSION_COOKIE_NAME

    def _csrf_cookie_name_for_request(self, request):
        path = request.path or "/"
        if path.startswith("/admin/"):
            return getattr(settings, "ADMIN_CSRF_COOKIE_NAME", "admin_csrftoken")
        if path.startswith("/dashboard/"):
            return getattr(settings, "DASHBOARD_CSRF_COOKIE_NAME", "dashboard_csrftoken")
        return settings.CSRF_COOKIE_NAME

    def __call__(self, request):
        desired_cookie = self._cookie_name_for_request(request)
        request._session_cookie_name = desired_cookie  # used later for response rewriting
        desired_csrf_cookie = self._csrf_cookie_name_for_request(request)
        request._csrf_cookie_name = desired_csrf_cookie

        # Ensure /admin and /dashboard NEVER fall back to the default session cookie.
        if (request.path or "").startswith(("/admin/", "/dashboard/")):
            request.COOKIES = dict(request.COOKIES)
            if settings.SESSION_COOKIE_NAME in request.COOKIES:
                del request.COOKIES[settings.SESSION_COOKIE_NAME]

            if desired_cookie in request.COOKIES:
                # Present the desired cookie under Django's default name so
                # SessionMiddleware will load it.
                request.COOKIES[settings.SESSION_COOKIE_NAME] = request.COOKIES[desired_cookie]

            # Do the same trick for CSRF so /admin and /dashboard each have their own CSRF secret.
            if settings.CSRF_COOKIE_NAME in request.COOKIES:
                del request.COOKIES[settings.CSRF_COOKIE_NAME]
            if desired_csrf_cookie in request.COOKIES:
                request.COOKIES[settings.CSRF_COOKIE_NAME] = request.COOKIES[desired_csrf_cookie]

        # For /api/ paths: if the default session cookie is absent but a
        # dashboard session cookie is present, the request likely originates
        # from the server-rendered dashboard.  Remap so Django recognises it.
        elif (request.path or "").startswith("/api/"):
            dashboard_session = getattr(settings, "DASHBOARD_SESSION_COOKIE_NAME", "dashboard_sessionid")
            dashboard_csrf = getattr(settings, "DASHBOARD_CSRF_COOKIE_NAME", "dashboard_csrftoken")
            request.COOKIES = dict(request.COOKIES)

            if settings.SESSION_COOKIE_NAME not in request.COOKIES and dashboard_session in request.COOKIES:
                request.COOKIES[settings.SESSION_COOKIE_NAME] = request.COOKIES[dashboard_session]

            if settings.CSRF_COOKIE_NAME not in request.COOKIES and dashboard_csrf in request.COOKIES:
                request.COOKIES[settings.CSRF_COOKIE_NAME] = request.COOKIES[dashboard_csrf]

        response = self.get_response(request)

        # Rename any Set-Cookie made by SessionMiddleware from the default name
        # to the path-specific cookie name.
        desired_cookie = getattr(request, "_session_cookie_name", settings.SESSION_COOKIE_NAME)
        if desired_cookie != settings.SESSION_COOKIE_NAME and settings.SESSION_COOKIE_NAME in response.cookies:
            old = response.cookies.pop(settings.SESSION_COOKIE_NAME)

            response.cookies[desired_cookie] = old.value
            new = response.cookies[desired_cookie]
            for k, v in old.items():
                new[k] = v

            # Scope cookie to its area (defense in depth).
            if (request.path or "").startswith("/admin/"):
                new["path"] = "/admin/"

        # Rename any Set-Cookie made by CsrfViewMiddleware from the default name
        # to the path-specific cookie name and scope it to the matching path.
        desired_csrf_cookie = getattr(request, "_csrf_cookie_name", settings.CSRF_COOKIE_NAME)
        if desired_csrf_cookie != settings.CSRF_COOKIE_NAME and settings.CSRF_COOKIE_NAME in response.cookies:
            old = response.cookies.pop(settings.CSRF_COOKIE_NAME)

            response.cookies[desired_csrf_cookie] = old.value
            new = response.cookies[desired_csrf_cookie]
            for k, v in old.items():
                new[k] = v

            if (request.path or "").startswith("/admin/"):
                new["path"] = "/admin/"

        return response
