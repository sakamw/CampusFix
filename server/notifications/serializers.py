from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    # Backwards/clientside-friendly alias
    type = serializers.CharField(source='notification_type', read_only=True)
    related_issue_id = serializers.IntegerField(source='related_issue.id', read_only=True, allow_null=True)
    related_issue_title = serializers.CharField(source='related_issue.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'notification_type', 'type', 'is_read', 
            'related_issue', 'related_issue_id', 'related_issue_title', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_on_comment', 'email_on_status_change', 'email_on_assignment',
            'email_on_upvote', 'email_on_resolution', 'real_time_notifications',
            'daily_digest'
        ]
