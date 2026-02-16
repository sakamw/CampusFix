from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Issue(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in-progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
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

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    location = models.CharField(max_length=255)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_issues'
    )
    
    # Admin work fields
    admin_notes = models.TextField(blank=True, help_text="Admin's internal notes about the issue")
    resolution_summary = models.TextField(blank=True, help_text="Summary of resolution for user")
    resolution_details = models.TextField(blank=True, help_text="Detailed explanation of work done")
    resolution_evidence = models.TextField(blank=True, help_text="Evidence or proof of resolution")
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


class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on {self.issue.title}"


class Attachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='issue_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.filename} - {self.issue.title}"


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
