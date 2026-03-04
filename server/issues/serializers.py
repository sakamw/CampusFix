from rest_framework import serializers
from .models import (
    Issue,
    Comment,
    Attachment,
    Upvote,
    ResolutionEvidence,
    ProgressUpdate,
    AdminWorkLog,
    IssueProgressLog,
)
from accounts.serializers import UserSerializer


class IssueProgressLogSerializer(serializers.ModelSerializer):
    staff = UserSerializer(read_only=True)

    class Meta:
        model = IssueProgressLog
        fields = ["id", "issue", "staff", "log_type", "description", "photo", "created_at"]
        read_only_fields = ["id", "issue", "staff", "created_at"]


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
        read_only_fields = ['id', 'created_at', 'admin']
    
    def create(self, validated_data):
        # Set admin from request context
        validated_data['admin'] = self.context['request'].user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'issue', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'issue', 'created_at', 'updated_at']
    
    def validate_content(self, value):
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Comment cannot be empty.")
        if len(value.strip()) > 2000:
            raise serializers.ValidationError("Comment cannot exceed 2000 characters.")
        return value
    
    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    uploaded_by_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Attachment
        fields = ['id', 'issue', 'file', 'filename', 'uploaded_by', 'uploaded_by_id', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class IssueListSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    verified_by = UserSerializer(read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    is_anonymous = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'created_at', 'updated_at',
            'resolved_at', 'upvote_count', 'upvoted_by_user', 'visibility',
            'is_anonymous',
            'progress_percentage', 'progress_status', 'progress_updated_at',
            'is_blocked', 'blocker_note', 'verified_at', 'verified_by'
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

    def to_representation(self, instance):
        """
        Hide reporter details for anonymous issues for non-superusers.
        """
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.is_anonymous and (not request or not request.user.is_superuser):
            data["reporter"] = {
                "id": None,
                "email": None,
                "first_name": "Anonymous",
                "last_name": "User",
                "student_id": None,
                "phone": None,
                "role": None,
                "avatar": None,
                "two_factor_enabled": False,
                "created_at": None,
                "is_superuser": False,
                "is_staff": False,
            }
        return data


class IssueDetailSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    verified_by = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    evidence_files = ResolutionEvidenceSerializer(many=True, read_only=True)
    progress_updates = ProgressUpdateSerializer(many=True, read_only=True)
    work_logs = AdminWorkLogSerializer(many=True, read_only=True)
    progress_logs = IssueProgressLogSerializer(many=True, read_only=True)
    upvoted_by_user = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_anonymous = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'reporter', 'created_at', 'updated_at', 
            'resolved_at', 'upvote_count', 'upvoted_by_user', 'comments', 
            'attachments', 'evidence_files', 'progress_updates', 'work_logs',
            'progress_logs',
            'comment_count', 'visibility', 'progress_percentage', 'progress_status', 
            'progress_notes', 'progress_updated_at', 'admin_notes', 'resolution_summary', 
            'resolution_details', 'estimated_resolution_text', 'estimated_completion', 'actual_completion', 
            'work_hours', 'resolution_cost', 'is_anonymous',
            'is_blocked', 'blocker_note', 'verified_by', 'verified_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'upvote_count', 'progress_updated_at']
    
    def get_upvoted_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.upvotes.filter(user=request.user).exists()
        return False
    
    def get_comment_count(self, obj):
        return obj.comments.count()

    def to_representation(self, instance):
        """
        Hide reporter details for anonymous issues for non-superusers.
        """
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.is_anonymous and (not request or not request.user.is_superuser):
            data["reporter"] = {
                "id": None,
                "email": None,
                "first_name": "Anonymous",
                "last_name": "User",
                "student_id": None,
                "phone": None,
                "role": None,
                "avatar": None,
                "two_factor_enabled": False,
                "created_at": None,
                "is_superuser": False,
                "is_staff": False,
            }
        return data


class IssueCreateSerializer(serializers.ModelSerializer):
    reporter_id = serializers.IntegerField(write_only=True, required=False)
    report_anonymously = serializers.BooleanField(write_only=True, required=False, default=False)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'category', 'status', 'priority', 
            'location', 'visibility', 'reporter_id', 'report_anonymously',
            'created_at', 'updated_at', 'progress_percentage', 'progress_status', 
            'progress_notes', 'admin_notes', 'resolution_summary', 'resolution_details', 
            'estimated_completion', 'actual_completion', 'work_hours', 'resolution_cost'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'progress_updated_at']
    
    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value
    
    def validate_description(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return value
    
    def validate_location(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Location must be at least 3 characters long.")
        return value
    
    def create(self, validated_data):
        # Handle anonymous reporting flag
        report_anonymously = validated_data.pop('report_anonymously', False)

        # Set reporter from request user if not provided
        if 'reporter_id' not in validated_data:
            validated_data['reporter'] = self.context['request'].user
        else:
            reporter_id = validated_data.pop('reporter_id')
            validated_data['reporter_id'] = reporter_id

        validated_data['is_anonymous'] = bool(report_anonymously)

        return super().create(validated_data)


class IssueUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer with role-based field protections.
    - Staff/admin users can update operational/admin fields (status, estimates, resolution info, progress).
    - Non-staff users can only update their own issue's basic editable fields.
    """

    class Meta:
        model = Issue
        fields = [
            'title', 'description', 'category', 'priority',
            'location', 'visibility',
            # Operational/admin fields
            'status',
            'estimated_resolution_text',
            'estimated_completion',
            'actual_completion',
            'progress_percentage', 'progress_status', 'progress_notes',
            'admin_notes', 'resolution_summary', 'resolution_details',
            'work_hours', 'resolution_cost',
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        instance = getattr(self, 'instance', None)

        if not user or not user.is_authenticated:
            return attrs

        # Non-staff can only edit their own issue
        if not user.is_staff:
            if not instance or instance.reporter_id != user.id:
                raise serializers.ValidationError("You do not have permission to update this issue.")

            admin_only_fields = {
                'status',
                'estimated_resolution_text',
                'estimated_completion',
                'actual_completion',
                'progress_percentage', 'progress_status', 'progress_notes',
                'admin_notes', 'resolution_summary', 'resolution_details',
                'work_hours', 'resolution_cost',
            }

            forbidden = admin_only_fields.intersection(self.initial_data.keys())
            if forbidden:
                raise serializers.ValidationError(
                    "You do not have permission to update administrative fields on this issue."
                )

        return attrs


class UpvoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Upvote
        fields = ['id', 'issue', 'user', 'created_at']
        read_only_fields = ['id', 'created_at']
