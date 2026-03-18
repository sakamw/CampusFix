from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.apps import apps
from datetime import timedelta, datetime
from security.validators import (
    NoMaliciousContentValidator,
    secure_location_validator,
    validate_file_upload,
)


class Issue(models.Model):
    STATUS_CHOICES = [
        ("open", "Pending"),
        ("in-progress", "In Progress"),
        ("awaiting_verification", "Awaiting Verification"),
        ("resolved", "Resolved"),
        ("reopened", "Reopened"),
        ("closed", "Closed"),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    CATEGORY_CHOICES = [
        ('facilities', 'Facilities'),
        ('it-infrastructure', 'IT Infrastructure'),
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('equipment', 'Equipment'),
        ('safety', 'Safety'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    title = models.CharField(max_length=255, validators=[NoMaliciousContentValidator()])
    description = models.TextField(validators=[NoMaliciousContentValidator()])
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    location = models.CharField(max_length=255, validators=[secure_location_validator])
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_issues'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_issues',
        null=True,
        blank=True,
        help_text="Staff member currently responsible for this issue",
    )
    is_anonymous = models.BooleanField(
        default=False,
        help_text="If true, reporter identity is hidden from non-superusers."
    )
    
    # Admin work fields
    admin_notes = models.TextField(blank=True, help_text="Admin's internal notes about the issue")
    resolution_summary = models.TextField(
        blank=True, null=True, help_text="Summary of resolution for user"
    )
    resolution_details = models.TextField(blank=True, help_text="Detailed explanation of work done")
    resolution_evidence = models.TextField(blank=True, help_text="Evidence or proof of resolution")
    estimated_resolution_text = models.CharField(
        max_length=255,
        blank=True,
        help_text='Human-friendly ETA, e.g. "2–3 business days"',
    )
    estimated_completion = models.DateTimeField(null=True, blank=True, help_text="Estimated completion date")
    actual_completion = models.DateTimeField(null=True, blank=True, help_text="Actual completion date")
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Hours spent on resolution")
    resolution_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Cost of resolution if applicable")
    
    # Progress tracking fields
    progress_percentage = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    progress_status = models.CharField(max_length=50, default='not_started', help_text="Current progress status")
    progress_updated_at = models.DateTimeField(auto_now=True, help_text="When progress was last updated")
    progress_notes = models.TextField(blank=True, help_text="Notes about current progress for user")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this issue was assigned to the current assignee",
    )

    is_blocked = models.BooleanField(
        default=False, help_text="Whether this issue is currently blocked"
    )
    blocker_note = models.TextField(
        null=True,
        blank=True,
        help_text="Explanation of what is blocking progress",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_issues",
        null=True,
        blank=True,
        help_text="Admin who verified and closed the issue",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the issue was verified by an admin",
    )
    sla_due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this issue is due according to SLA rules",
    )
    is_overdue = models.BooleanField(
        default=False,
        help_text="Whether this issue has exceeded its SLA without being resolved",
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this issue is part of a recurring pattern for the same location and category",
    )
    
    # New SLA Tracking Fields
    sla_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this issue is due according to SLA rules starting from acknowledgement",
    )
    sla_paused_duration = models.DurationField(
        default=timedelta(0),
        help_text="Total time SLA was paused due to maintenance",
    )
    sla_pause_start = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when the SLA was paused due to maintenance"
    )
    sla_breached = models.BooleanField(
        default=False,
        help_text="True if not resolved by sla_deadline",
    )
    sla_reminded_5d = models.BooleanField(default=False, help_text="Tracks if 5-day reminder was sent")
    sla_reminded_2d = models.BooleanField(default=False, help_text="Tracks if 2-day reminder was sent")
    sla_reminded_day = models.BooleanField(default=False, help_text="Tracks if same-day reminder was sent")
    
    # AI Analysis Fields
    sentiment = models.CharField(
        max_length=20,
        choices=[
            ('positive', 'Positive'),
            ('neutral', 'Neutral'),
            ('frustrated', 'Frustrated'),
            ('angry', 'Angry'),
        ],
        default='neutral',
        help_text="AI-detected sentiment from the issue description",
    )
    frustration_score = models.IntegerField(
        default=0,
        help_text="AI-calculated frustration score (0-10)",
    )
    needs_escalation = models.BooleanField(
        default=False,
        help_text="Whether this issue needs priority escalation based on AI analysis",
    )
    ai_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this issue was last analyzed by AI",
    )
    
    upvote_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['reporter']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def mark_recurring(self):
        """
        Mark this issue as recurring if there have been at least two
        other issues in the last 30 days with the same location and category.
        """
        if not self.location or not self.category:
            return

        window_start = timezone.now() - timedelta(days=30)
        qs = self.__class__.objects.filter(
            location=self.location,
            category=self.category,
            created_at__gte=window_start,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.count() >= 2:
            self.is_recurring = True

    def apply_sla(self, start_time=None):
        """
        Ensure sla_due_at and is_overdue reflect the current SLA rule
        for this issue's category, based on start_time or created_at.
        """
        SLARule = apps.get_model("issues", "SLARule")  # type: ignore[assignment]
        try:
            rule = SLARule.objects.get(category=self.category)  # type: ignore[attr-defined]
        except SLARule.DoesNotExist:  # type: ignore[attr-defined]
            return

        base_time = start_time or self.created_at or timezone.now()
        if not base_time:
            return

        self.sla_due_at = base_time + timedelta(hours=rule.response_time_hours)

        # Only mark overdue for non-resolved/closed issues
        if self.status not in {"resolved", "closed"} and self.sla_due_at and timezone.now() > self.sla_due_at:
            self.is_overdue = True

    def save(self, *args, **kwargs):
        # Recompute SLA fields when creating the issue or when category/status changes.
        # For safety, always ensure sla_due_at is set if possible.
        self.mark_recurring()
        
        # If created_at is not yet set (new instance), use timezone.now() as fallback for SLA
        if not self.sla_due_at:
            self.apply_sla()
        else:
            # If status changed to a non-final state, keep overdue flag up to date
            if self.sla_due_at and self.status not in {"resolved", "closed"}:
                if timezone.now() > self.sla_due_at:
                    self.is_overdue = True
        super().save(*args, **kwargs)


class IssueProgressLog(models.Model):
    LOG_TYPE_CHOICES = [
        ("acknowledged", "Acknowledged"),
        ("on_site", "Arrived On Site"),
        ("diagnosis", "Diagnosis"),
        ("in_progress", "Work In Progress"),
        ("blocked", "Blocked - Needs Attention"),
        ("completed", "Work Completed"),
        ("reopened", "Reopened"),
    ]

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="progress_logs",
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_progress_logs",
        help_text="Staff member who created this log entry",
    )
    log_type = models.CharField(max_length=32, choices=LOG_TYPE_CHOICES)
    description = models.TextField(help_text="What was observed or done at this step")
    photo = models.ImageField(
        upload_to="issue_progress/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="Optional photo evidence for this log entry",
        validators=[validate_file_upload],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["issue"]),
            models.Index(fields=["staff"]),
            models.Index(fields=["log_type"]),
        ]

    def __str__(self):
        return f"{self.get_log_type_display()} - #{self.issue_id}"


class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(validators=[NoMaliciousContentValidator()])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # AI Analysis Fields
    sentiment = models.CharField(
        max_length=20,
        choices=[
            ('positive', 'Positive'),
            ('neutral', 'Neutral'),
            ('frustrated', 'Frustrated'),
            ('angry', 'Angry'),
        ],
        default='neutral',
        help_text="AI-detected sentiment from the comment",
    )
    frustration_score = models.IntegerField(
        default=0,
        help_text="AI-calculated frustration score (0-10)",
    )
    needs_escalation = models.BooleanField(
        default=False,
        help_text="Whether this comment indicates need for escalation",
    )
    ai_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this comment was last analyzed by AI",
    )
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.issue.title}"


class Attachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='issue_attachments/%Y/%m/%d/', validators=[validate_file_upload])
    filename = models.CharField(max_length=255, validators=[NoMaliciousContentValidator()])
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        super().clean()
        if self.file:
            validate_file_upload(self.file)


class Upvote(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='upvotes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('issue', 'user')
    
    def __str__(self):
        return f"{self.user.email} upvoted {self.issue.title}"


class AdminWorkLog(models.Model):
    """Track admin work on issues"""
    WORK_TYPE_CHOICES = [
        ('assessment', 'Initial Assessment'),
        ('investigation', 'Investigation'),
        ('repair', 'Repair Work'),
        ('maintenance', 'Maintenance'),
        ('coordination', 'Coordination'),
        ('documentation', 'Documentation'),
        ('follow_up', 'Follow-up'),
        ('other', 'Other'),
    ]
    
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='work_logs')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='work_logs')
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    description = models.TextField(help_text="Description of work performed")
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, help_text="Hours spent on this work")
    materials_used = models.TextField(blank=True, help_text="Materials or resources used")
    outcome = models.TextField(help_text="Result or outcome of this work")
    next_steps = models.TextField(blank=True, help_text="Next steps if any")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['issue']),
            models.Index(fields=['admin']),
        ]
    
    def __str__(self):
        return f"{self.admin.email} - {self.get_work_type_display()} on {self.issue.title}"


class ProgressUpdate(models.Model):
    """Track detailed progress updates for issues"""
    UPDATE_TYPE_CHOICES = [
        ('milestone', 'Milestone Reached'),
        ('delay', 'Delay Reported'),
        ('issue', 'New Issue Found'),
        ('completion', 'Task Completed'),
        ('status', 'Status Update'),
        ('resource', 'Resource Update'),
        ('other', 'Other Update'),
    ]
    
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='progress_updates')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_updates')
    update_type = models.CharField(max_length=20, choices=UPDATE_TYPE_CHOICES)
    progress_percentage = models.IntegerField(help_text="Progress percentage at this update (0-100)")
    title = models.CharField(max_length=255, help_text="Brief title of this update")
    description = models.TextField(help_text="Detailed description of progress update")
    next_steps = models.TextField(blank=True, help_text="Next steps or planned actions")
    estimated_completion = models.DateTimeField(null=True, blank=True, help_text="New estimated completion date")
    is_major_update = models.BooleanField(default=False, help_text="Is this a major milestone update?")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['issue']),
            models.Index(fields=['admin']),
            models.Index(fields=['is_major_update']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.issue.title} ({self.progress_percentage}%)"


class ResolutionEvidence(models.Model):
    """Store evidence files for issue resolution"""
    EVIDENCE_TYPES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('receipt', 'Receipt'),
        ('report', 'Report'),
        ('other', 'Other'),
    ]
    
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='evidence_files')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_evidence')
    file = models.FileField(upload_to='resolution_evidence/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='other')
    description = models.TextField(blank=True, help_text="Description of this evidence file")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['-uploaded_at']),
            models.Index(fields=['issue']),
            models.Index(fields=['admin']),
        ]
    
    def __str__(self):
        return f"{self.filename} - Evidence for {self.issue.title}"


class SLARule(models.Model):
    """
    SLA configuration per issue category.

    Stores the expected resolution window in hours; e.g.
    Safety = 24h, Plumbing = 48h, General = 120h.
    """

    category = models.CharField(
        max_length=50,
        choices=Issue.CATEGORY_CHOICES,
        unique=True,
    )
    response_time_hours = models.PositiveIntegerField(
        help_text="Target resolution time in hours for this category",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.get_category_display()} SLA: {self.response_time_hours}h"


class MaintenanceTask(models.Model):
    """
    Scheduled preventive maintenance task for the maintenance calendar.
    """

    title = models.CharField(max_length=255, validators=[NoMaliciousContentValidator()])
    location = models.CharField(max_length=255, validators=[secure_location_validator])
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_tasks",
    )
    scheduled_for = models.DateTimeField(
        help_text="When this maintenance task is planned to occur"
    )
    notes = models.TextField(blank=True, validators=[NoMaliciousContentValidator()])
    related_issue = models.ForeignKey(
        Issue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_tasks",
        help_text="Optional related issue that motivated this maintenance task",
    )
    reminder_sent = models.BooleanField(
        default=False,
        help_text="Whether the 24-hour reminder email has been sent to the assigned staff",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"{self.title} @ {self.location} on {self.scheduled_for}"


class IssueFeedback(models.Model):
    """
    Post-resolution feedback from the original reporter about their experience.

    Stored separately from Issue so we can track per-user feedback and
    aggregate ratings for staff performance analytics.
    """

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_feedback",
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (worst) to 5 (best)",
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional written feedback about the resolution experience",
        validators=[NoMaliciousContentValidator()],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("issue", "user")
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Feedback {self.rating}/5 by {self.user.email} on issue #{self.issue_id}"


class MaintenanceWindow(models.Model):
    """
    Admin-scheduled planned system maintenance window.
    """
    title = models.CharField(max_length=255, validators=[NoMaliciousContentValidator()])
    description = models.TextField(validators=[NoMaliciousContentValidator()])
    scheduled_start = models.DateTimeField(help_text="When maintenance begins")
    scheduled_end = models.DateTimeField(help_text="When maintenance is planned to end")
    actual_end = models.DateTimeField(
        null=True, blank=True, help_text="Set if admin ends maintenance early"
    )
    is_active = models.BooleanField(
        default=False, help_text="True when system is currently in maintenance"
    )
    is_cancelled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_maintenance_windows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notified_48h = models.BooleanField(
        default=False, help_text="Tracks if 48hr warning was sent"
    )
    notified_24h = models.BooleanField(
        default=False, help_text="Tracks if 24hr warning was sent"
    )

    class Meta:
        ordering = ["-scheduled_start"]

    def __str__(self):
        return f"{self.title} ({self.scheduled_start} to {self.scheduled_end})"
