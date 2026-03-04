from django.urls import path

from . import views

app_name = "dashboard"


urlpatterns = [
    path("login/", views.dashboard_login, name="login"),
    path("logout/", views.dashboard_logout, name="logout"),
    path("", views.dashboard_home, name="home"),
    path("issues/", views.issue_list, name="issues_list"),
    path("issues/<int:pk>/", views.issue_detail, name="issue_detail"),
    path(
        "issues/<int:pk>/quick-update/",
        views.issue_quick_update,
        name="issue_quick_update",
    ),
    path("users/", views.user_management, name="users"),
    path("staff/", views.staff_overview, name="staff"),
    path("analytics/", views.analytics, name="analytics"),
    path("calendar/", views.calendar, name="calendar"),
    path("announcements/", views.announcements, name="announcements"),
    path("settings/", views.settings_view, name="settings"),
    path(
        "notifications/assignments/mark-all-read/",
        views.assignment_notifications_mark_all_read,
        name="assignment_notifications_mark_all_read",
    ),
]

