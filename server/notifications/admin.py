from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Status', {
            'fields': ('is_read', 'related_issue')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'real_time_notifications', 'daily_digest', 'email_on_comment', 'email_on_status_change']
    list_filter = ['real_time_notifications', 'daily_digest', 'email_on_comment', 'email_on_status_change']
    search_fields = ['user__email']
    ordering = ['user__email']
