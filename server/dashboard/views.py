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
from issues.models import Issue, IssueProgressLog, SLARule, MaintenanceTask, IssueFeedback
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
                    
                    from issues.services import calculate_sla_deadline
                    issue.sla_deadline = calculate_sla_deadline(issue)
                    
                    issue.save(update_fields=["status", "is_blocked", "blocker_note", "updated_at", "sla_deadline"])

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

    # Feedback Analytics
    feedback_qs = IssueFeedback.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    feedback_total = feedback_qs.count()
    feedback_overall_avg_dict = feedback_qs.aggregate(avg=Avg("rating"))
    feedback_overall_avg = feedback_overall_avg_dict["avg"]

    feedback_staff_ratings = (
        feedback_qs.filter(issue__assigned_to__isnull=False)
        .values(
            "issue__assigned_to__first_name",
            "issue__assigned_to__last_name",
            "issue__assigned_to__email",
        )
        .annotate(
            avg_rating=Avg("rating"),
            rating_count=Count("id")
        )
        .order_by("-rating_count", "-avg_rating")
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
        "feedback_total": feedback_total,
        "feedback_overall_avg": feedback_overall_avg,
        "feedback_staff_ratings": feedback_staff_ratings,
    }
    return render(request, "dashboard/analytics.html", context)


@admin_required
@require_http_methods(["POST"])
def generate_ai_report(request):
    """Dashboard-native endpoint for AI monthly report generation.

    Lives under /dashboard/ so the dashboard session cookie is sent
    automatically, avoiding cross-path cookie issues with /api/.
    """
    from django.http import JsonResponse
    from issues.ai_services import ai_service
    from issues.models import IssueFeedback

    if not ai_service.is_available():
        return JsonResponse(
            {"error": "AI service is currently unavailable"}, status=503
        )

    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_issues = Issue.objects.filter(created_at__gte=thirty_days_ago)

    stats = {
        "total_issues": recent_issues.count(),
        "issues_by_category": list(
            recent_issues.values("category").annotate(count=Count("id"))
        ),
        "issues_by_status": list(
            recent_issues.values("status").annotate(count=Count("id"))
        ),
        "resolution_times": [],
        "top_locations": list(
            recent_issues.values("location")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        ),
        "average_rating": IssueFeedback.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(avg=Avg("rating"))["avg"]
        or 0,
    }

    resolved_issues = recent_issues.filter(
        status__in=["resolved", "closed"], resolved_at__isnull=False
    )
    if resolved_issues.exists():
        total_hours = sum(
            (issue.resolved_at - issue.created_at).total_seconds() / 3600
            for issue in resolved_issues
        )
        stats["average_resolution_time_hours"] = total_hours / resolved_issues.count()
    else:
        stats["average_resolution_time_hours"] = 0

    high_priority = recent_issues.filter(priority="high")
    other_priority = recent_issues.exclude(priority="high")
    sla_compliant = 0
    total_sla_tracked = 0
    for issue in list(high_priority) + list(other_priority):
        if issue.sla_due_at:
            total_sla_tracked += 1
            if issue.resolved_at and issue.resolved_at <= issue.sla_due_at:
                sla_compliant += 1

    stats["sla_compliance_rate"] = (
        (sla_compliant / total_sla_tracked * 100) if total_sla_tracked > 0 else 0
    )

    report = ai_service.generate_monthly_report(stats)
    return JsonResponse({"report": report, "stats": stats})


@admin_required
def calendar_events_api(request):
    """
    Returns JSON data for FullCalendar.
    Staff users only see their own assigned issues and maintenance windows.
    Admins see everything based on the `view_mode` query param.
    """
    from django.http import JsonResponse
    
    now = timezone.now()
    is_admin = request.user.is_superuser or request.user.role == "admin"
    view_mode = request.GET.get('view_mode', 'combined') # 'maintenance', 'sla', 'combined'
    
    events = []
    
    # 1. Maintenance Windows
    if view_mode in ['combined', 'maintenance'] or not is_admin:
        windows = MaintenanceWindow.objects.all()
        for w in windows:
            color = "#ef4444" # RED
            if w.is_cancelled:
                color = "#9ca3af" # GREY
            elif w.actual_end:
                color = "#10b981" # GREEN
                
            events.append({
                "id": f"mw_{w.id}",
                "title": f"Maintenance: {w.title}",
                "start": w.scheduled_start.isoformat(),
                "end": (w.actual_end if w.actual_end else w.scheduled_end).isoformat(),
                "color": color,
                "extendedProps": {
                    "type": "maintenance",
                    "description": w.description,
                    "is_cancelled": w.is_cancelled,
                    "is_active": w.is_active,
                    "actual_end": w.actual_end.isoformat() if w.actual_end else None,
                    "scheduled_start": w.scheduled_start.isoformat(),
                    "scheduled_end": w.scheduled_end.isoformat(),
                }
            })

    # 2. SLA Issues
    if view_mode in ['combined', 'sla'] or not is_admin:
        issues_qs = Issue.objects.filter(sla_deadline__isnull=False, assigned_to__isnull=False)
        if not is_admin:
            issues_qs = issues_qs.filter(assigned_to=request.user)
            
        for issue in issues_qs:
            color = "#3b82f6" # BLUE
            if issue.status in ["resolved", "closed"]:
                color = "#9ca3af" # GREY
            elif issue.sla_breached or (now > issue.sla_deadline and issue.status not in ["resolved", "closed"]):
                color = "#f97316" # ORANGE
                
            # For start, use acknowledged log or assigned_at or created_at
            ack_log = issue.progress_logs.filter(log_type="acknowledged").order_by("created_at").first()
            start_time = ack_log.created_at if ack_log else (issue.assigned_at if issue.assigned_at else issue.created_at)

            events.append({
                "id": f"is_{issue.id}",
                "title": f"Issue #{issue.id}: {issue.title}",
                "start": start_time.isoformat(),
                "end": issue.sla_deadline.isoformat(),
                "color": color,
                "extendedProps": {
                    "type": "issue",
                    "issue_id": issue.id,
                    "location": issue.location,
                    "category": issue.get_category_display(),
                    "status": issue.get_status_display(),
                    "assigned_to": issue.assigned_to.get_full_name() or issue.assigned_to.email,
                }
            })

    return JsonResponse(events, safe=False)


@admin_required
def calendar(request):
    """
    Admin and Staff calendar view mapping Maintenance Windows and SLA deadlines.
    """
    is_admin = request.user.is_superuser or request.user.role == "admin"
    
    if request.method == "POST" and is_admin:
        action = request.POST.get("action")
        
        if action == "schedule_maintenance":
            title = (request.POST.get("title") or "").strip()
            description = (request.POST.get("description") or "").strip()
            start_str = (request.POST.get("scheduled_start") or "").strip()
            end_str = (request.POST.get("scheduled_end") or "").strip()
            
            try:
                start_dt = timezone.make_aware(datetime.fromisoformat(start_str))
                end_dt = timezone.make_aware(datetime.fromisoformat(end_str))
                
                # Simple conflict check (warning should be handled in frontend by querying API, but this stops creating if overlapping? No, we just create it as requested.)
                
                window = MaintenanceWindow.objects.create(
                    title=title,
                    description=description,
                    scheduled_start=start_dt,
                    scheduled_end=end_dt,
                    created_by=request.user
                )
                
                # Notify all users immediately
                start_fmt = timezone.localtime(start_dt).strftime('%Y-%m-%d %H:%M')
                end_fmt = timezone.localtime(end_dt).strftime('%Y-%m-%d %H:%M')
                
                msg = f"📢 Scheduled Maintenance: {title} — The system will be unavailable on {timezone.localtime(start_dt).strftime('%Y-%m-%d')} from {timezone.localtime(start_dt).strftime('%H:%M')} to {timezone.localtime(end_dt).strftime('%H:%M')}. {description}"
                
                for user in User.objects.all():
                    NotificationService.create_notification(
                        user=user,
                        title="Scheduled Maintenance",
                        message=msg,
                        notification_type="system"
                    )
                
                messages.success(request, "Maintenance window scheduled successfully.")
            except Exception as e:
                messages.error(request, f"Error scheduling maintenance: {e}")
                
        elif action == "cancel_maintenance":
            mw_id = request.POST.get("maintenance_id")
            if mw_id:
                window = get_object_or_404(MaintenanceWindow, id=mw_id)
                if not window.is_active and not window.actual_end:
                    window.is_cancelled = True
                    window.save(update_fields=["is_cancelled"])
                    msg = f"📢 Maintenance '{window.title}' scheduled for {timezone.localtime(window.scheduled_start).strftime('%Y-%m-%d')} has been cancelled. No downtime expected."
                    for user in User.objects.all():
                        NotificationService.create_notification(
                            user=user,
                            title="Maintenance Cancelled",
                            message=msg,
                            notification_type="system"
                        )
                    messages.success(request, "Maintenance window cancelled.")
                
        elif action == "end_maintenance":
            mw_id = request.POST.get("maintenance_id")
            if mw_id:
                window = get_object_or_404(MaintenanceWindow, id=mw_id)
                if window.is_active and not window.actual_end:
                    window.actual_end = timezone.now()
                    window.is_active = False
                    window.save(update_fields=["actual_end", "is_active"])
                    msg = "✅ Maintenance has ended early. The system is back online."
                    for user in User.objects.all():
                        NotificationService.create_notification(
                            user=user,
                            title="Maintenance Complete",
                            message=msg,
                            notification_type="system"
                        )
                    messages.success(request, "Maintenance ended early.")
                
        return redirect("dashboard:calendar")
        
    # Get staff workload indicator
    staff_workload = []
    if is_admin:
        staff_users = User.objects.filter(role__in=["staff", "admin"]).distinct()
        for su in staff_users:
            active_count = Issue.objects.filter(
                assigned_to=su, status__in=["open", "in-progress"]
            ).count()
            status = "Available"
            if active_count >= 3:
                status = "Overloaded"
            elif active_count > 0:
                status = "Busy"
                
            staff_workload.append({
                "name": su.get_full_name() or su.email,
                "count": active_count,
                "status": status
            })

    context = {
        **_get_active_context(request, "calendar"),
        "is_admin": is_admin,
        "staff_workload": staff_workload,
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

    # Default fallback if not defined based on categories
    defaults = {
        'safety': 24,
        'electrical': 48,
        'plumbing': 48,
        'it-infrastructure': 48,
        'facilities': 120,
        'equipment': 120,
        'maintenance': 120,
        'other': 120,
    }
    
    sla_rows = []
    for value, label in Issue.CATEGORY_CHOICES:
        rule = existing_rules.get(value)
        sla_rows.append(
            {
                "value": value,
                "label": label,
                "hours": rule.response_time_hours if rule else defaults.get(value, 120),
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

