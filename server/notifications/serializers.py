from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    related_issue_id = serializers.IntegerField(source='related_issue.id', read_only=True, allow_null=True)
    related_issue_title = serializers.CharField(source='related_issue.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'title', 'message', 'type', 'is_read', 
            'related_issue', 'related_issue_id', 'related_issue_title', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user']
