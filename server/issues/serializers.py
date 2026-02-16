from rest_framework import serializers
from .models import Issue, Comment, Attachment, Upvote, ResolutionEvidence, ProgressUpdate, AdminWorkLog
from accounts.serializers import UserSerializer


class ResolutionEvidenceSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ResolutionEvidence
        fields = ['id', 'issue', 'file', 'filename', 'description', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ProgressUpdateSerializer(serializers.ModelSerializer):
    admin = UserSerializer(read_only=True)
    
    class Meta:
        model = ProgressUpdate
        fields = [
            'id', 'issue', 'admin', 'update_type', 'progress_percentage', 
            'title', 'description', 'next_steps', 'estimated_completion', 
            'is_major_update', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AdminWorkLogSerializer(serializers.ModelSerializer):
    admin = UserSerializer(read_only=True)
    
    class Meta:
        model = AdminWorkLog
        fields = [
            'id', 'issue', 'admin', 'work_type', 'hours_spent', 'description', 
            'materials_used', 'outcome', 'next_steps', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Comment
        fields = ['id', 'issue', 'user', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    uploaded_by_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Attachment
        fields = ['id', 'issue', 'file', 'filename', 'uploaded_by', 'uploaded_by_id', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class IssueListSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'created_at', 'updated_at', 
            'resolved_at', 'upvote_count', 'upvoted_by_user', 'visibility',
            'progress_percentage', 'progress_status', 'progress_updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'upvote_count', 'progress_updated_at']
        extra_kwargs = {
            'visibility': {'required': False}
        }
    
    def get_upvoted_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False


class IssueDetailSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    evidence_files = ResolutionEvidenceSerializer(many=True, read_only=True)
    progress_updates = ProgressUpdateSerializer(many=True, read_only=True)
    work_logs = AdminWorkLogSerializer(many=True, read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'created_at', 'updated_at', 
            'resolved_at', 'upvote_count', 'upvoted_by_user', 'comments', 
            'attachments', 'evidence_files', 'progress_updates', 'work_logs',
            'comment_count', 'visibility', 'progress_percentage', 'progress_status', 
            'progress_notes', 'progress_updated_at', 'admin_notes', 'resolution_summary', 
            'resolution_details', 'estimated_completion', 'actual_completion', 
            'work_hours', 'resolution_cost'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'upvote_count', 'progress_updated_at']
    
    def get_upvoted_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False
    
    def get_comment_count(self, obj):
        return obj.comments.count()


class IssueCreateSerializer(serializers.ModelSerializer):
    reporter_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'visibility', 'reporter_id', 
            'created_at', 'updated_at', 'progress_percentage', 'progress_status', 
            'progress_notes', 'admin_notes', 'resolution_summary', 'resolution_details', 
            'estimated_completion', 'actual_completion', 'work_hours', 'resolution_cost'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'progress_updated_at']
    
    def create(self, validated_data):
        # Set reporter from request user if not provided
        if 'reporter_id' not in validated_data:
            validated_data['reporter'] = self.context['request'].user
        else:
            reporter_id = validated_data.pop('reporter_id')
            validated_data['reporter_id'] = reporter_id
        
        return super().create(validated_data)


class UpvoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Upvote
        fields = ['id', 'issue', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']
