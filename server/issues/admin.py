from django.contrib import admin
from django.db.models import Sum
from django.utils.safestring import mark_safe
from .models import Issue, Comment, Attachment, Upvote, AdminWorkLog, ResolutionEvidence, ProgressUpdate


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'status', 'priority', 'reporter', 'created_at', 'upvote_count', 'work_progress', 'evidence_count']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'upvote_count', 'evidence_files_display', 'progress_display']
    
    fieldsets = (
        ('Issue Information', {
            'fields': ('title', 'description', 'category', 'location', 'visibility')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Reporter Information', {
            'fields': ('reporter',)
        }),
        ('Progress Tracking', {
            'fields': (
                'progress_percentage',
                'progress_status',
                'progress_notes',
                'estimated_completion'
            ),
            'classes': ('collapse',),
        }),
        ('Admin Work Section', {
            'fields': (
                'admin_notes',
                'resolution_summary', 
                'resolution_details',
                'actual_completion',
                'work_hours',
                'resolution_cost'
            ),
            'classes': ('collapse',),
        }),
        ('Resolution Evidence', {
            'fields': ('evidence_files_display',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'upvote_count', 'progress_display')
        }),
    )
    
    def work_progress(self, obj):
        """Show work progress based on work logs"""
        total_hours = obj.work_logs.aggregate(total=Sum('hours_spent'))['total'] or 0
        log_count = obj.work_logs.count()
        if log_count == 0:
            return "No work started"
        return f"{log_count} tasks, {total_hours}h total"
    work_progress.short_description = 'Work Progress'
    
    def evidence_count(self, obj):
        """Show count of evidence files"""
        count = obj.evidence_files.count()
        if count == 0:
            return "No evidence"
        return f"{count} file(s)"
    evidence_count.short_description = 'Evidence Files'
    
    def evidence_files_display(self, obj):
        """Display evidence files with links"""
        evidence_files = obj.evidence_files.all()
        if not evidence_files:
            return "No evidence files uploaded"
        
        html = "<div style='max-height: 200px; overflow-y: auto;'>"
        for evidence in evidence_files:
            html += f"""
            <div style="margin-bottom: 10px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <strong><a href="{evidence.file.url}" target="_blank">{evidence.filename}</a></strong><br>
                <small>Type: {evidence.get_file_type_display()} | Size: {self._format_file_size(evidence.file_size)}</small><br>
                {evidence.description and f"<small>Description: {evidence.description}</small><br>"}
                <small>Uploaded by {evidence.admin.email} on {evidence.uploaded_at.strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            """
        html += "</div>"
        return mark_safe(html)
    evidence_files_display.short_description = 'Evidence Files'
    
    def _format_file_size(self, size):
        """Format file size in human readable format"""
        if not size:
            return "Unknown"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def progress_display(self, obj):
        """Display progress information"""
        progress_updates = obj.progress_updates.all()
        if not progress_updates and obj.progress_percentage == 0:
            return "No progress updates yet"
        
        html = "<div style='max-height: 200px; overflow-y: auto;'>"
        
        # Show current progress
        html += f"""
        <div style="margin-bottom: 10px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">
            <strong>Current Progress: {obj.progress_percentage}%</strong><br>
            <small>Status: {obj.progress_status}</small><br>
            {obj.progress_notes and f"<small>Notes: {obj.progress_notes[:100]}{'...' if len(obj.progress_notes) > 100 else ''}</small><br>"}
            <small>Last updated: {obj.progress_updated_at.strftime('%Y-%m-%d %H:%M')}</small>
        </div>
        """
        
        # Show recent updates
        if progress_updates:
            html += "<strong>Recent Updates:</strong><br>"
            for update in progress_updates[:3]:
                html += f"""
                <div style="margin-bottom: 8px; padding: 6px; border-left: 3px solid #007cba; background: #f0f8ff;">
                    <strong>{update.title}</strong> ({update.progress_percentage}%)<br>
                    <small>{update.get_update_type_display()} by {update.admin.email}</small><br>
                    <small>{update.created_at.strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """
        
        html += "</div>"
        return mark_safe(html)
    progress_display.short_description = 'Progress Information'


@admin.register(AdminWorkLog)
class AdminWorkLogAdmin(admin.ModelAdmin):
    list_display = ['issue', 'admin', 'work_type', 'hours_spent', 'created_at', 'outcome_summary']
    list_filter = ['work_type', 'created_at', 'admin']
    search_fields = ['issue__title', 'description', 'outcome']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Work Information', {
            'fields': ('issue', 'admin', 'work_type', 'hours_spent')
        }),
        ('Work Details', {
            'fields': ('description', 'materials_used', 'outcome', 'next_steps')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def outcome_summary(self, obj):
        """Show brief outcome"""
        return obj.outcome[:50] + "..." if len(obj.outcome) > 50 else obj.outcome
    outcome_summary.short_description = 'Outcome Summary'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'issue', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'issue__title']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'issue', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'issue__title']
    date_hierarchy = 'uploaded_at'


@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'issue', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['issue__title', 'user__email']
    date_hierarchy = 'created_at'


@admin.register(ResolutionEvidence)
class ResolutionEvidenceAdmin(admin.ModelAdmin):
    list_display = ['filename', 'issue', 'admin', 'file_type', 'file_size_display', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at', 'admin']
    search_fields = ['filename', 'description', 'issue__title']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'file_size']
    
    fieldsets = (
        ('Evidence Information', {
            'fields': ('issue', 'admin', 'file_type', 'description')
        }),
        ('File Details', {
            'fields': ('file', 'filename', 'file_size')
        }),
        ('Timestamp', {
            'fields': ('uploaded_at',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if not obj.file_size:
            return "Unknown"
        
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size'
    
    def save_model(self, request, obj, form, change):
        """Set file size and admin on save"""
        if not change:  # Only for new objects
            obj.admin = request.user
            if obj.file and hasattr(obj.file, 'size'):
                obj.file_size = obj.file.size
        super().save_model(request, obj, form, change)


@admin.register(ProgressUpdate)
class ProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ['title', 'issue', 'admin', 'update_type', 'progress_percentage', 'is_major_update', 'created_at']
    list_filter = ['update_type', 'is_major_update', 'created_at', 'admin']
    search_fields = ['title', 'description', 'issue__title']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Update Information', {
            'fields': ('issue', 'admin', 'update_type', 'is_major_update')
        }),
        ('Progress Details', {
            'fields': ('title', 'progress_percentage', 'description', 'next_steps')
        }),
        ('Timeline', {
            'fields': ('estimated_completion', 'created_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set admin and update issue progress on save"""
        if not change:  # Only for new objects
            obj.admin = request.user
        
        # Update the parent issue's progress
        if change or not change:  # Always update the issue
            issue = obj.issue
            issue.progress_percentage = obj.progress_percentage
            issue.progress_updated_at = obj.created_at
            if obj.description:
                issue.progress_notes = obj.description[:500]  # Truncate for notes
            issue.save(update_fields=['progress_percentage', 'progress_updated_at', 'progress_notes'])
        
        super().save_model(request, obj, form, change)
