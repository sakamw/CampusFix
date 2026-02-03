from rest_framework import serializers
from .models import Issue, Comment, Attachment, Upvote
from accounts.serializers import UserSerializer


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
    assigned_to = UserSerializer(read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'assigned_to', 'created_at', 'updated_at', 
            'resolved_at', 'upvote_count', 'upvoted_by_user'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'upvote_count']
    
    def get_upvoted_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False


class IssueDetailSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'assigned_to', 'created_at', 'updated_at', 
            'resolved_at', 'upvote_count', 'upvoted_by_user', 'comments', 
            'attachments', 'comment_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'upvote_count']
    
    def get_upvoted_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False
    
    def get_comment_count(self, obj):
        return obj.comments.count()


class IssueCreateSerializer(serializers.ModelSerializer):
    reporter_id = serializers.IntegerField(write_only=True, required=False)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter_id', 'assigned_to_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Set reporter from request user if not provided
        if 'reporter_id' not in validated_data:
            validated_data['reporter'] = self.context['request'].user
        else:
            reporter_id = validated_data.pop('reporter_id')
            validated_data['reporter_id'] = reporter_id
        
        # Handle assigned_to
        if 'assigned_to_id' in validated_data:
            assigned_to_id = validated_data.pop('assigned_to_id')
            validated_data['assigned_to_id'] = assigned_to_id
        
        return super().create(validated_data)


class UpvoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Upvote
        fields = ['id', 'issue', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']
