"""
Signals for automatic notification triggering.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Issue, Comment, Upvote
from notifications.services import NotificationService, AdminDashboardService
from .ai_services import ai_service

User = get_user_model()


def analyze_issue_sentiment(instance):
    """Analyze sentiment of an issue and update fields."""
    if not ai_service.is_available():
        return
    
    # Combine title and description for analysis
    text_to_analyze = f"{instance.title} {instance.description}"
    
    result = ai_service.analyze_sentiment(text_to_analyze)
    
    # Update issue with AI analysis
    instance.sentiment = result['sentiment']
    instance.frustration_score = result['frustration_score']
    instance.needs_escalation = result['needs_escalation']
    instance.ai_analyzed_at = timezone.now()
    
    # Save without triggering signals again
    instance.save(update_fields=['sentiment', 'frustration_score', 'needs_escalation', 'ai_analyzed_at'])
    
    # If needs escalation, notify admins
    if result['needs_escalation']:
        staff_users = User.objects.filter(is_staff=True, is_active=True)
        for staff in staff_users:
            NotificationService.create_notification(
                user=staff,
                title=f"🚨 Issue #{instance.id} needs attention - high frustration detected",
                message=f"Student appears frustrated with issue '{instance.title}'. Please prioritize this issue.",
                notification_type='system',
                related_issue=instance
            )


def analyze_comment_sentiment(instance):
    """Analyze sentiment of a comment and update fields."""
    if not ai_service.is_available():
        return
    
    result = ai_service.analyze_sentiment(instance.content)
    
    # Update comment with AI analysis
    instance.sentiment = result['sentiment']
    instance.frustration_score = result['frustration_score']
    instance.needs_escalation = result['needs_escalation']
    instance.ai_analyzed_at = timezone.now()
    
    # Save without triggering signals again
    instance.save(update_fields=['sentiment', 'frustration_score', 'needs_escalation', 'ai_analyzed_at'])
    
    # If needs escalation, notify admins
    if result['needs_escalation']:
        staff_users = User.objects.filter(is_staff=True, is_active=True)
        for staff in staff_users:
            NotificationService.create_notification(
                user=staff,
                title=f"🚨 Comment on issue #{instance.issue.id} needs attention",
                message=f"Student comment appears frustrated. Please review issue '{instance.issue.title}'.",
                notification_type='system',
                related_issue=instance.issue
            )


@receiver(post_save, sender=Issue)
def issue_created_or_updated(sender, instance, created, **kwargs):
    """Handle issue creation and updates."""
    if created:
        # New issue created
        AdminDashboardService.notify_new_issue(instance)
        
        # Analyze sentiment for new issues
        analyze_issue_sentiment(instance)
        
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
        # Analyze sentiment for new comments
        analyze_comment_sentiment(instance)
        
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
