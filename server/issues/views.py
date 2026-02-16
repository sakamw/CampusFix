from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Issue, Comment, Attachment, Upvote, ResolutionEvidence, ProgressUpdate, AdminWorkLog
from .serializers import (
    IssueListSerializer,
    IssueDetailSerializer,
    IssueCreateSerializer,
    CommentSerializer,
    AttachmentSerializer,
    UpvoteSerializer,
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
        
        # Allow filtering by 'my-issues'
        filter_type = getattr(self.request, 'query_params', {}).get('filter', None)
        if filter_type == 'my-issues':
            queryset = queryset.filter(reporter=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return IssueDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return IssueCreateSerializer
        return IssueListSerializer
    
    def perform_create(self, serializer):
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
            
            # Create notification for issue reporter
            from notifications.models import Notification
            if issue.reporter != user:
                Notification.objects.create(
                    user=issue.reporter,
                    title='New Upvote',
                    message=f'{user.first_name} {user.last_name} upvoted your issue: {issue.title}',
                    type='upvote',
                    related_issue=issue
                )
            
            return Response({'message': 'Upvoted successfully', 'upvoted': True, 'upvote_count': issue.upvote_count})
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments for an issue."""
        issue = self.get_object()
        
        if request.method == 'GET':
            comments = issue.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(issue=issue)
                
                # Create notifications for issue reporter and all admins
                from notifications.models import Notification
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                recipients = set()
                
                # Notify issue reporter if they didn't post the comment
                if issue.reporter != request.user:
                    recipients.add(issue.reporter)
                
                # Notify all admin users (except the commenter if they're an admin)
                admin_users = User.objects.filter(role='admin')
                for admin in admin_users:
                    if admin != request.user:
                        recipients.add(admin)
                
                for recipient in recipients:
                    # Customize message based on recipient type
                    if recipient == issue.reporter:
                        message = f'{request.user.first_name} {request.user.last_name} commented on your issue: {issue.title}'
                    else:
                        message = f'New comment from {request.user.first_name} {request.user.last_name} on issue: {issue.title}'
                    
                    Notification.objects.create(
                        user=recipient,
                        title='New Comment',
                        message=message,
                        type='comment',
                        related_issue=issue
                    )
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_update(self, serializer):
        """Override to handle status changes and create notifications."""
        old_status = self.get_object().status
        instance = serializer.save()
        
        # If status changed, create notifications
        if old_status != instance.status:
            from notifications.models import Notification
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            recipients = set()
            
            # Notify reporter if they didn't make the change
            if instance.reporter != self.request.user:
                recipients.add(instance.reporter)
            
            # Notify all admin users (except the changer if they're an admin)
            admin_users = User.objects.filter(role='admin')
            for admin in admin_users:
                if admin != self.request.user:
                    recipients.add(admin)
            
            for recipient in recipients:
                # Customize message based on recipient type and who made the change
                if recipient == instance.reporter:
                    if self.request.user == instance.reporter:
                        message = f'You changed your issue "{instance.title}" status to {instance.get_status_display()}'
                    else:
                        message = f'Your issue "{instance.title}" status was changed to {instance.get_status_display()} by {self.request.user.first_name} {self.request.user.last_name}'
                    title = 'Issue Status Updated'
                else:
                    # Admin notification
                    if self.request.user.role == 'admin':
                        message = f'Admin {self.request.user.first_name} {self.request.user.last_name} changed issue "{instance.title}" status to {instance.get_status_display()}'
                    else:
                        message = f'User {self.request.user.first_name} {self.request.user.last_name} marked issue "{instance.title}" as {instance.get_status_display()}'
                    title = 'Issue Status Changed'
                
                Notification.objects.create(
                    user=recipient,
                    title=title,
                    message=message,
                    type='status_change',
                    related_issue=instance
                )
            
            # Update resolved_at timestamp
            if instance.status == 'resolved' and not instance.resolved_at:
                instance.resolved_at = timezone.now()
                instance.save()


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing comments."""
    queryset = Comment.objects.all().select_related('user', 'issue')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
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
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
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
