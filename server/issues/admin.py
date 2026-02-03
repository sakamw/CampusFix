from django.contrib import admin
from .models import Issue, Comment, Attachment, Upvote


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'status', 'priority', 'reporter', 'assigned_to', 'created_at', 'upvote_count']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['title', 'description', 'location']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'upvote_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'location')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Assignment', {
            'fields': ('reporter', 'assigned_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'upvote_count')
        }),
    )


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
