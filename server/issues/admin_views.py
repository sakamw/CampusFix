from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Issue, AdminWorkLog, ProgressUpdate
from .forms import AdminWorkLogForm, ProgressUpdateForm
from .analytics import AnalyticsService


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    """Admin dashboard view"""
    context = {
        'total_issues': Issue.objects.count(),
        'open_issues': Issue.objects.filter(status='open').count(),
        'in_progress_issues': Issue.objects.filter(status='in-progress').count(),
        'resolved_issues': Issue.objects.filter(status='resolved').count(),
        'recent_work_logs': AdminWorkLog.objects.select_related('issue', 'admin').order_by('-created_at')[:10],
    }
    return render(request, 'admin/admin_dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_api(request):
    """API endpoint for real-time admin dashboard data"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    analytics = AnalyticsService()
    
    return Response({
        'overview': analytics.get_dashboard_overview(),
        'resolution_times': analytics.get_resolution_time_analytics(),
        'campus_hotspots': analytics.get_campus_hotspot_analysis(),
        'performance_metrics': analytics.get_performance_metrics(),
        'time_series': analytics.get_time_series_data(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resolution_analytics(request):
    """API endpoint for resolution time analytics"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    analytics = AnalyticsService()
    return Response(analytics.get_resolution_time_analytics())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def campus_hotspots(request):
    """API endpoint for campus hotspot analysis"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    analytics = AnalyticsService()
    return Response(analytics.get_campus_hotspot_analysis())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_metrics(request):
    """API endpoint for performance metrics"""
    if not request.user.is_staff:
        return Response({'error': 'Admin access required'}, status=403)
    
    analytics = AnalyticsService()
    return Response(analytics.get_performance_metrics())


@login_required
@user_passes_test(lambda u: u.is_staff)
def issue_work_logs(request, issue_id):
    """View and manage work logs for a specific issue"""
    issue = get_object_or_404(Issue, id=issue_id)
    work_logs = issue.work_logs.all().select_related('admin').order_by('-created_at')
    
    if request.method == 'POST':
        form = AdminWorkLogForm(request.POST)
        if form.is_valid():
            work_log = form.save(commit=False)
            work_log.issue = issue
            work_log.admin = request.user
            work_log.save()
            
            messages.success(request, f'Work log added for issue: {issue.title}')
            return redirect('admin_issue_work_logs', kwargs={'issue_id': issue_id})
    else:
        form = AdminWorkLogForm()
    
    context = {
        'issue': issue,
        'work_logs': work_logs,
        'form': form,
        'total_hours': work_logs.aggregate(total_hours=models.Sum('hours_spent'))['total_hours'] or 0,
    }
    return render(request, 'admin/issue_work_logs.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def add_work_log(request, issue_id):
    """Add work log via AJAX for better UX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    issue = get_object_or_404(Issue, id=issue_id)
    form = AdminWorkLogForm(request.POST)
    
    if form.is_valid():
        work_log = form.save(commit=False)
        work_log.issue = issue
        work_log.admin = request.user
        work_log.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Work log added successfully',
            'work_log': {
                'id': work_log.id,
                'work_type': work_log.get_work_type_display(),
                'hours_spent': str(work_log.hours_spent),
                'description': work_log.description,
                'outcome': work_log.outcome,
                'created_at': work_log.created_at.strftime('%Y-%m-%d %H:%M'),
                'admin_name': request.user.get_full_name(),
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)


@login_required
@user_passes_test(lambda u: u.is_staff)
def progress_updates(request, issue_id):
    """View and manage progress updates for a specific issue"""
    issue = get_object_or_404(Issue, id=issue_id)
    progress_updates = issue.progress_updates.all().select_related('admin').order_by('-created_at')
    
    if request.method == 'POST':
        form = ProgressUpdateForm(request.POST)
        if form.is_valid():
            progress_update = form.save(commit=False)
            progress_update.issue = issue
            progress_update.admin = request.user
            progress_update.save()
            
            # Update issue progress
            issue.progress_percentage = progress_update.progress_percentage
            issue.progress_updated_at = progress_update.created_at
            if progress_update.description:
                issue.progress_notes = progress_update.description[:500]
            issue.save(update_fields=['progress_percentage', 'progress_updated_at', 'progress_notes'])
            
            messages.success(request, f'Progress update added for issue: {issue.title}')
            return redirect('admin_progress_updates', kwargs={'issue_id': issue_id})
    else:
        form = ProgressUpdateForm()
    
    context = {
        'issue': issue,
        'progress_updates': progress_updates,
        'form': form,
    }
    return render(request, 'admin/progress_updates.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def add_progress_update(request, issue_id):
    """Add progress update via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    issue = get_object_or_404(Issue, id=issue_id)
    form = ProgressUpdateForm(request.POST)
    
    if form.is_valid():
        progress_update = form.save(commit=False)
        progress_update.issue = issue
        progress_update.admin = request.user
        progress_update.save()
        
        # Update issue progress
        issue.progress_percentage = progress_update.progress_percentage
        issue.progress_updated_at = progress_update.created_at
        if progress_update.description:
            issue.progress_notes = progress_update.description[:500]
        issue.save(update_fields=['progress_percentage', 'progress_updated_at', 'progress_notes'])
        
        return JsonResponse({
            'success': True,
            'message': 'Progress update added successfully',
            'progress_update': {
                'id': progress_update.id,
                'update_type': progress_update.get_update_type_display(),
                'progress_percentage': progress_update.progress_percentage,
                'title': progress_update.title,
                'description': progress_update.description,
                'created_at': progress_update.created_at.strftime('%Y-%m-%d %H:%M'),
                'admin_name': request.user.get_full_name(),
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)
