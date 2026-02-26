from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IssueViewSet, CommentViewSet, DashboardStatsView
from .admin_views import (
    admin_dashboard_api, resolution_analytics, 
    campus_hotspots, performance_metrics
)

router = DefaultRouter()
router.register(r'issues', IssueViewSet, basename='issue')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'dashboard', DashboardStatsView, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/dashboard/', admin_dashboard_api, name='admin_dashboard_api'),
    path('admin/analytics/resolution/', resolution_analytics, name='resolution_analytics'),
    path('admin/analytics/hotspots/', campus_hotspots, name='campus_hotspots'),
    path('admin/analytics/performance/', performance_metrics, name='performance_metrics'),
]
