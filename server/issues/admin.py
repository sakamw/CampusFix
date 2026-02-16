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
    readonly_fields = ['created_at', 'updated_at', 'upvote_count', 'evidence_files_display', 'progress_display', 'comments_chat_display']
    
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
        ('Chat & Comments', {
            'fields': ('comments_chat_display',),
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
            <strong style="color: #212529;">Current Progress: {obj.progress_percentage}%</strong><br>
            <small style="color: #495057; font-weight: 500;">Status: {obj.progress_status}</small><br>
            {obj.progress_notes and f"<small style='color: #495057; font-weight: 500;'>Notes: {obj.progress_notes[:100]}{'...' if len(obj.progress_notes) > 100 else ''}</small><br>"}
            <small style="color: #495057; font-weight: 500;">Last updated: {obj.progress_updated_at.strftime('%Y-%m-%d %H:%M')}</small>
        </div>
        """
        
        # Show recent updates
        if progress_updates:
            html += "<strong style='color: #212529;'>Recent Updates:</strong><br>"
            for update in progress_updates[:3]:
                html += f"""
                <div style="margin-bottom: 8px; padding: 6px; border-left: 3px solid #007cba; background: #f0f8ff;">
                    <strong style="color: #212529;">{update.title}</strong> ({update.progress_percentage}%)<br>
                    <small style="color: #495057; font-weight: 500;">{update.get_update_type_display()} by {update.admin.email}</small><br>
                    <small style="color: #495057; font-weight: 500;">{update.created_at.strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """
        
        html += "</div>"
        return mark_safe(html)
    progress_display.short_description = 'Progress Information'
    
    def comments_chat_display(self, obj):
        """Display chat/comments interface for admins"""
        comments = obj.comments.all().order_by('created_at')
        
        if not comments:
            return "No comments yet. Users can comment through the frontend interface."
        
        html = """
        <div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background: #f9f9f9;'>
            <h4 style='margin-top: 0; color: #333; border-bottom: 2px solid #007cba; padding-bottom: 5px;'>
                💬 Chat History ({comments.count()} messages)
            </h4>
        """
        
        for comment in comments:
            # Determine comment style based on user role
            if comment.user.role == 'admin':
                bg_color = '#e3f2fd'  # Light blue for admin
                border_color = '#2196f3'
                role_label = '👨‍💼 Admin'
            else:
                bg_color = '#fff3e0'  # Light orange for user
                border_color = '#ff9800'
                role_label = '👤 User'
            
            html += f"""
            <div style='margin-bottom: 15px; padding: 12px; border-left: 4px solid {border_color}; background-color: {bg_color}; border-radius: 4px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <div>
                        <strong style="color: #212529;">{comment.user.first_name} {comment.user.last_name}</strong>
                        <span style='margin-left: 8px; padding: 2px 6px; background: {border_color}; color: white; border-radius: 3px; font-size: 11px; font-weight: bold;'>
                            {role_label}
                        </span>
                        {comment.user.email != comment.user.get_full_name() and f"<br><small style='color: #495057; font-weight: 500;'>{comment.user.email}</small>"}
                    </div>
                    <small style='color: #495057; font-weight: 500; white-space: nowrap;'>{comment.created_at.strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                <div style='background: white; padding: 8px; border-radius: 3px; margin-top: 5px;'>
                    <p style='margin: 0; line-height: 1.4; color: #212529;'>{comment.content}</p>
                </div>
            </div>
            """
        
        # Add admin response prompt
        html += """
            <div style='margin-top: 20px; padding: 10px; background: #f0f8ff; border: 1px dashed #007cba; border-radius: 4px; text-align: center;'>
                <p style='margin: 0; color: #007cba; font-weight: bold;'>💡 Admin Response</p>
                <p style='margin: 5px 0 0 0; font-size: 12px; color: #495057; font-weight: 500;'>To respond to this issue, add a comment through the Comment model in Django Admin or use the frontend interface.</p>
            </div>
            """
        
        html += "</div>"
        return mark_safe(html)
    comments_chat_display.short_description = 'Chat & Comments'


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
    list_display = ['id', 'issue_title', 'user_info', 'content_preview', 'created_at', 'user_role']
    list_filter = ['created_at', 'user__role']
    search_fields = ['content', 'issue__title', 'user__email', 'user__first_name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Comment Information', {
            'fields': ('issue', 'user', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def issue_title(self, obj):
        """Show issue title with link"""
        return f"<strong>{obj.issue.title}</strong><br><small>ID: {obj.issue.id}</small>"
    issue_title.short_description = 'Issue'
    issue_title.allow_tags = True
    
    def user_info(self, obj):
        """Show user information with role"""
        role_color = '#2196f3' if obj.user.role == 'admin' else '#ff9800'
        role_icon = '👨‍💼' if obj.user.role == 'admin' else '👤'
        return f"""
        <div>
            <strong>{obj.user.first_name} {obj.user.last_name}</strong><br>
            <small style='color: #666;'>{obj.user.email}</small><br>
            <span style='background: {role_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;'>
                {role_icon} {obj.user.role.title()}
            </span>
        </div>
        """
    user_info.short_description = 'User'
    user_info.allow_tags = True
    
    def content_preview(self, obj):
        """Show content preview"""
        content = obj.content
        if len(content) > 100:
            return f"{content[:100]}..."
        return content
    content_preview.short_description = 'Content'
    
    def user_role(self, obj):
        """Show user role with color"""
        if obj.user.role == 'admin':
            return '<span style="background: #2196f3; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;">👨‍💼 Admin</span>'
        else:
            return '<span style="background: #ff9800; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;">👤 User</span>'
    user_role.short_description = 'Role'
    user_role.allow_tags = True


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
    list_display = ['filename', 'issue', 'admin', 'file_type', 'file_size_display', 'uploaded_at', 'quick_preview']
    list_filter = ['file_type', 'uploaded_at', 'admin']
    search_fields = ['filename', 'description', 'issue__title']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'file_size', 'file_preview', 'filename_display']
    
    fieldsets = (
        ('Evidence Information', {
            'fields': ('issue', 'admin', 'file_type', 'description')
        }),
        ('File Upload', {
            'fields': ('file', 'filename_display')
        }),
        ('File Details', {
            'fields': ('file_size', 'file_preview'),
            'classes': ('collapse',),
        }),
        ('Timestamp', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',),
        }),
    )
    
    def filename_display(self, obj):
        """Display filename with link if file exists"""
        if obj.file and hasattr(obj.file, 'url'):
            return f'<a href="{obj.file.url}" target="_blank">{obj.filename}</a>'
        return obj.filename or "No file uploaded"
    filename_display.short_description = 'Current File'
    filename_display.allow_tags = True
    
    def file_preview(self, obj):
        """Display file preview based on file type"""
        if not obj.file or not hasattr(obj.file, 'url'):
            return "No file uploaded"
        
        file_url = obj.file.url
        file_extension = obj.filename.split('.')[-1].lower() if obj.filename else ''
        
        # Image preview
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return f"""
            <div style='text-align: center;'>
                <img src="{file_url}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" />
                <br><br>
                <a href="{file_url}" target="_blank" style="background: #007cba; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">
                    🔗 View Full Image
                </a>
            </div>
            """
        
        # PDF preview
        elif file_extension == 'pdf':
            return f"""
            <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5;'>
                <div style="font-size: 48px; color: #dc3545;">📄</div>
                <p style="margin: 10px 0; color: #212529; font-weight: 500;">PDF Document</p>
                <a href="{file_url}" target="_blank" style="background: #dc3545; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-weight: 500;">
                    🔗 Open PDF
                </a>
            </div>
            """
        
        # Video preview
        elif file_extension in ['mp4', 'webm', 'ogg', 'mov']:
            return f"""
            <div style='text-align: center;'>
                <video controls style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;">
                    <source src="{file_url}" type="video/{file_extension}">
                    Your browser does not support the video tag.
                </video>
                <br><br>
                <a href="{file_url}" target="_blank" style="background: #28a745; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-weight: 500;">
                    🔗 Download Video
                </a>
            </div>
            """
        
        # Audio preview
        elif file_extension in ['mp3', 'wav', 'ogg', 'm4a']:
            return f"""
            <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5;'>
                <div style="font-size: 48px; color: #6f42c1;">🎵</div>
                <p style="margin: 10px 0; color: #212529; font-weight: 500;">Audio File</p>
                <audio controls style="width: 100%;">
                    <source src="{file_url}" type="audio/{file_extension}">
                    Your browser does not support the audio element.
                </audio>
                <br><br>
                <a href="{file_url}" target="_blank" style="background: #6f42c1; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-weight: 500;">
                    🔗 Download Audio
                </a>
            </div>
            """
        
        # Document preview
        elif file_extension in ['doc', 'docx', 'txt', 'rtf']:
            return f"""
            <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5;'>
                <div style="font-size: 48px; color: #17a2b8;">📝</div>
                <p style="margin: 10px 0; color: #212529; font-weight: 500;">Document</p>
                <a href="{file_url}" target="_blank" style="background: #17a2b8; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-weight: 500;">
                    🔗 Open Document
                </a>
            </div>
            """
        
        # Default file preview
        else:
            return f"""
            <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 4px; background: #f5f5f5;'>
                <div style="font-size: 48px; color: #495057;">📎</div>
                <p style="margin: 10px 0; color: #212529; font-weight: 500;">File: {obj.filename}</p>
                <a href="{file_url}" target="_blank" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; font-weight: 500;">
                    🔗 Download File
                </a>
            </div>
            """
    
    file_preview.short_description = 'File Preview'
    file_preview.allow_tags = True
    
    def quick_preview(self, obj):
        """Show quick file icon in list view"""
        if not obj.file or not hasattr(obj.file, 'url'):
            return "❌ No file"
        
        file_extension = obj.filename.split('.')[-1].lower() if obj.filename else ''
        
        # Return appropriate icon based on file type
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return '🖼️ Image'
        elif file_extension == 'pdf':
            return '📄 PDF'
        elif file_extension in ['mp4', 'webm', 'ogg', 'mov']:
            return '🎥 Video'
        elif file_extension in ['mp3', 'wav', 'ogg', 'm4a']:
            return '🎵 Audio'
        elif file_extension in ['doc', 'docx', 'txt', 'rtf']:
            return '📝 Document'
        else:
            return '📎 File'
    
    quick_preview.short_description = 'Type'
    
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
        """Set file size, filename, and admin on save"""
        if not change:  # Only for new objects
            obj.admin = request.user
        
        # Handle file upload
        if obj.file and hasattr(obj.file, 'name'):
            # Set filename from the uploaded file
            if not obj.filename:
                obj.filename = obj.file.name.split('/')[-1]  # Get just the filename
            
            # Set file size
            if hasattr(obj.file, 'size'):
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
