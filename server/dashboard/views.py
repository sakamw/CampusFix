from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import admin_required, superuser_required
from accounts.models import User
from issues.models import Issue


def _get_active_context(active_page):
    return {"active_page": active_page}


@admin_required
def dashboard_home(request):
    """Admin dashboard overview at /dashboard/."""
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_issues = Issue.objects.count()
    open_issues = Issue.objects.filter(status__in=["open", "in-progress"]).count()

    resolved_this_month_qs = Issue.objects.filter(
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
    avg_resolution_days = round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else 0

    recent_issues = (
        Issue.objects.select_related("reporter")
        .all()
        .order_by("-created_at")[:10]
    )

    issues_by_status = (
        Issue.objects.values("status").annotate(count=Count("id")).order_by("status")
    )

    month_issues = Issue.objects.filter(
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
        **_get_active_context("home"),
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
    issues_qs = Issue.objects.select_related("reporter").all()

    status = request.GET.get("status")
    category = request.GET.get("category")
    priority = request.GET.get("priority")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    search = request.GET.get("q")
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

    # Sorting: default by newest, optional sort by most upvotes
    if sort == "most_upvotes":
        issues_qs = issues_qs.order_by("-upvote_count", "-created_at")
    else:
        issues_qs = issues_qs.order_by("-created_at")

    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected")
        selected_issues = Issue.objects.filter(id__in=selected_ids)

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
        **_get_active_context("issues"),
        "page_obj": page_obj,
        "status_filter": status or "",
        "category_filter": category or "",
        "priority_filter": priority or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "search_query": search or "",
        "sort": sort,
        "status_choices": Issue.STATUS_CHOICES,
        "category_choices": Issue.CATEGORY_CHOICES,
        "priority_choices": Issue.PRIORITY_CHOICES,
    }
    return render(request, "dashboard/issues_list.html", context)


@admin_required
def issue_detail(request, pk):
    """Detailed view for managing a single issue."""
    issue = get_object_or_404(Issue.objects.select_related("reporter"), pk=pk)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status and new_status in dict(Issue.STATUS_CHOICES):
            issue.status = new_status
            # Keep resolved_at in sync when status becomes resolved
            if new_status in {"resolved", "closed"} and not issue.resolved_at:
                issue.resolved_at = timezone.now()
            issue.save()
            messages.success(request, "Issue updated successfully.")
        else:
            messages.error(request, "Invalid status selected.")

        return redirect("dashboard:issue_detail", pk=issue.pk)

    context = {
        **_get_active_context("issues"),
        "issue": issue,
        "status_choices": Issue.STATUS_CHOICES,
    }
    return render(request, "dashboard/issue_detail.html", context)


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
        **_get_active_context("users"),
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
            status__in=["open", "in-progress"],
        ).count()
        staff_data.append(
            {
                "user": user,
                "open_assigned_count": open_assigned,
            }
        )

    context = {
        **_get_active_context("staff"),
        "staff_data": staff_data,
    }
    return render(request, "dashboard/staff.html", context)


@admin_required
def analytics(request):
    context = {
        **_get_active_context("analytics"),
    }
    return render(request, "dashboard/analytics.html", context)


@admin_required
def calendar(request):
    context = {
        **_get_active_context("calendar"),
    }
    return render(request, "dashboard/calendar.html", context)


@admin_required
def announcements(request):
    context = {
        **_get_active_context("announcements"),
    }
    return render(request, "dashboard/announcements.html", context)


@admin_required
def settings_view(request):
    context = {
        **_get_active_context("settings"),
    }
    return render(request, "dashboard/settings.html", context)

