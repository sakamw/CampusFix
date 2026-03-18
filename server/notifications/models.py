from django.db import models
from django.conf import settings
from django.utils import timezone
from security.validators import NoMaliciousContentValidator


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


class Announcement(models.Model):
    """
    Admin-authored campus-wide announcements shown in the student dashboard.
    """

    title = models.CharField(
        max_length=255,
        validators=[NoMaliciousContentValidator()],
    )
    body = models.TextField(
        validators=[NoMaliciousContentValidator()],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, the announcement will stop showing after this date.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() > self.expires_at)


class AnnouncementDismissal(models.Model):
    """
    Tracks when a user has dismissed a given announcement so it no longer appears.
    """

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="dismissals",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dismissed_announcements",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("announcement", "user")
        ordering = ["-dismissed_at"]


class FailedEmail(models.Model):
    """Log of failed email attempts for admin review."""
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    error_message = models.TextField()
    attempted_at = models.DateTimeField(auto_now_add=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"Failed: {self.subject} to {self.to_email}"
