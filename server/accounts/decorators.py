from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


def _redirect_to_login(request, message):
    """
    Redirect the user to the appropriate login page with an error message.
    - /dashboard/* should use the dashboard login
    - everything else falls back to Django admin login
    """
    messages.error(request, message)
    if (request.path or "").startswith("/dashboard/"):
        login_url = reverse("dashboard:login")
    else:
        login_url = reverse("admin:login")
    return redirect(f"{login_url}?next={request.path}")


def role_required(allowed_roles=None, require_staff_flag=False):
    """
    Generic role-based access decorator.
    
    - allowed_roles: iterable of role strings (e.g. ['admin', 'staff'])
    - require_staff_flag: additionally require user.is_staff to be True
    """
    allowed_roles = set(allowed_roles or [])

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return _redirect_to_login(request, "Please log in to access the dashboard.")

            if allowed_roles and getattr(user, "role", None) not in allowed_roles:
                return _redirect_to_login(request, "You do not have permission to access this area.")

            if require_staff_flag and not user.is_staff:
                return _redirect_to_login(request, "You do not have permission to access this area.")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """
    Require an admin user for access to dashboard views.
    Treat both role='admin' and is_staff superusers as admins.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return _redirect_to_login(request, "Please log in to access the dashboard.")

        # Allow either explicit admin role or standard Django staff superusers
        is_admin_role = getattr(user, "role", None) == "admin"
        if not (is_admin_role or user.is_staff):
            return _redirect_to_login(request, "You do not have permission to access the admin dashboard.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def staff_required(view_func):
    """
    Require a staff or admin user. This is useful for views that should
    be available to non-superuser staff members.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return _redirect_to_login(request, "Please log in to access this page.")

        role = getattr(user, "role", None)
        if role not in {"staff", "admin"} and not user.is_staff:
            return _redirect_to_login(request, "You do not have permission to access this page.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def superuser_required(view_func):
    """
    Restrict access to Django superusers only.
    Useful for sensitive management views like user and staff administration.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return _redirect_to_login(request, "Please log in to access this page.")

        if not user.is_superuser:
            return _redirect_to_login(request, "You do not have permission to manage users and staff.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

