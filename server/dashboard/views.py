from datetime import timedelta, datetime
import json

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_required, superuser_required
from accounts.models import User
from issues.models import Issue, IssueProgressLog, SLARule, MaintenanceTask
from issues.analytics import AnalyticsService
from notifications.models import Notification
from notifications.services import NotificationService


@require_http_methods(["GET", "POST"])
def dashboard_login(request):
    """
    Separate login for /dashboard/* so it doesn't share auth with /admin/*.
    Only staff/admin/superusers are allowed to sign in here.
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if user.is_superuser or user.is_staff or getattr(user, "role", None) in {"admin", "staff"}:
            return redirect("dashboard:home")
        auth_logout(request)

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        authed_user = form.get_user()
        if not (
            authed_user.is_superuser
            or authed_user.is_staff
            or getattr(authed_user, "role", None) in {"admin", "staff"}
        ):
            messages.error(
                request,
                "This account does not have access to the dashboard. Use an admin/staff account.",
            )
        else:
            auth_login(request, authed_user)
            next_url = (request.GET.get("next") or "").strip()
            return redirect(next_url or "dashboard:home")

    return render(request, "dashboard/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def dashboard_logout(request):
    auth_logout(request)
    return redirect("dashboard:login")


def _get_active_context(request, active_page):
    """
    Base context for all dashboard pages, including notification badge counts.
    """
    assignment_unread = 0
    assignment_notifications = []
    if request.user.is_authenticated:
        assignment_unread = Notification.objects.filter(
            user=request.user,
            notification_type="assignment",
            is_read=False,
        ).count()
        assignment_notifications = list(
            Notification.objects.filter(
                user=request.user,
                notification_type="assignment",
            )
            .select_related("related_issue")
            .order_by("-created_at")[:10]
        )

    return {
        "active_page": active_page,
        "assignment_unread_count": assignment_unread,
        "assignment_notifications": assignment_notifications,
    }


@admin_required
def dashboard_home(request):
    """Admin dashboard overview at /dashboard/."""
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    is_staff_view = request.user.role == "staff" and not request.user.is_superuser

    # Staff dashboard home is scoped to assigned issues only
    if is_staff_view:
        base_qs = Issue.objects.filter(assigned_to=request.user)

        my_open_issues = base_qs.filter(status__in=["open", "in-progress"]).count()
        resolved_this_month = base_qs.filter(
            status="resolved",
            resolved_at__gte=start_of_month,
            resolved_at__lte=now,
        ).count()
        awaiting_verification = base_qs.filter(status="awaiting_verification").count()
        blocked_issues = base_qs.filter(is_blocked=True).count()

        status_filter = request.GET.get("status") or ""
        sort = request.GET.get("sort") or "priority"

        issues_qs = (
            base_qs.select_related("reporter")
            .order_by("-updated_at")
        )
        if status_filter:
            issues_qs = issues_qs.filter(status=status_filter)

        priority_rank = Case(
            When(priority="critical", then=Value(0)),
            When(priority="high", then=Value(1)),
            When(priority="medium", then=Value(2)),
            When(priority="low", then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )

        if sort == "assigned_at":
            issues_qs = issues_qs.order_by(F("assigned_at").desc(nulls_last=True), "-updated_at")
        elif sort == "status":
            issues_qs = issues_qs.order_by("status", "-updated_at")
        else:
            issues_qs = issues_qs.annotate(_priority_rank=priority_rank).order_by(
                "_priority_rank", F("assigned_at").desc(nulls_last=True), "-updated_at"
            )

        context = {
            **_get_active_context(request, "home"),
            "is_staff_home": True,
            "my_open_issues": my_open_issues,
            "resolved_this_month": resolved_this_month,
            "awaiting_verification": awaiting_verification,
            "blocked_issues": blocked_issues,
            "issues": issues_qs,
            "status_filter": status_filter,
            "sort": sort,
            "status_choices": Issue.STATUS_CHOICES,
        }
        return render(request, "dashboard/home.html", context)

    # Admin/superuser overview stays campus-wide
    base_qs = Issue.objects.all()

    # Update SLA overdue flags for any issues that have crossed their SLA deadline
    overdue_candidates = base_qs.filter(
        sla_due_at__isnull=False,
        is_overdue=False,
        status__in=["open", "in-progress", "awaiting_verification", "reopened"],
    )
    newly_overdue_ids = []
    for issue in overdue_candidates:
        if issue.sla_due_at and now > issue.sla_due_at:
            issue.is_overdue = True
            issue.save(update_fields=["is_overdue", "updated_at"])
            newly_overdue_ids.append(issue.id)

    if newly_overdue_ids:
        admins = User.objects.filter(Q(is_superuser=True) | Q(role="admin")).distinct()
        for admin_user in admins:
            for issue in Issue.objects.filter(id__in=newly_overdue_ids):
                NotificationService.create_notification(
                    user=admin_user,
                    title=f"Issue #{issue.id} is overdue",
                    message=f"Issue '{issue.title}' has exceeded its SLA deadline.",
                    notification_type="status_change",
                    related_issue=issue,
                )

    total_issues = base_qs.count()
    open_issues = base_qs.filter(status__in=["open", "in-progress"]).count()

    resolved_this_month_qs = base_qs.filter(
        status__in=["resolved", "closed"],
        resolved_at__gte=start_of_month,
        resolved_at__lte=now,
    )
    resolved_this_month = resolved_this_month_qs.count()

    resolution_time = ExpressionWrapper(
        F("resolved_at") - F("created_at"), output_field=DurationField()
    )
    avg_resolution = (
        resolved_this_month_qs.annotate(resolution_time=resolution_time).aggregate(
            avg=Avg("resolution_time")
        )["avg"]
        or timedelta(0)
    )
    avg_resolution_days = (
        round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else 0
    )

    recent_issues = base_qs.select_related("reporter").order_by("-created_at")[:10]

    issues_by_status = (
        base_qs.values("status").annotate(count=Count("id")).order_by("status")
    )

    month_issues = base_qs.filter(
        created_at__gte=start_of_month,
        created_at__lte=now,
    )

    top_locations = (
        month_issues.values("location")
        .annotate(count=Count("id"))
        .order_by("-count")[:3]
    )
    top_categories = (
        month_issues.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:3]
    )

    context = {
        **_get_active_context(request, "home"),
        "total_issues": total_issues,
        "open_issues": open_issues,
        "resolved_this_month": resolved_this_month,
        "avg_resolution_days": avg_resolution_days,
        "recent_issues": recent_issues,
        "issues_by_status": issues_by_status,
        "top_locations": top_locations,
        "top_categories": top_categories,
    }
    return render(request, "dashboard/home.html", context)


@admin_required
def issue_list(request):
    """Paginated issue management list with filters and search."""
    # Staff users should only see issues assigned to them
    if request.user.role == "staff" and not request.user.is_superuser:
        issues_qs = Issue.objects.select_related("reporter").filter(
            assigned_to=request.user
        )
    else:
        issues_qs = Issue.objects.select_related("reporter").all()

    status = request.GET.get("status")
    category = request.GET.get("category")
    priority = request.GET.get("priority")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    search = request.GET.get("q")
    recurring_only = request.GET.get("recurring") == "1"
    sort = request.GET.get("sort") or ""

    if status:
        issues_qs = issues_qs.filter(status=status)
    if category:
        issues_qs = issues_qs.filter(category=category)
    if priority:
        issues_qs = issues_qs.filter(priority=priority)
    if date_from:
        issues_qs = issues_qs.filter(created_at__date__gte=date_from)
    if date_to:
        issues_qs = issues_qs.filter(created_at__date__lte=date_to)
    if search:
        issues_qs = issues_qs.filter(
            Q(title__icontains=search)
            | Q(location__icontains=search)
            | Q(reporter__first_name__icontains=search)
            | Q(reporter__last_name__icontains=search)
            | Q(reporter__email__icontains=search)
        )
    if recurring_only:
        issues_qs = issues_qs.filter(is_recurring=True)

    # Sorting: default by newest, optional sort by most upvotes
    if sort == "most_upvotes":
        issues_qs = issues_qs.order_by("-upvote_count", "-created_at")
    else:
        issues_qs = issues_qs.order_by("-created_at")

    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected")
        selected_issues = Issue.objects.filter(id__in=selected_ids)
        # Staff users can only bulk-update issues assigned to them
        if request.user.role == "staff" and not request.user.is_superuser:
            selected_issues = selected_issues.filter(assigned_to=request.user)

        if action == "mark_in_progress":
            updated = selected_issues.update(status="in-progress")
            messages.success(request, f"Marked {updated} issues as In Progress.")
        elif action == "mark_resolved":
            updated = selected_issues.update(status="resolved")
            messages.success(request, f"Marked {updated} issues as Resolved.")
        elif action == "delete":
            count = selected_issues.count()
            selected_issues.delete()
            messages.success(request, f"Deleted {count} issues.")
        else:
            messages.error(request, "Please select a valid bulk action.")

        return redirect("dashboard:issues_list")

    paginator = Paginator(issues_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        **_get_active_context(request, "issues"),
        "page_obj": page_obj,
        "status_filter": status or "",
        "category_filter": category or "",
        "priority_filter": priority or "",
        "recurring_filter": "1" if recurring_only else "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "search_query": search or "",
        "sort": sort,
        "status_choices": Issue.STATUS_CHOICES,
        "category_choices": Issue.CATEGORY_CHOICES,
        "priority_choices": Issue.PRIORITY_CHOICES,
        "is_staff_view": request.user.role == "staff" and not request.user.is_superuser,
    }
    return render(request, "dashboard/issues_list.html", context)


@admin_required
def issue_detail(request, pk):
    """Detailed view for managing a single issue."""
    issue = get_object_or_404(
        Issue.objects.select_related("reporter", "assigned_to"), pk=pk
    )
    is_staff_view = request.user.role == "staff" and not request.user.is_superuser
    if is_staff_view and issue.assigned_to_id != request.user.id:
        messages.error(request, "You do not have permission to view this issue.")
        return redirect("dashboard:issues_list")

    if request.method == "POST":
        if is_staff_view:
            action = request.POST.get("action") or ""

            if action == "acknowledge":
                if issue.status != "open":
                    messages.error(request, "This issue cannot be acknowledged in its current state.")
                else:
                    issue.status = "in-progress"
                    issue.is_blocked = False
                    issue.blocker_note = None
                    issue._modified_by_user = request.user  # type: ignore[attr-defined]
                    issue.save(update_fields=["status", "is_blocked", "blocker_note", "updated_at"])

                    IssueProgressLog.objects.create(
                        issue=issue,
                        staff=request.user,
                        log_type="acknowledged",
                        description="Issue acknowledged. Work starting.",
                    )
                    messages.success(request, "Issue acknowledged.")

            elif action == "add_progress":
                if issue.status != "in-progress":
                    messages.error(request, "You can only post progress updates while the issue is In Progress.")
                else:
                    log_type = request.POST.get("log_type") or ""
                    allowed = {"on_site", "diagnosis", "in_progress"}
                    if log_type not in allowed:
                        messages.error(request, "Invalid log type selected.")
                    else:
                        description = (request.POST.get("description") or "").strip()
                        if not description:
                            messages.error(request, "Description is required.")
                        else:
                            photo = request.FILES.get("photo")
                            IssueProgressLog.objects.create(
                                issue=issue,
                                staff=request.user,
                                log_type=log_type,
                                description=description,
                                photo=photo,
                            )
                            messages.success(request, "Progress update posted.")

            elif action == "flag_blocked":
                if issue.status != "in-progress":
                    messages.error(request, "You can only flag blockers while the issue is In Progress.")
                else:
                    blocker_note = (request.POST.get("blocker_note") or "").strip()
                    if not blocker_note:
                        messages.error(request, "Please provide a blocker note.")
                    else:
                        issue.is_blocked = True
                        issue.blocker_note = blocker_note
                        issue._modified_by_user = request.user  # type: ignore[attr-defined]
                        issue.save(update_fields=["is_blocked", "blocker_note", "updated_at"])

                        IssueProgressLog.objects.create(
                            issue=issue,
                            staff=request.user,
                            log_type="blocked",
                            description=blocker_note,
                        )

                        admins = User.objects.filter(Q(is_superuser=True) | Q(role="admin")).distinct()
                        for admin_user in admins:
                            NotificationService.create_notification(
                                user=admin_user,
                                title=f"Issue #{issue.id} blocked",
                                message=f"{request.user.get_full_name() or request.user.email} flagged a blocker: {blocker_note}",
                                notification_type="assignment",
                                related_issue=issue,
                            )
                        messages.success(request, "Issue flagged as blocked and admins notified.")

            elif action == "remove_blocker":
                if issue.status != "in-progress" or not issue.is_blocked:
                    messages.error(request, "This issue is not currently blocked.")
                else:
                    issue.is_blocked = False
                    issue.blocker_note = None
                    issue._modified_by_user = request.user  # type: ignore[attr-defined]
                    issue.save(update_fields=["is_blocked", "blocker_note", "updated_at"])

                    IssueProgressLog.objects.create(
                        issue=issue,
                        staff=request.user,
                        log_type="in_progress",
                        description="Blocker resolved. Resuming work.",
                    )
                    messages.success(request, "Blocker removed.")

            elif action == "submit_resolution":
                if issue.status != "in-progress":
                    messages.error(request, "You can only submit resolution while the issue is In Progress.")
                else:
                    summary = (request.POST.get("resolution_summary") or "").strip()
                    follow_up = (request.POST.get("follow_up_recommendations") or "").strip()
                    if not summary:
                        messages.error(request, "Resolution summary is required.")
                    else:
                        issue.status = "awaiting_verification"
                        issue.resolved_at = timezone.now()
                        issue.resolution_summary = summary
                        if follow_up:
                            issue.resolution_details = follow_up
                        issue._modified_by_user = request.user  # type: ignore[attr-defined]
                        issue.save()

                        final_photo = request.FILES.get("final_photo")
                        IssueProgressLog.objects.create(
                            issue=issue,
                            staff=request.user,
                            log_type="completed",
                            description=summary,
                            photo=final_photo,
                        )

                        admins = User.objects.filter(Q(is_superuser=True) | Q(role="admin")).distinct()
                        for admin_user in admins:
                            NotificationService.create_notification(
                                user=admin_user,
                                title=f"Issue #{issue.id} awaiting verification",
                                message=f"Issue #{issue.id} was resolved by {request.user.get_full_name() or request.user.email} and is awaiting your verification.",
                                notification_type="assignment",
                                related_issue=issue,
                            )

                        messages.success(request, "Issue submitted for verification.")

            else:
                messages.error(request, "Invalid action.")

            return redirect("dashboard:issue_detail", pk=issue.pk)

        # Admin/superuser edit flow (existing behavior)
        updated = False

        new_status = request.POST.get("status")
        if new_status:
            if new_status in dict(Issue.STATUS_CHOICES):
                issue.status = new_status
                updated = True
                if new_status in {"resolved", "closed"} and not issue.resolved_at:
                    issue.resolved_at = timezone.now()
            else:
                messages.error(request, "Invalid status selected.")

        if request.user.is_superuser or getattr(request.user, "role", "") == "admin":
            assigned_to_id = request.POST.get("assigned_to")
            if assigned_to_id is not None:
                if assigned_to_id == "":
                    if issue.assigned_to is not None:
                        issue.assigned_to = None
                        issue.assigned_at = None
                        updated = True
                else:
                    try:
                        assignee = User.objects.get(
                            id=assigned_to_id,
                            role__in=["staff", "admin"],
                        )
                        if issue.assigned_to_id != assignee.id:
                            issue.assigned_to = assignee
                            issue.assigned_at = timezone.now()
                            updated = True
                    except User.DoesNotExist:
                        messages.error(request, "Selected staff member is not valid.")

        if updated:
            issue._modified_by_user = request.user  # type: ignore[attr-defined]
            issue.save()
            messages.success(request, "Issue updated successfully.")

        return redirect("dashboard:issue_detail", pk=issue.pk)

    # Staff users available for assignment (superuser/admin only)
    staff_users = []
    if request.user.is_superuser or getattr(request.user, "role", "") == "admin":
        staff_users = (
            User.objects.filter(role__in=["staff", "admin"])
            .order_by("first_name", "last_name", "email")
            .distinct()
        )

    progress_logs = IssueProgressLog.objects.filter(issue=issue).select_related("staff")

    context = {
        **_get_active_context(request, "issues"),
        "issue": issue,
        "status_choices": Issue.STATUS_CHOICES,
        "staff_users": staff_users,
        "progress_logs": progress_logs,
        "is_staff_view": is_staff_view,
    }
    if is_staff_view:
        return render(request, "dashboard/staff_issue_detail.html", context)
    return render(request, "dashboard/issue_detail.html", context)


@admin_required
def issue_quick_update(request, pk):
    """
    Lightweight endpoint for staff to update an issue status directly
    from the list view while keeping their current filters and page.
    """
    if request.method != "POST":
        return redirect("dashboard:issues_list")

    issue = get_object_or_404(Issue, pk=pk)
    # Staff can only update issues assigned to them
    if request.user.role == "staff" and not request.user.is_superuser:
        if issue.assigned_to_id != request.user.id:
            messages.error(request, "You do not have permission to update this issue.")
            return redirect("dashboard:issues_list")
    new_status = request.POST.get("status")

    if new_status and new_status in dict(Issue.STATUS_CHOICES):
        issue.status = new_status
        issue._modified_by_user = request.user  # type: ignore[attr-defined]
        if new_status in {"resolved", "closed"} and not issue.resolved_at:
            issue.resolved_at = timezone.now()
        issue.save()
        messages.success(request, "Issue updated successfully.")
    else:
        messages.error(request, "Invalid status selected.")

    return_url = request.POST.get("return_url")
    if return_url:
        return redirect(return_url)
    return redirect("dashboard:issues_list")


@superuser_required
def user_management(request):
    """User management page for viewing and updating roles."""
    search = request.GET.get("q", "")
    users_qs = User.objects.all().order_by("email")

    if search:
        users_qs = users_qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        role = request.POST.get("role")
        user = get_object_or_404(User, pk=user_id)

        valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect("dashboard:users")

        user.role = role
        # Keep is_staff aligned with elevated roles
        if role in {"staff", "admin"}:
            user.is_staff = True
        else:
            # Do not silently unset is_staff for superusers
            if not user.is_superuser:
                user.is_staff = False

        user.save(update_fields=["role", "is_staff"])
        messages.success(request, f"Updated role for {user.email} to {role}.")
        return redirect("dashboard:users")

    users = users_qs

    context = {
        **_get_active_context(request, "users"),
        "users": users,
        "search_query": search,
        "role_choices": User.ROLE_CHOICES,
    }
    return render(request, "dashboard/users.html", context)


@superuser_required
def staff_overview(request):
    """Read-only overview of staff and their open issue workload."""
    staff_users = User.objects.filter(
        Q(role__in=["staff", "admin"]) | Q(is_staff=True)
    ).distinct()

    staff_data = []
    for user in staff_users:
        open_assigned = Issue.objects.filter(
            assigned_to=user,
            status__in=["open", "in-progress"],
        ).count()
        staff_data.append(
            {
                "user": user,
                "open_assigned_count": open_assigned,
            }
        )

    context = {
        **_get_active_context(request, "staff"),
        "staff_data": staff_data,
    }
    return render(request, "dashboard/staff.html", context)


@admin_required
def analytics(request):
    """
    Admin analytics dashboard with charts and summary stats.
    """
    range_param = (request.GET.get("range") or "30").lower()
    today = timezone.localdate()

    if range_param in {"7", "30", "90"}:
        days = int(range_param)
        date_to = today
        date_from = today - timedelta(days=days - 1)
    elif range_param == "custom":
        try:
            date_from_str = (request.GET.get("date_from") or "").strip()
            date_to_str = (request.GET.get("date_to") or "").strip()
            if not date_from_str or not date_to_str:
                raise ValueError
            date_from = timezone.datetime.fromisoformat(date_from_str).date()
            date_to = timezone.datetime.fromisoformat(date_to_str).date()
            if date_from > date_to:
                raise ValueError
        except Exception:
            messages.error(
                request,
                "Invalid custom date range. Falling back to last 30 days.",
            )
            range_param = "30"
            date_to = today
            date_from = today - timedelta(days=29)
    else:
        range_param = "30"
        date_to = today
        date_from = today - timedelta(days=29)

    # Base issue queryset for the selected range
    issues_qs = Issue.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    # Status pie chart data
    status_counts = (
        issues_qs.values("status").annotate(count=Count("id")).order_by("status")
    )
    status_chart = {
        "labels": [row["status"].replace("_", " ").title() for row in status_counts],
        "data": [row["count"] for row in status_counts],
    }

    # Issues per day (line chart)
    daily_counts = (
        issues_qs.extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    daily_chart = {
        # SQLite may return the annotated "day" as a string already; normalise via str().
        "labels": [str(row["day"]) for row in daily_counts],
        "data": [row["count"] for row in daily_counts],
    }

    # Average resolution time by category (bar chart) using AnalyticsService
    analytics_service = AnalyticsService()
    resolution_stats = analytics_service.get_resolution_time_analytics()
    by_category = resolution_stats.get("by_category", [])
    category_labels = []
    category_hours = []
    for row in by_category:
        category_labels.append(row["category"])
        avg_duration = row.get("avg_resolution_time")
        if avg_duration is not None:
            hours = round(avg_duration.total_seconds() / 3600, 2)
        else:
            hours = 0
        category_hours.append(hours)
    resolution_chart = {
        "labels": category_labels,
        "data": category_hours,
    }

    # Top 5 most reported locations
    top_locations = (
        issues_qs.values("location")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    # SLA compliance rate (% of resolved within SLA)
    resolved_in_range = issues_qs.filter(
        status__in=["resolved", "closed"], resolved_at__isnull=False
    )
    sla_rules = {
        rule.category: rule.response_time_hours for rule in SLARule.objects.all()
    }
    total_resolved_with_sla = 0
    resolved_within_sla = 0
    for issue in resolved_in_range:
        hours = sla_rules.get(issue.category)
        if hours is None:
            continue
        total_resolved_with_sla += 1
        allowed_delta = timedelta(hours=hours)
        actual_delta = issue.resolved_at - issue.created_at
        if actual_delta <= allowed_delta:
            resolved_within_sla += 1

    sla_compliance_rate = 0
    if total_resolved_with_sla:
        sla_compliance_rate = round(
            (resolved_within_sla / total_resolved_with_sla) * 100, 1
        )

    context = {
        **_get_active_context(request, "analytics"),
        "range": range_param,
        "date_from": date_from,
        "date_to": date_to,
        "status_chart_data": json.dumps(status_chart),
        "daily_chart_data": json.dumps(daily_chart),
        "resolution_chart_data": json.dumps(resolution_chart),
        "top_locations": top_locations,
        "sla_compliance_rate": sla_compliance_rate,
        "total_resolved_with_sla": total_resolved_with_sla,
    }
    return render(request, "dashboard/analytics.html", context)


@admin_required
def calendar(request):
    """
    Admin maintenance scheduling calendar.
    Allows admins to create preventive maintenance tasks and see upcoming work.
    """
    now = timezone.now()

    # Send 24-hour reminders for upcoming tasks that haven't been reminded yet.
    reminder_window_start = now + timedelta(hours=24)
    reminder_window_end = now + timedelta(hours=25)
    reminder_candidates = MaintenanceTask.objects.filter(
        reminder_sent=False,
        scheduled_for__gte=reminder_window_start,
        scheduled_for__lte=reminder_window_end,
        assigned_to__isnull=False,
    ).select_related("assigned_to")

    for task in reminder_candidates:
        NotificationService.create_notification(
            user=task.assigned_to,
            title=f"Upcoming maintenance: {task.title}",
            message=(
                f"You have a scheduled maintenance task at {task.location} on "
                f"{timezone.localtime(task.scheduled_for).strftime('%Y-%m-%d %H:%M')}."
            ),
            notification_type="assignment",
        )
        task.reminder_sent = True
        task.save(update_fields=["reminder_sent", "updated_at"])

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        location = (request.POST.get("location") or "").strip()
        notes = (request.POST.get("notes") or "").strip()
        assigned_to_id = request.POST.get("assigned_to") or ""
        date_str = (request.POST.get("scheduled_date") or "").strip()
        time_str = (request.POST.get("scheduled_time") or "").strip()

        if not title or not location or not date_str or not time_str:
            messages.error(
                request,
                "Title, location, date, and time are required for a maintenance task.",
            )
            return redirect("dashboard:calendar")

        try:
            dt = datetime.fromisoformat(f"{date_str}T{time_str}")
            scheduled_for = timezone.make_aware(dt, timezone.get_current_timezone())
        except Exception:
            messages.error(request, "Invalid date or time for scheduled task.")
            return redirect("dashboard:calendar")

        assignee = None
        if assigned_to_id:
            try:
                assignee = User.objects.get(
                    id=assigned_to_id, role__in=["staff", "admin"]
                )
            except User.DoesNotExist:
                messages.error(request, "Selected staff member is not valid.")
                return redirect("dashboard:calendar")

        MaintenanceTask.objects.create(
            title=title,
            location=location,
            notes=notes,
            assigned_to=assignee,
            scheduled_for=scheduled_for,
        )
        messages.success(request, "Maintenance task scheduled successfully.")
        return redirect("dashboard:calendar")

    upcoming_tasks = (
        MaintenanceTask.objects.select_related("assigned_to")
        .filter(scheduled_for__gte=now - timedelta(days=1))
        .order_by("scheduled_for")
    )

    staff_users = (
        User.objects.filter(role__in=["staff", "admin"])
        .order_by("first_name", "last_name", "email")
        .distinct()
    )

    context = {
        **_get_active_context(request, "calendar"),
        "upcoming_tasks": upcoming_tasks,
        "staff_users": staff_users,
    }
    return render(request, "dashboard/calendar.html", context)


@admin_required
def announcements(request):
    context = {
        **_get_active_context(request, "announcements"),
    }
    return render(request, "dashboard/announcements.html", context)


@admin_required
def settings_view(request):
    """
    Admin settings page, currently focused on SLA configuration.
    """
    # Build a mapping of existing SLA rules by category
    existing_rules = {
        rule.category: rule for rule in SLARule.objects.all()
    }

    if request.method == "POST":
        # Update or create SLA rules per category based on submitted form data
        for category_value, _label in Issue.CATEGORY_CHOICES:
            field_name = f"sla_hours_{category_value}"
            raw_value = (request.POST.get(field_name) or "").strip()
            if not raw_value:
                # Skip empty values to avoid accidentally wiping SLAs
                continue
            try:
                hours = int(raw_value)
                if hours <= 0:
                    raise ValueError
            except ValueError:
                messages.error(
                    request,
                    f"Invalid SLA hours for category '{category_value}'. Please enter a positive whole number.",
                )
                return redirect("dashboard:settings")

            rule = existing_rules.get(category_value)
            if rule:
                if rule.response_time_hours != hours:
                    rule.response_time_hours = hours
                    rule.save(update_fields=["response_time_hours", "updated_at"])
            else:
                SLARule.objects.create(
                    category=category_value,
                    response_time_hours=hours,
                )

        messages.success(request, "SLA settings updated successfully.")
        return redirect("dashboard:settings")

    # Prepare context for rendering the SLA settings form
    sla_rows = []
    for value, label in Issue.CATEGORY_CHOICES:
        rule = existing_rules.get(value)
        sla_rows.append(
            {
                "value": value,
                "label": label,
                "hours": rule.response_time_hours if rule else "",
            }
        )

    context = {
        **_get_active_context(request, "settings"),
        "sla_rows": sla_rows,
    }
    return render(request, "dashboard/settings.html", context)


@admin_required
def assignment_notifications_mark_all_read(request):
    """
    Mark all assignment notifications for the current user as read,
    then redirect back to the dashboard (or the referring page).
    """
    if request.method == "POST":
        count = Notification.objects.filter(
            user=request.user,
            notification_type="assignment",
            is_read=False,
        ).update(is_read=True)
        if count:
            messages.success(
                request, f"Marked {count} assignment notification(s) as read."
            )
    # Prefer redirecting to referrer if available
    redirect_to = request.META.get("HTTP_REFERER") or "dashboard:home"
    try:
        return redirect(redirect_to)
    except Exception:
        return redirect("dashboard:home")

