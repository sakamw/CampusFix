from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IssueViewSet, CommentViewSet, DashboardStatsView

router = DefaultRouter()
router.register(r'issues', IssueViewSet, basename='issue')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'dashboard', DashboardStatsView, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
