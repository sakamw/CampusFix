from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import Notification, NotificationPreference

User = get_user_model()
channel_layer = get_channel_layer()


class NotificationService:
    """Service for managing notifications."""
    
    @staticmethod
    def create_notification(user, title, message, notification_type='system', related_issue=None):
        """Create and send a notification."""
        # Check user preferences
        try:
            preferences = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            preferences = NotificationPreference.objects.create(user=user)
        
        # Create notification in database
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_issue=related_issue
        )
        
        # Send real-time notification if enabled
        if preferences.real_time_notifications:
            NotificationService._send_real_time_notification(user, notification)
        
        # Send email notification if enabled and applicable
        if NotificationService._should_send_email(preferences, notification_type):
            NotificationService._send_email_notification(user, notification)
        
        return notification
    
    @staticmethod
    def _send_real_time_notification(user, notification):
        """Send real-time notification via WebSocket."""
        try:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'notification_type': notification.notification_type,
                        'created_at': notification.created_at.isoformat(),
                        'is_read': notification.is_read,
                        'related_issue_id': notification.related_issue.id if notification.related_issue else None
                    }
                }
            )
        except Exception as e:
            # Log error but don't fail the notification creation
            print(f"Failed to send real-time notification: {e}")
    
    @staticmethod
    def _should_send_email(preferences, notification_type):
        """Check if email should be sent based on user preferences."""
        email_preferences = {
            'comment': preferences.email_on_comment,
            'status_change': preferences.email_on_status_change,
            'assignment': preferences.email_on_assignment,
            'upvote': preferences.email_on_upvote,
            'resolution': preferences.email_on_resolution,
        }
        return email_preferences.get(notification_type, False)
    
    @staticmethod
    def _send_email_notification(user, notification):
        """Send email notification (placeholder for email service)."""
        subject = notification.title or "CampusFix notification"
        message = notification.message or ""

        from_email = getattr(
            settings, "DEFAULT_FROM_EMAIL", "no-reply@campusfix.local"
        )

        # Best-effort email send; failures should not break the app
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            # Intentionally swallow exceptions; logging can be added later
            return
    
    @staticmethod
    def notify_issue_comment(issue, comment_author, comment_content):
        """Notify relevant users about a new comment."""
        # Notify issue reporter (if not the commenter)
        if issue.reporter != comment_author:
            NotificationService.create_notification(
                user=issue.reporter,
                title=f"New comment on: {issue.title}",
                message=f"{comment_author.get_full_name() or comment_author.email} commented: {comment_content[:100]}...",
                notification_type='comment',
                related_issue=issue
            )
        
        # Notify assigned staff (if not the commenter)
        if hasattr(issue, 'assigned_to') and issue.assigned_to and issue.assigned_to != comment_author and issue.assigned_to.is_staff:
            NotificationService.create_notification(
                user=issue.assigned_to,
                title=f"New comment on assigned issue: {issue.title}",
                message=f"{comment_author.get_full_name() or comment_author.email} commented: {comment_content[:100]}...",
                notification_type='comment',
                related_issue=issue
            )
    
    @staticmethod
    def notify_issue_status_change(issue, old_status, new_status, changed_by):
        """Notify about issue status change."""
        # Notify issue reporter (if not the changer)
        if issue.reporter != changed_by:
            NotificationService.create_notification(
                user=issue.reporter,
                title=f"Status updated on: {issue.title}",
                message=f"Status changed from {old_status} to {new_status} by {changed_by.get_full_name() or changed_by.email}",
                notification_type='status_change',
                related_issue=issue
            )
        
        # Notify assigned staff (if not the changer)
        if hasattr(issue, 'assigned_to') and issue.assigned_to and issue.assigned_to != changed_by:
            NotificationService.create_notification(
                user=issue.assigned_to,
                title=f"Status updated on assigned issue: {issue.title}",
                message=f"Status changed from {old_status} to {new_status} by {changed_by.get_full_name() or changed_by.email}",
                notification_type='status_change',
                related_issue=issue
            )
    
    @staticmethod
    def notify_issue_assignment(issue, assigned_by):
        """Notify about issue assignment."""
        if issue.assigned_to:
            NotificationService.create_notification(
                user=issue.assigned_to,
                title=f"Issue assigned to you: {issue.title}",
                message=f"You have been assigned to this issue by {assigned_by.get_full_name() or assigned_by.email}",
                notification_type='assignment',
                related_issue=issue
            )
    
    @staticmethod
    def notify_issue_upvote(issue, upvoter):
        """Notify about issue upvote."""
        # Notify issue reporter (if not the upvoter)
        if issue.reporter != upvoter:
            NotificationService.create_notification(
                user=issue.reporter,
                title=f"Your issue received an upvote: {issue.title}",
                message=f"{upvoter.get_full_name() or upvoter.email} upvoted your issue",
                notification_type='upvote',
                related_issue=issue
            )
    
    @staticmethod
    def notify_issue_resolution(issue, resolved_by):
        """Notify about issue resolution."""
        # Notify issue reporter (if not the resolver)
        if issue.reporter != resolved_by:
            summary = (issue.resolution_summary or "").strip()
            summary_text = f" {summary}" if summary else ""
            NotificationService.create_notification(
                user=issue.reporter,
                title=f"Your issue '{issue.title}' has been resolved",
                message=f"Your issue '{issue.title}' has been resolved.{summary_text} Please rate your experience.",
                notification_type="resolution",
                related_issue=issue,
            )
        
        # Notify all participants in the issue
        participants = User.objects.filter(
            comment__issue=issue
        ).distinct().exclude(
            id__in=[issue.reporter.id, resolved_by.id]
        )
        
        for participant in participants:
            NotificationService.create_notification(
                user=participant,
                title=f"Issue resolved: {issue.title}",
                message=f"This issue was resolved by {resolved_by.get_full_name() or resolved_by.email}",
                notification_type='resolution',
                related_issue=issue
            )


class AdminDashboardService:
    """Service for admin dashboard real-time updates."""
    
    @staticmethod
    def broadcast_dashboard_update(event_type, data):
        """Broadcast dashboard update to all admin users."""
        try:
            async_to_sync(channel_layer.group_send)(
                "admin_dashboard",
                {
                    'type': 'dashboard_update',
                    'data': {
                        'event_type': event_type,
                        'data': data,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )
        except Exception as e:
            print(f"Failed to broadcast dashboard update: {e}")
    
    @staticmethod
    def notify_new_issue(issue):
        """Notify admins about new issue."""
        AdminDashboardService.broadcast_dashboard_update(
            'new_issue',
            {
                'issue_id': issue.id,
                'title': issue.title,
                'reporter': issue.reporter.email,
                'priority': issue.priority,
                'category': issue.category
            }
        )
    
    @staticmethod
    def notify_issue_status_change(issue, old_status, new_status):
        """Notify admins about issue status change."""
        AdminDashboardService.broadcast_dashboard_update(
            'status_change',
            {
                'issue_id': issue.id,
                'title': issue.title,
                'old_status': old_status,
                'new_status': new_status
            }
        )
