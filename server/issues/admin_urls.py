from django.urls import path
from . import admin_views

app_name = 'issues'

urlpatterns = [
    path('dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('work-logs/<int:issue_id>/', admin_views.issue_work_logs, name='admin_issue_work_logs'),
    path('add-work-log/<int:issue_id>/', admin_views.add_work_log, name='admin_add_work_log'),
    path('progress-updates/<int:issue_id>/', admin_views.progress_updates, name='admin_progress_updates'),
    path('add-progress-update/<int:issue_id>/', admin_views.add_progress_update, name='admin_add_progress_update'),
]
