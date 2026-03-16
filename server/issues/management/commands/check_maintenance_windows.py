import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from issues.models import MaintenanceWindow, Issue
from notifications.services import NotificationService
from accounts.models import User

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Manage maintenance windows and issue SLA deadlines/reminders"

    def handle(self, *args, **options):
        now = timezone.now()

        # 1. Handle Maintenance Windows Activation/Deactivation
        maintenance_windows = MaintenanceWindow.objects.filter(is_cancelled=False)

        for window in maintenance_windows:
            # Check for exactly 48h and 24h warnings
            if not window.is_active and window.actual_end is None:
                # 48h reminder
                if window.scheduled_start - timedelta(hours=48) <= now < window.scheduled_start - timedelta(hours=24):
                    if not window.notified_48h:
                        self.notify_all(f"⏰ Reminder: System maintenance in 48 hours — {timezone.localtime(window.scheduled_start).strftime('%Y-%m-%d %H:%M')}")
                        window.notified_48h = True
                        window.save(update_fields=["notified_48h"])

                # 24h reminder
                elif window.scheduled_start - timedelta(hours=24) <= now < window.scheduled_start:
                    if not window.notified_24h:
                        self.notify_all(f"⏰ Final Reminder: System maintenance starts in 24 hours — {timezone.localtime(window.scheduled_start).strftime('%Y-%m-%d %H:%M')}. Please save your work.")
                        window.notified_24h = True
                        window.save(update_fields=["notified_24h"])

            # Activate maintenance
            if window.scheduled_start <= now <= window.scheduled_end and window.actual_end is None:
                if not window.is_active:
                    # Maintenance just started!
                    window.is_active = True
                    window.save(update_fields=["is_active"])

                    # SLA Pause: Find all in-progress issues with a future SLA deadline
                    issues_to_pause = Issue.objects.filter(
                        status="in-progress",
                        sla_deadline__gt=now,
                        sla_pause_start__isnull=True
                    )
                    issues_to_pause.update(sla_pause_start=now)

            # Deactivate maintenance
            if window.is_active and (now > window.scheduled_end or window.actual_end is not None):
                # Maintenance ends!
                window.is_active = False
                end_time = window.actual_end if window.actual_end else window.scheduled_end
                window.save(update_fields=["is_active"])
                
                # Notify users if scheduled_end was reached
                if window.actual_end is None:
                    self.notify_all("✅ Maintenance complete. CampusFix is back online.")
                
                # Recalculate paused SLAs
                paused_issues = Issue.objects.filter(
                    status="in-progress",
                    sla_pause_start__isnull=False
                )
                for issue in paused_issues:
                    pause_duration = end_time - issue.sla_pause_start
                    issue.sla_paused_duration += pause_duration
                    issue.sla_deadline += pause_duration
                    issue.sla_pause_start = None
                    issue.save(update_fields=["sla_paused_duration", "sla_deadline", "sla_pause_start"])

                    # Notify staff
                    if issue.assigned_to:
                        hours = round(pause_duration.total_seconds() / 3600, 1)
                        # Avoid 0.0 hour extensions text
                        if hours > 0:
                            NotificationService.create_notification(
                                user=issue.assigned_to,
                                title=f"SLA Extended for Issue #{issue.id}",
                                message=f"Your SLA deadline for Issue #{issue.id} has been extended by {hours} hours due to the maintenance window.",
                                notification_type="system",
                                related_issue=issue
                            )

        # 2. SLA Reminders
        active_issues = Issue.objects.filter(
            ~Q(status__in=["resolved", "closed"]),
            sla_deadline__isnull=False
        )

        admins = User.objects.filter(Q(is_superuser=True) | Q(role="admin")).distinct()

        for issue in active_issues:
            delta = issue.sla_deadline - now
            
            # Breach
            if delta.total_seconds() < 0 and not issue.sla_breached:
                issue.sla_breached = True
                issue.save(update_fields=["sla_breached"])
                if issue.assigned_to:
                    NotificationService.create_notification(
                        user=issue.assigned_to,
                        title=f"SLA Breach: Issue #{issue.id}",
                        message=f"❌ Issue #{issue.id} — {issue.title} SLA has been breached. This issue is now overdue.",
                        notification_type="assignment",
                        related_issue=issue
                    )
                for admin in admins:
                    deadline_str = timezone.localtime(issue.sla_deadline).strftime('%Y-%m-%d %H:%M')
                    staff_name = issue.assigned_to.get_full_name() if issue.assigned_to else "Unassigned"
                    NotificationService.create_notification(
                        user=admin,
                        title=f"SLA Breach: Issue #{issue.id}",
                        message=f"❌ SLA Breach: Issue #{issue.id} assigned to {staff_name} is overdue. SLA deadline was {deadline_str}.",
                        notification_type="assignment",
                        related_issue=issue
                    )

            # Same-day (24h)
            elif 0 <= delta.total_seconds() <= 86400 and not issue.sla_reminded_day:
                issue.sla_reminded_day = True
                issue.save(update_fields=["sla_reminded_day"])
                if issue.assigned_to:
                    time_str = timezone.localtime(issue.sla_deadline).strftime('%H:%M')
                    NotificationService.create_notification(
                        user=issue.assigned_to,
                        title=f"SLA Reminder: Issue #{issue.id} due TODAY",
                        message=f"🚨 Issue #{issue.id} — {issue.title} is due TODAY by {time_str}. Please resolve or flag a blocker immediately.",
                        notification_type="assignment",
                        related_issue=issue
                    )

            # 2-day
            elif 86400 < delta.total_seconds() <= 172800 and not issue.sla_reminded_2d:
                issue.sla_reminded_2d = True
                issue.save(update_fields=["sla_reminded_2d"])
                if issue.assigned_to:
                    date_str = timezone.localtime(issue.sla_deadline).strftime('%Y-%m-%d')
                    NotificationService.create_notification(
                        user=issue.assigned_to,
                        title=f"SLA Urgent: Issue #{issue.id} due in 2 days",
                        message=f"🔴 Urgent: Issue #{issue.id} — {issue.title} is due in 2 days ({date_str}). Immediate attention required.",
                        notification_type="assignment",
                        related_issue=issue
                    )

            # 5-day
            elif 172800 < delta.total_seconds() <= 432000 and not issue.sla_reminded_5d:
                issue.sla_reminded_5d = True
                issue.save(update_fields=["sla_reminded_5d"])
                if issue.assigned_to:
                    date_str = timezone.localtime(issue.sla_deadline).strftime('%Y-%m-%d')
                    NotificationService.create_notification(
                        user=issue.assigned_to,
                        title=f"SLA Reminder: Issue #{issue.id} due in 5 days",
                        message=f"⚠️ Issue #{issue.id} — {issue.title} is due in 5 days ({date_str}). Please ensure progress is on track.",
                        notification_type="assignment",
                        related_issue=issue
                    )

        self.stdout.write(self.style.SUCCESS('Successfully checked maintenance windows and SLAs'))

    def notify_all(self, message):
        users = User.objects.all()
        for user in users:
            NotificationService.create_notification(
                user=user,
                title="System Maintenance Update",
                message=message,
                notification_type="system"
            )
