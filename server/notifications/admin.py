from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'title', 'message', 'type')
        }),
        ('Status', {
            'fields': ('is_read', 'related_issue')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
