import logging
from django.shortcuts import render
from django.utils import timezone
from issues.models import MaintenanceWindow

logger = logging.getLogger(__name__)

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow superusers, /admin/, /static/, /media/ mapped paths bypass
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        now = timezone.now()
        active_window = MaintenanceWindow.objects.filter(
            is_active=True,
            is_cancelled=False,
            actual_end__isnull=True,
            scheduled_start__lte=now,
            scheduled_end__gte=now
        ).first()

        if active_window:
            user = getattr(request, 'user', None)
            if user and user.is_authenticated and user.is_superuser:
                # Superusers bypass maintenance mode
                return self.get_response(request)

            # Show maintenance page
            response = render(request, "maintenance.html", {"maintenance_window": active_window})
            response.status_code = 503
            return response

        return self.get_response(request)
