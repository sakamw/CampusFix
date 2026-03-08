from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from .models import (
    Notification,
    NotificationPreference,
    Announcement,
    AnnouncementDismissal,
)
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    AnnouncementSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing notifications.
    Users can only see their own notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only return notifications for the current user
        return Notification.objects.filter(user=self.request.user).select_related('related_issue').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        List notifications for the current user.
        Supports `?limit=30` to cap results.
        """
        queryset = self.filter_queryset(self.get_queryset())
        limit = request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[: max(0, int(limit))]
            except (TypeError, ValueError):
                pass
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user."""
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({
            'message': f'{count} notifications marked as read',
            'success': True,
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification preferences."""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get or create notification preferences for the current user."""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    Announcements visible in the student dashboard and manageable by admins.
    """

    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Announcement.objects.filter(is_active=True)
        now = timezone.now()
        qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        # When listing for students, hide announcements they have dismissed
        if self.action == "list":
            qs = qs.exclude(dismissals__user=self.request.user)

        return qs.order_by("-created_at")

    def _ensure_admin(self, request):
        user = request.user
        role = getattr(user, "role", None)
        if not (user.is_superuser or role == "admin"):
            raise PermissionDenied("Admin access is required to manage announcements.")

    def perform_create(self, serializer):
        self._ensure_admin(self.request)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        self._ensure_admin(self.request)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        self._ensure_admin(request)
        # Soft-delete via is_active flag to keep history intact
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """
        Mark an announcement as dismissed for the current user so it no longer appears.
        """
        announcement = self.get_object()
        AnnouncementDismissal.objects.get_or_create(
            announcement=announcement,
            user=request.user,
        )
        return Response({"success": True})
