from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import (
    Issue,
    Comment,
    Attachment,
    Upvote,
    ResolutionEvidence,
    ProgressUpdate,
    AdminWorkLog,
    IssueFeedback,
)
from .serializers import (
    IssueListSerializer,
    IssueDetailSerializer,
    IssueCreateSerializer,
    IssueUpdateSerializer,
    CommentSerializer,
    AttachmentSerializer,
    UpvoteSerializer,
    AdminWorkLogSerializer,
)


class IssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing issues.
    Supports listing, creating, retrieving, updating, and deleting issues.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'reporter']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['created_at', 'updated_at', 'upvote_count', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Issue.objects.all().select_related('reporter').prefetch_related(
            'upvotes', 'comments', 'attachments', 'evidence_files', 'progress_updates', 'work_logs'
        )

        # Visibility / access rules:
        # - Staff can only see issues assigned to them
        # - Admins/superusers can see all issues
        # - Non-staff can see public issues, plus any issues they reported
        role = getattr(self.request.user, "role", None)
        if self.request.user.is_staff and not self.request.user.is_superuser and role == "staff":
            queryset = queryset.filter(assigned_to=self.request.user)
        elif not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(visibility='public') | Q(reporter=self.request.user)
            )
        
        # Allow filtering by 'my-issues'
        filter_type = getattr(self.request, 'query_params', {}).get('filter', None)
        if filter_type == 'my-issues':
            queryset = queryset.filter(reporter=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return IssueDetailSerializer
        elif self.action == 'create':
            return IssueCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return IssueUpdateSerializer
        return IssueListSerializer
    
    def perform_create(self, serializer):
        # Apply rate limiting for issue creation
        from django.core.cache import cache
        
        rate_limit_key = f'issue_rate_limit:{self.request.user.id}'
        request_count = cache.get(rate_limit_key, 0)
        
        if request_count >= 10:  # 10 issues per hour
            from rest_framework.exceptions import Throttled
            raise Throttled(detail="You have reached the maximum number of issues you can create per hour. Please wait before creating a new issue.")
        
        # Increment counter
        cache.set(rate_limit_key, request_count + 1, 3600)  # 1 hour expiry
        
        serializer.save(reporter=self.request.user)
    
    @action(detail=True, methods=['post'])
    def upvote(self, request, pk=None):
        """Toggle upvote on an issue."""
        issue = self.get_object()
        user = request.user
        
        # Check if user already upvoted
        upvote = Upvote.objects.filter(issue=issue, user=user).first()
        
        if upvote:
            # Remove upvote
            upvote.delete()
            issue.upvote_count = max(0, issue.upvote_count - 1)
            issue.save()
            return Response({'message': 'Upvote removed', 'upvoted': False, 'upvote_count': issue.upvote_count})
        else:
            # Add upvote
            Upvote.objects.create(issue=issue, user=user)
            issue.upvote_count += 1
            issue.save()
            return Response({'message': 'Upvoted successfully', 'upvoted': True, 'upvote_count': issue.upvote_count})
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        """Upload one or more attachments for an issue.
        
        Constraints:
        - Maximum 5 attachments per issue
        - Each file is validated by validate_file_upload (size/type)
        """
        issue = self.get_object()
        files = request.FILES.getlist('files')
        
        if not files:
            return Response(
                {'error': 'No files were uploaded. Use the "files" field in multipart form data.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        max_attachments = 5
        existing_count = issue.attachments.count()
        if existing_count + len(files) > max_attachments:
            return Response(
                {
                    'error': 'Attachment limit exceeded.',
                    'detail': f'Each issue can have at most {max_attachments} attachments. '
                              f'This issue already has {existing_count} attachment(s).',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Build payload for serializer
        payload = [
            {
                'issue': issue.id,
                'file': uploaded_file,
                'filename': uploaded_file.name,
            }
            for uploaded_file in files
        ]
        
        serializer = AttachmentSerializer(
            data=payload,
            many=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        attachments = serializer.save(uploaded_by=request.user)
        
        return Response(
            AttachmentSerializer(attachments, many=True, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments for an issue."""
        issue = self.get_object()
        
        if request.method == 'GET':
            comments = issue.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Only:
            # - the reporter, OR
            # - admins/superusers, OR
            # - assigned staff member
            role = getattr(request.user, "role", None)
            is_admin = request.user.is_superuser or role == "admin"
            is_assigned_staff = role == "staff" and issue.assigned_to_id == request.user.id
            if not (is_admin or is_assigned_staff or issue.reporter_id == request.user.id):
                return Response(
                    {'error': 'You do not have permission to comment on this issue.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Apply rate limiting for POST requests
            from django.core.cache import cache
            from django.http import HttpResponse
            
            # Simple rate limiting check
            rate_limit_key = f'comment_rate_limit:{request.user.id}'
            request_count = cache.get(rate_limit_key, 0)
            
            if request_count >= 30:  # 30 comments per hour
                return Response(
                    {
                        'error': 'Rate limit exceeded',
                        'message': 'You have reached the maximum number of comments per hour. Please wait before posting again.'
                    },
                    status=429
                )
            
            # Increment counter
            cache.set(rate_limit_key, request_count + 1, 3600)  # 1 hour expiry
            
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(issue=issue)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_update(self, serializer):
        """Override to handle status changes and create notifications."""
        obj = self.get_object()
        old_status = obj.status

        # Attach modifier for signals-based notifications
        obj._modified_by_user = self.request.user  # type: ignore[attr-defined]

        instance = serializer.save()
        
        # If status changed, create notifications
        if old_status != instance.status:
            pass

        # Update resolved_at timestamp
        if instance.status == 'resolved' and not instance.resolved_at:
            instance.resolved_at = timezone.now()
            instance.save()
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get timeline events for an issue."""
        issue = self.get_object()
        events = []
        
        # Issue creation event
        events.append({
            'id': f'issue_{issue.id}',
            'type': 'issue_created',
            'title': 'Issue Created',
            'description': f'Issue "{issue.title}" was reported in {issue.get_category_display()} category',
            'timestamp': issue.created_at.isoformat(),
            'user': {
                'first_name': issue.reporter.first_name,
                'last_name': issue.reporter.last_name,
                'email': issue.reporter.email,
            },
            'metadata': {
                'category': issue.get_category_display(),
                'priority': issue.get_priority_display(),
            }
        })
        
        # Work logs
        work_logs = issue.work_logs.all().order_by('created_at')
        for log in work_logs:
            # Handle case where admin might be None
            admin_user = log.admin if log.admin else issue.reporter
            
            events.append({
                'id': f'worklog_{log.id}',
                'type': 'work_log',
                'title': f'Work Logged: {log.get_work_type_display()}',
                'description': log.description,
                'timestamp': log.created_at.isoformat(),
                'user': {
                    'first_name': admin_user.first_name,
                    'last_name': admin_user.last_name,
                    'email': admin_user.email,
                },
                'metadata': {
                    'work_type': log.get_work_type_display(),
                    'hours_spent': float(log.hours_spent),
                }
            })
        
        # Progress updates
        progress_updates = issue.progress_updates.all().order_by('created_at')
        for update in progress_updates:
            # Handle case where admin might be None
            admin_user = update.admin if update.admin else issue.reporter
            
            events.append({
                'id': f'progress_{update.id}',
                'type': 'progress_update',
                'title': update.title,
                'description': update.description,
                'timestamp': update.created_at.isoformat(),
                'user': {
                    'first_name': admin_user.first_name,
                    'last_name': admin_user.last_name,
                    'email': admin_user.email,
                },
                'metadata': {
                    'progress_percentage': update.progress_percentage,
                    'update_type': update.get_update_type_display(),
                    'is_major_update': update.is_major_update,
                }
            })
        
       # For now, we'll show the current status if it's not the initial 'open' status
        if issue.status != 'open':
            events.append({
                'id': f'status_{issue.id}',
                'type': 'status_change',
                'title': 'Status Changed',
                'description': f'Issue status changed to {issue.get_status_display()}',
                'timestamp': issue.updated_at.isoformat(),
                'user': {
                    'first_name': issue.reporter.first_name,
                    'last_name': issue.reporter.last_name,
                    'email': issue.reporter.email,
                },
                'metadata': {
                    'new_status': issue.get_status_display(),
                }
            })
        
        # Resolution evidence uploads
        evidence_files = issue.evidence_files.all().order_by('uploaded_at')
        for evidence in evidence_files:
            # Handle case where admin might be None
            admin_user = evidence.admin if evidence.admin else issue.reporter
            
            events.append({
                'id': f'evidence_{evidence.id}',
                'type': 'evidence_uploaded',
                'title': f'Evidence Uploaded: {evidence.get_file_type_display()}',
                'description': evidence.description or f'File "{evidence.filename}" uploaded as evidence',
                'timestamp': evidence.uploaded_at.isoformat(),
                'user': {
                    'first_name': admin_user.first_name,
                    'last_name': admin_user.last_name,
                    'email': admin_user.email,
                },
                'metadata': {
                    'file_type': evidence.get_file_type_display(),
                    'filename': evidence.filename,
                    'file_size': evidence.file_size,
                }
            })
        
        # Issue resolution
        if issue.status in ['resolved', 'closed'] and issue.resolved_at:
            events.append({
                'id': f'resolved_{issue.id}',
                'type': 'issue_resolved',
                'title': 'Issue Resolved',
                'description': issue.resolution_summary or f'Issue marked as {issue.get_status_display()}',
                'timestamp': issue.resolved_at.isoformat(),
                'user': {
                    'first_name': issue.reporter.first_name,
                    'last_name': issue.reporter.last_name,
                    'email': issue.reporter.email,
                },
                'metadata': {
                    'final_status': issue.get_status_display(),
                }
            })
        
        # Sort all events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return Response(events)

    @action(detail=True, methods=["post"])
    def submit_feedback(self, request, pk=None):
        """
        Submit or update post-resolution feedback for an issue by its reporter.

        Expected payload:
        {
            "rating": 1-5,
            "comment": "optional text"
        }
        """
        issue = self.get_object()
        user = request.user

        # Only the original reporter can submit feedback
        if issue.reporter_id != user.id:
            return Response(
                {
                    "error": "Only the original reporter can submit feedback for this issue."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only allow feedback once the issue is resolved/closed
        if issue.status not in ["resolved", "closed"]:
            return Response(
                {
                    "error": "Feedback can only be submitted after the issue is resolved or closed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data or {}
        try:
            rating = int(data.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            return Response(
                {"error": "Rating must be an integer between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = (data.get("comment") or "").strip()

        feedback, _created = IssueFeedback.objects.update_or_create(
            issue=issue,
            user=user,
            defaults={
                "rating": rating,
                "comment": comment,
            },
        )

        # Optionally return simple aggregates for UI (not strictly required by client)
        agg = IssueFeedback.objects.filter(issue=issue).aggregate(
            avg_rating=Avg("rating"),
            count=Count("id"),
        )

        return Response(
            {
                "success": True,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "created_at": feedback.created_at,
                "feedback_count": agg.get("count") or 0,
                "average_rating": agg.get("avg_rating"),
            }
        )

    @action(detail=True, methods=['get', 'post'])
    def work_logs(self, request, pk=None):
        """Get or add work logs for an issue."""
        issue = self.get_object()
        
        if request.method == 'GET':
            work_logs = issue.work_logs.all()
            serializer = AdminWorkLogSerializer(work_logs, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Only admins can add work logs
            if not request.user.is_staff:
                return Response(
                    {'error': 'Admin access required to add work logs'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = AdminWorkLogSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(issue=issue)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing comments."""
    queryset = Comment.objects.all().select_related('user', 'issue')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        role = getattr(self.request.user, "role", None)
        if self.request.user.is_staff and not self.request.user.is_superuser and role == "staff":
            return qs.filter(issue__assigned_to=self.request.user)
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(issue__visibility='public') | Q(issue__reporter=self.request.user))
    
    def perform_create(self, serializer):
        issue = serializer.validated_data.get('issue')
        role = getattr(self.request.user, "role", None)
        is_admin = self.request.user.is_superuser or role == "admin"
        is_assigned_staff = role == "staff" and issue and issue.assigned_to_id == self.request.user.id
        if issue and not (is_admin or is_assigned_staff or issue.reporter_id == self.request.user.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to comment on this issue.")
        serializer.save(user=self.request.user)


class DashboardStatsView(viewsets.ViewSet):
    """ViewSet for dashboard statistics."""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics for the current user."""
        user = request.user
        
        # Get user's issues
        user_issues = Issue.objects.filter(reporter=user)
        
        # Calculate statistics
        total_issues = user_issues.count()
        open_issues = user_issues.filter(status='open').count()
        in_progress_issues = user_issues.filter(status='in-progress').count()
        resolved_issues = user_issues.filter(status='resolved').count()
        closed_issues = user_issues.filter(status='closed').count()
        
        # Calculate resolution rate
        completed = resolved_issues + closed_issues
        resolution_rate = (completed / total_issues * 100) if total_issues > 0 else 0
        
        # Calculate average response time (time from created to first comment or status change)
        resolved_with_time = user_issues.filter(
            status__in=['resolved', 'closed'],
            resolved_at__isnull=False
        )
        
        if resolved_with_time.exists():
            avg_seconds = sum([
                (issue.resolved_at - issue.created_at).total_seconds()
                for issue in resolved_with_time
            ]) / resolved_with_time.count()
            avg_response_hours = avg_seconds / 3600
        else:
            avg_response_hours = 0
        
        return Response({
            'total_issues': total_issues,
            'open_issues': open_issues,
            'in_progress_issues': in_progress_issues,
            'resolved_issues': resolved_issues,
            'closed_issues': closed_issues,
            'resolution_rate': round(resolution_rate, 1),
            'avg_response_time_hours': round(avg_response_hours, 1),
        })
    
    @action(detail=False, methods=['get'])
    def recent_issues(self, request):
        """Get recent issues for the dashboard."""
        user = request.user
        limit = int(request.query_params.get('limit', 5))
        
        # Get user's recent issues
        issues = Issue.objects.filter(reporter=user).order_by('-created_at')[:limit]
        serializer = IssueListSerializer(issues, many=True, context={'request': request})
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def admin_stats(self, request):
        """Get campus-wide statistics for admins."""
        role = getattr(request.user, "role", None)
        if not (request.user.is_superuser or role == "admin"):
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        # Get all issues
        all_issues = Issue.objects.all()
        
        # Calculate statistics
        total_issues = all_issues.count()
        open_issues = all_issues.filter(status='open').count()
        in_progress_issues = all_issues.filter(status='in-progress').count()
        resolved_issues = all_issues.filter(status='resolved').count()
        closed_issues = all_issues.filter(status='closed').count()
        
        # Resolution rate
        completed = resolved_issues + closed_issues
        resolution_rate = (completed / total_issues * 100) if total_issues > 0 else 0
        
        # Category breakdown
        category_stats = all_issues.values('category').annotate(count=Count('id'))
        
        # Priority breakdown
        priority_stats = all_issues.values('priority').annotate(count=Count('id'))
        
        return Response({
            'total_issues': total_issues,
            'open_issues': open_issues,
            'in_progress_issues': in_progress_issues,
            'resolved_issues': resolved_issues,
            'closed_issues': closed_issues,
            'resolution_rate': round(resolution_rate, 1),
            'category_stats': list(category_stats),
            'priority_stats': list(priority_stats),
        })
