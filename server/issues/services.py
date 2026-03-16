from datetime import timedelta
from django.utils import timezone
from .models import Issue, SLARule, MaintenanceWindow

def calculate_sla_deadline(issue, start_time=None):
    if start_time is None:
        start_time = timezone.now()
        
    try:
        rule = SLARule.objects.get(category=issue.category)
        duration_hours = rule.response_time_hours
    except SLARule.DoesNotExist:
        # Default fallback if not defined based on categories
        defaults = {
            'safety': 24,
            'electrical': 48,
            'plumbing': 48,
            'structural': 72,
            'it-infrastructure': 48,
            'cleanliness': 72,
            'equipment': 120,
            'facilities': 120,
            'maintenance': 120,
            'other': 120,
        }
        duration_hours = defaults.get(issue.category, 120)
        
    # If acknowledged during an active maintenance window, start SLA clock from when maintenance ends
    active_maintenance = MaintenanceWindow.objects.filter(
        is_active=True,
        is_cancelled=False,
        actual_end__isnull=True,
        scheduled_start__lte=start_time,
        scheduled_end__gte=start_time
    ).first()
    
    if active_maintenance:
        start_time = active_maintenance.scheduled_end
        
    return start_time + timedelta(hours=duration_hours)
