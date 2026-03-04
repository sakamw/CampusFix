from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import admin_required, superuser_required
from accounts.models import User
from dashboard.forms import StaffBlockerForm, StaffProgressUpdateForm, StaffResolutionForm
from issues.models import Issue, IssueProgressLog
from notifications.models import Notification
from notifications.services import NotificationService


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

    # For staff users (non-superuser), only show issues assigned to them
    is_staff_view = request.user.role == "staff" and not request.user.is_superuser
    if is_staff_view:
        base_qs = Issue.objects.filter(assigned_to=request.user)
    else:
        base_qs = Issue.objects.all()

    total_issues = base_qs.count()
    open_issues = base_qs.filter(status__in=["open", "in-progress"]).count()

    # For staff, treat issues submitted for verification this month as "resolved this month"
    if is_staff_view:
        resolved_this_month_qs = base_qs.filter(
            status__in=["awaiting_verification", "resolved", "closed"],
            resolved_at__gte=start_of_month,
            resolved_at__lte=now,
        )
    else:
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
    avg_resolution_days = round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else 0

    # For staff users, we use "My Assigned Issues" with priority-first ordering
    recent_issues = (
        base_qs.select_related("reporter", "assigned_to")
        .order_by("priority", "-created_at")[:25]
    )

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
        "is_staff_view": is_staff_view,
        "status_choices": Issue.STATUS_CHOICES,
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

    # Staff can only view issues currently assigned to them
    is_staff_view = request.user.role == "staff" and not request.user.is_superuser
    if is_staff_view:
        if issue.assigned_to_id != request.user.id:
            messages.error(request, "You do not have permission to view this issue.")
            return redirect("dashboard:issues_list")

    # Staff workflow actions
    if request.method == "POST" and is_staff_view:
        action = request.POST.get("staff_action")
        if issue.assigned_to_id != request.user.id:
            messages.error(request, "You can only modify issues assigned to you.")
            return redirect("dashboard:issues_list")

        # Acknowledge issue -> move to in-progress and log
        if action == "acknowledge" and issue.status == "open":
            issue.status = "in-progress"
            issue._modified_by_user = request.user  # type: ignore[attr-defined]
            issue.save()
            IssueProgressLog.objects.create(
                issue=issue,
                staff=request.user,
                log_type=IssueProgressLog.LOG_TYPE_ACKNOWLEDGED,
                description="Issue acknowledged. Work starting.",
            )
            messages.success(request, "Issue acknowledged and work marked as in progress.")
            return redirect("dashboard:issue_detail", pk=issue.pk)

        # Add progress update
        if action == "add_progress" and issue.status in {"in-progress"}:
            progress_form = StaffProgressUpdateForm(request.POST, request.FILES)
            if progress_form.is_valid():
                log = progress_form.save(commit=False)
                log.issue = issue
                log.staff = request.user
                log.save()
                messages.success(request, "Progress update posted.")
                return redirect("dashboard:issue_detail", pk=issue.pk)
        # Flag as blocked
        if action == "flag_blocked" and issue.status in {"in-progress"}:
            blocker_form = StaffBlockerForm(request.POST)
            if blocker_form.is_valid():
                blocker_note = blocker_form.cleaned_data["blocker_note"]
                issue.is_blocked = True
                issue.blocker_note = blocker_note
                issue._modified_by_user = request.user  # type: ignore[attr-defined]
                issue.save()
                IssueProgressLog.objects.create(
                    issue=issue,
                    staff=request.user,
                    log_type=IssueProgressLog.LOG_TYPE_BLOCKED,
                    description=blocker_note,
                )
                # Notify admins about the blocker
                admin_users = User.objects.filter(role="admin") | User.objects.filter(
                    is_superuser=True
                )
                for admin_user in admin_users.distinct():
                    NotificationService.create_notification(
                        user=admin_user,
                        title=f"Blocked issue needs attention: {issue.title}",
                        message=blocker_note,
                        notification_type="status_change",
                        related_issue=issue,
                    )
                messages.success(request, "Issue flagged as blocked and admins notified.")
                return redirect("dashboard:issue_detail", pk=issue.pk)

        # Remove blocker
        if action == "remove_blocker" and issue.status in {"in-progress"} and issue.is_blocked:
            issue.is_blocked = False
            issue.blocker_note = ""
            issue._modified_by_user = request.user  # type: ignore[attr-defined]
            issue.save()
            IssueProgressLog.objects.create(
                issue=issue,
                staff=request.user,
                log_type=IssueProgressLog.LOG_TYPE_IN_PROGRESS,
                description="Blocker resolved. Resuming work.",
            )
            messages.success(request, "Blocker cleared. Issue is back in progress.")
            return redirect("dashboard:issue_detail", pk=issue.pk)

        # Mark as resolved -> Awaiting verification
        if action == "mark_resolved" and issue.status in {"in-progress"}:
            resolution_form = StaffResolutionForm(request.POST, request.FILES)
            if resolution_form.is_valid():
                resolution_summary = resolution_form.cleaned_data["resolution_summary"]
                follow_up = resolution_form.cleaned_data["follow_up_recommendations"]
                final_photo = resolution_form.cleaned_data.get("final_photo")

                issue.status = "awaiting_verification"
                issue.resolved_at = issue.resolved_at or timezone.now()
                issue.resolution_summary = resolution_summary
                issue._modified_by_user = request.user  # type: ignore[attr-defined]
                issue.save()

                log = IssueProgressLog.objects.create(
                    issue=issue,
                    staff=request.user,
                    log_type=IssueProgressLog.LOG_TYPE_COMPLETED,
                    description=resolution_summary
                    + (f"\n\nFollow-up recommendations: {follow_up}" if follow_up else ""),
                    photo=final_photo,
                )

                # Notify admins that this issue is awaiting verification
                admin_users = User.objects.filter(role="admin") | User.objects.filter(
                    is_superuser=True
                )
                for admin_user in admin_users.distinct():
                    NotificationService.create_notification(
                        user=admin_user,
                        title=f"Issue #{issue.id} awaiting verification",
                        message=f"Issue '{issue.title}' has been resolved by {request.user.get_full_name() or request.user.email} and is awaiting your verification.",
                        notification_type="resolution",
                        related_issue=issue,
                    )
                messages.success(request, "Issue submitted for verification.")
                return redirect("dashboard:issue_detail", pk=issue.pk)

        # If we reach here, either the action was invalid or the form had errors
        messages.error(request, "Unable to process your request. Please check the form and try again.")
        return redirect("dashboard:issue_detail", pk=issue.pk)

    # Admin / superuser path for status and assignment management
    if request.method == "POST" and not is_staff_view:
        updated = False

        # Status update
        new_status = request.POST.get("status")
        if new_status:
            if new_status in dict(Issue.STATUS_CHOICES):
                issue.status = new_status
                updated = True
                # Keep resolved_at in sync when status becomes resolved
                if new_status in {"resolved", "closed"} and not issue.resolved_at:
                    issue.resolved_at = timezone.now()
            else:
                messages.error(request, "Invalid status selected.")

        # Assignment update (superusers and admin-role users only)
        if request.user.is_superuser or getattr(request.user, "role", "") == "admin":
            assigned_to_id = request.POST.get("assigned_to")
            if assigned_to_id is not None:
                if assigned_to_id == "":
                    if issue.assigned_to is not None:
                        issue.assigned_to = None
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
                        messages.error(
                            request,
                            "Selected staff member is not valid.",
                        )

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

    # Forms for staff workflow
    progress_form = StaffProgressUpdateForm()
    blocker_form = StaffBlockerForm()
    resolution_form = StaffResolutionForm()

    context = {
        **_get_active_context(request, "issues"),
        "issue": issue,
        "status_choices": Issue.STATUS_CHOICES,
        "staff_users": staff_users,
        "is_staff_view": is_staff_view,
        "progress_form": progress_form,
        "blocker_form": blocker_form,
        "resolution_form": resolution_form,
        "progress_logs": issue.progress_logs.select_related("staff"),
    }
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
    context = {
        **_get_active_context(request, "analytics"),
    }
    return render(request, "dashboard/analytics.html", context)


@admin_required
def calendar(request):
    context = {
        **_get_active_context(request, "calendar"),
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
    context = {
        **_get_active_context(request, "settings"),
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

