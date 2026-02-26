import time
import logging
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
from django.conf import settings

logger = logging.getLogger('security')

def rate_limit(key_func, rate='5/m', block_time=300):
    """
    Rate limiting decorator.
    
    Args:
        key_func: Function to generate unique key for rate limiting
        rate: Rate limit string (e.g., '5/m' = 5 requests per minute)
        block_time: Time in seconds to block user after rate limit exceeded
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Parse rate limit
            try:
                limit, period = rate.split('/')
                limit = int(limit)
                period_map = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                period_seconds = period_map[period[0].lower()]
            except (ValueError, KeyError):
                limit, period_seconds = 5, 60  # Default: 5 requests per minute
            
            # Generate cache key
            cache_key = f"rate_limit:{key_func(request)}:{view_func.__name__}"
            
            # Check if user is blocked
            block_key = f"{cache_key}:blocked"
            if cache.get(block_key):
                return JsonResponse(
                    {
                        'error': 'Too many requests',
                        'message': 'You have made too many requests. Please wait a while before trying again.'
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            if request_count >= limit:
                # Block user
                cache.set(block_key, True, block_time)
                logger.warning(
                    f"Rate limit exceeded for {key_func(request)} on {view_func.__name__}. "
                    f"Blocked for {block_time} seconds."
                )
                return JsonResponse(
                    {
                        'error': 'Too many requests',
                        'message': 'You have reached the maximum number of requests allowed. Please wait before trying again.'
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Increment request count
            cache.set(cache_key, request_count + 1, period_seconds)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def ip_rate_limit(rate='100/m', block_time=900):
    """Rate limit by IP address."""
    def key_func(request):
        # Get client IP from various possible locations
        ip = None
        if hasattr(request, 'META'):
            ip = request.META.get('REMOTE_ADDR')
            if not ip:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('HTTP_X_REAL_IP')
        if not ip:
            ip = 'unknown'
        return ip
    
    return rate_limit(key_func=key_func, rate=rate, block_time=block_time)


def user_rate_limit(rate='50/m', block_time=600):
    """Rate limit by authenticated user."""
    def key_func(request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Get client IP for anonymous users
        ip = None
        if hasattr(request, 'META'):
            ip = request.META.get('REMOTE_ADDR')
            if not ip:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('HTTP_X_REAL_IP')
        if not ip:
            ip = 'unknown'
        return f"anon:{ip}"
    
    return rate_limit(key_func=key_func, rate=rate, block_time=block_time)


def auth_rate_limit(rate='5/m', block_time=900):
    """Stricter rate limit for authentication endpoints."""
    def key_func(request):
        # Get client IP from various possible locations
        ip = None
        if hasattr(request, 'META'):
            ip = request.META.get('REMOTE_ADDR')
            if not ip:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('HTTP_X_REAL_IP')
        if not ip:
            ip = 'unknown'
        return f"auth:{ip}"
    
    return rate_limit(key_func=key_func, rate=rate, block_time=block_time)


def sensitive_operation_rate_limit(rate='10/h', block_time=3600):
    """Very strict rate limit for sensitive operations."""
    def key_func(request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"sensitive:{request.user.id}"
        
        # Get client IP for anonymous users
        ip = None
        if hasattr(request, 'META'):
            ip = request.META.get('REMOTE_ADDR')
            if not ip:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('HTTP_X_REAL_IP')
        if not ip:
            ip = 'unknown'
        return f"sensitive:anon:{ip}"
    
    return rate_limit(key_func=key_func, rate=rate, block_time=block_time)
