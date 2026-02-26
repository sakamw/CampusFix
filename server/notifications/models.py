from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('status_change', 'Status Change'),
        ('assignment', 'Assignment'),
        ('upvote', 'Upvote'),
        ('resolution', 'Resolution'),
        ('system', 'System'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    related_issue = models.ForeignKey(
        'issues.Issue',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"


class NotificationPreference(models.Model):
    """User notification preferences."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notification preferences
    email_on_comment = models.BooleanField(default=True)
    email_on_status_change = models.BooleanField(default=True)
    email_on_assignment = models.BooleanField(default=True)
    email_on_upvote = models.BooleanField(default=False)
    email_on_resolution = models.BooleanField(default=True)
    
    # Real-time notification preferences
    real_time_notifications = models.BooleanField(default=True)
    
    # Daily digest
    daily_digest = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Preferences - {self.user.email}"
