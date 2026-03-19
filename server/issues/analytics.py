from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField, Sum
from django.db.models.functions import TruncDate, TruncHour, ExtractHour
from django.utils import timezone
from datetime import timedelta, date
from .models import Issue, Comment, Upvote, AdminWorkLog, ProgressUpdate, IssueFeedback
from accounts.models import User


class AnalyticsService:
    """Service for generating analytics data."""
    
    @staticmethod
    def get_dashboard_overview():
        """Get overview statistics for dashboard."""
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        return {
            'issues': {
                'total': Issue.objects.count(),
                'open': Issue.objects.filter(status='open').count(),
                'in_progress': Issue.objects.filter(status='in-progress').count(),
                'resolved': Issue.objects.filter(status='resolved').count(),
                'closed': Issue.objects.filter(status='closed').count(),
                'last_24h': Issue.objects.filter(created_at__gte=last_24h).count(),
                'last_7d': Issue.objects.filter(created_at__gte=last_7d).count(),
                'last_30d': Issue.objects.filter(created_at__gte=last_30d).count(),
            },
            'users': {
                'total': User.objects.count(),
                'active_last_24h': User.objects.filter(last_login__gte=last_24h).count(),
                'active_last_7d': User.objects.filter(last_login__gte=last_7d).count(),
                'staff': User.objects.filter(is_staff=True).count(),
            },
            'engagement': {
                'total_comments': Comment.objects.count(),
                'total_upvotes': Upvote.objects.count(),
                'comments_last_24h': Comment.objects.filter(created_at__gte=last_24h).count(),
                'upvotes_last_24h': Upvote.objects.filter(created_at__gte=last_24h).count(),
            },
            'work_logs': {
                'total_hours': AdminWorkLog.objects.aggregate(
                    total=Sum('hours_spent')
                )['total'] or 0,
                'logs_last_7d': AdminWorkLog.objects.filter(
                    created_at__gte=last_7d
                ).count(),
            }
        }
    
    @staticmethod
    def get_resolution_time_analytics():
        """Get resolution time analytics."""
        resolved_issues = Issue.objects.filter(
            status='resolved',
            resolved_at__isnull=False
        ).annotate(
            resolution_time=ExpressionWrapper(
                F('resolved_at') - F('created_at'),
                output_field=DurationField()
            )
        )
        
        # Average resolution time by priority
        priority_stats = resolved_issues.values('priority').annotate(
            avg_resolution_time=Avg('resolution_time'),
            count=Count('id')
        ).order_by('priority')
        
        # Average resolution time by category
        category_stats = resolved_issues.values('category').annotate(
            avg_resolution_time=Avg('resolution_time'),
            count=Count('id')
        ).order_by('-count')
        
        # Resolution time trend (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_resolution_times = resolved_issues.filter(
            resolved_at__gte=thirty_days_ago
        ).annotate(
            resolved_date=TruncDate('resolved_at')
        ).values('resolved_date').annotate(
            avg_resolution_time=Avg('resolution_time'),
            count=Count('id')
        ).order_by('resolved_date')
        
        return {
            'overall_avg': resolved_issues.aggregate(
                avg_resolution_time=Avg('resolution_time')
            )['avg_resolution_time'],
            'by_priority': list(priority_stats),
            'by_category': list(category_stats),
            'daily_trend': list(daily_resolution_times),
            'total_resolved': resolved_issues.count(),
        }
    
    @staticmethod
    def get_campus_hotspot_analysis():
        """Analyze issue hotspots across campus locations."""
        # Issues by location
        location_stats = Issue.objects.values('location').annotate(
            total_issues=Count('id'),
            open_issues=Count('id', filter=Q(status='open')),
            resolved_issues=Count('id', filter=Q(status='resolved')),
            avg_priority=Avg(
                Case(
                    When(priority='low', then=Value(1)),
                    When(priority='medium', then=Value(2)),
                    When(priority='high', then=Value(3)),
                    When(priority='critical', then=Value(4)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
        ).order_by('-total_issues')
        
        # Issues by category and location
        category_location_matrix = Issue.objects.values(
            'location', 'category'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent activity by location
        last_7d = timezone.now() - timedelta(days=7)
        recent_activity = Issue.objects.filter(
            created_at__gte=last_7d
        ).values('location').annotate(
            recent_issues=Count('id'),
            urgent_issues=Count('id', filter=Q(priority__in=['high', 'critical']))
        ).order_by('-recent_issues')
        
        return {
            'location_stats': list(location_stats),
            'category_location_matrix': list(category_location_matrix),
            'recent_activity': list(recent_activity),
        }
    
    @staticmethod
    def get_performance_metrics():
        """Get performance metrics for staff and processes."""
        # Staff performance
        staff_performance = User.objects.filter(
            is_staff=True,
            work_logs__isnull=False
        ).annotate(
            total_issues_assigned=Count('assigned_issues', distinct=True),
            total_hours_worked=Sum('work_logs__hours_spent'),
            avg_resolution_time=Avg(
                'assigned_issues__resolved_at' - F('assigned_issues__created_at')
            ),
            total_work_logs=Count('work_logs')
        ).order_by('-total_hours_worked')
        
        # Response time analysis (time to first comment/admin action)
        response_times = Issue.objects.annotate(
            first_comment_time=Min('comments__created_at'),
            response_time=ExpressionWrapper(
                Min('comments__created_at') - F('created_at'),
                output_field=DurationField()
            )
        ).filter(
            first_comment_time__isnull=False
        ).aggregate(
            avg_response_time=Avg('response_time'),
            min_response_time=Min('response_time'),
            max_response_time=Max('response_time')
        )
        
        # Workload distribution
        workload_distribution = AdminWorkLog.objects.values(
            'admin__email'
        ).annotate(
            total_hours=Sum('hours_spent'),
            total_logs=Count('id'),
            avg_hours_per_log=Avg('hours_spent')
        ).order_by('-total_hours')
        
        return {
            'staff_performance': list(staff_performance),
            'response_times': response_times,
            'workload_distribution': list(workload_distribution),
        }
    
    @staticmethod
    def get_time_series_data(days=30):
        """Get time series data for various metrics."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Daily issue creation
        daily_issues = Issue.objects.filter(
            created_at__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            open_count=Count('id', filter=Q(status='open')),
            resolved_count=Count('id', filter=Q(status='resolved'))
        ).order_by('date')
        
        # Hourly activity pattern
        hourly_activity = Issue.objects.annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        # Weekly trends
        weekly_trends = Issue.objects.filter(
            created_at__gte=start_date
        ).annotate(
            week_day=ExtractWeekDay('created_at')
        ).values('week_day').annotate(
            count=Count('id'),
            resolved_count=Count('id', filter=Q(status='resolved'))
        ).order_by('week_day')
        
        return {
            'daily_issues': list(daily_issues),
            'hourly_activity': list(hourly_activity),
            'weekly_trends': list(weekly_trends),
        }

    @staticmethod
    def get_feedback_analytics():
        """
        Get aggregate analytics for post-resolution feedback and staff ratings.
        """
        feedback_qs = IssueFeedback.objects.all()
        total_feedback = feedback_qs.count()
        overall_avg = feedback_qs.aggregate(avg=Avg("rating"))["avg"]

        staff_ratings = (
            IssueFeedback.objects.filter(issue__assigned_to__isnull=False)
            .values(
                "issue__assigned_to__id",
                "issue__assigned_to__first_name",
                "issue__assigned_to__last_name",
                "issue__assigned_to__email",
            )
            .annotate(
                avg_rating=Avg("rating"),
                rating_count=Count("id"),
            )
            .order_by("-avg_rating", "-rating_count")
        )

        return {
            "total_feedback": total_feedback,
            "overall_average": overall_avg,
            "staff_ratings": list(staff_ratings),
        }


from django.db.models import Sum, Min, Max, StdDev, Variance, Case, When, Value, IntegerField
from django.db.models.functions import ExtractWeekDay
