"""
Signals for automatic notification triggering.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Issue, Comment, Upvote
from notifications.services import NotificationService, AdminDashboardService

User = get_user_model()


@receiver(post_save, sender=Issue)
def issue_created_or_updated(sender, instance, created, **kwargs):
    """Handle issue creation and updates."""
    if created:
        # New issue created
        AdminDashboardService.notify_new_issue(instance)
        
        # Notify relevant staff about new issue
        if instance.priority in ['high', 'critical']:
            # Notify all staff about high/critical priority issues
            staff_users = User.objects.filter(is_staff=True, is_active=True)
            for staff in staff_users:
                NotificationService.create_notification(
                    user=staff,
                    title=f"New {instance.get_priority_display()} priority issue: {instance.title}",
                    message=f"A new {instance.get_priority_display()} priority issue was reported by {instance.reporter.get_full_name() or instance.reporter.email}",
                    notification_type='assignment',
                    related_issue=instance
                )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            # Status changed
            changed_by = getattr(instance, "_modified_by_user", instance.reporter)

            NotificationService.notify_issue_status_change(
                instance,
                old_status,
                instance.status,
                changed_by,
            )

            AdminDashboardService.notify_issue_status_change(
                instance,
                old_status,
                instance.status,
            )

            # If resolved, send resolution notifications
            if instance.status == 'resolved' and old_status != 'resolved':
                NotificationService.notify_issue_resolution(
                    instance,
                    changed_by,
                )


@receiver(pre_save, sender=Issue)
def issue_pre_save(sender, instance, **kwargs):
    """
    Capture old status for reliable change detection and
    keep `resolved_at` aligned across all save entrypoints.
    """
    if not instance.pk:
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    instance._old_status = old.status  # type: ignore[attr-defined]

    # Keep resolved_at in sync when status becomes resolved/closed
    if old.status != instance.status and instance.status in {"resolved", "closed"} and not instance.resolved_at:
        from django.utils import timezone
        instance.resolved_at = timezone.now()


@receiver(post_save, sender=Comment)
def comment_created(sender, instance, created, **kwargs):
    """Handle new comment creation."""
    if created:
        NotificationService.notify_issue_comment(
            instance.issue,
            instance.user,
            instance.content
        )


@receiver(post_save, sender=Upvote)
def upvote_created(sender, instance, created, **kwargs):
    """Handle new upvote creation."""
    if created:
        # Update upvote count on issue
        issue = instance.issue
        issue.upvote_count = Upvote.objects.filter(issue=issue).count()
        issue.save(update_fields=['upvote_count'])
        
        NotificationService.notify_issue_upvote(issue, instance.user)
