from django.urls import path

from . import views

app_name = "dashboard"


urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("issues/", views.issue_list, name="issues_list"),
    path("issues/<int:pk>/", views.issue_detail, name="issue_detail"),
    path("users/", views.user_management, name="users"),
    path("staff/", views.staff_overview, name="staff"),
    path("analytics/", views.analytics, name="analytics"),
    path("calendar/", views.calendar, name="calendar"),
    path("announcements/", views.announcements, name="announcements"),
    path("settings/", views.settings_view, name="settings"),
]

