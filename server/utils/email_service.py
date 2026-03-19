import logging
import time
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from notifications.models import Notification

logger = logging.getLogger(__name__)

def send_email(to_email, subject, html_content, text_content=None):
    """
    Base email sender with retry logic.
    Retries up to 3 times on failure with 2 second delay between attempts.
    Logs all send attempts and failures to Django's logger.
    Never raises an exception to the caller — failures are logged silently
    so a broken email never crashes a user-facing request.
    """
    if not text_content:
        text_content = strip_tags(html_content)

    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting to send email to {to_email}: {subject} (Attempt {attempt})")
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"Successfully sent email to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Attempt {attempt} failed to send email to {to_email}: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                # All retries failed
                log_failed_email(to_email, subject, str(e))
                return False

def log_failed_email(to_email, subject, error_message):
    """
    Log failed emails to the database for admin review.
    """
    from notifications.models import FailedEmail
    try:
        FailedEmail.objects.create(
            to_email=to_email,
            subject=subject,
            error_message=error_message,
            retry_count=3
        )
    except Exception as e:
        logger.critical(f"Failed to log email failure to database: {e}")

# Specific email functions

def send_verification_email(user, token):
    """Send account verification email."""
    verification_url = f"{settings.SITE_URL}/auth/verify-email/{token}/"
    context = {
        'first_name': user.first_name,
        'verification_url': verification_url,
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/verify_account.html', context)
    return send_email(user.email, "Verify your CampusFix account", html_content)

def send_account_verified_email(user):
    """Send account verified confirmation email."""
    context = {
        'first_name': user.first_name,
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/account_verified.html', context)
    return send_email(user.email, "Your CampusFix account is verified ✓", html_content)

def send_password_reset_email(user, reset_url):
    """Send password reset email."""
    context = {
        'first_name': user.first_name,
        'reset_url': reset_url,
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/password_reset.html', context)
    return send_email(user.email, "Reset your CampusFix password", html_content)

def send_password_changed_email(user):
    """Send password changed confirmation email."""
    from django.utils import timezone
    now = timezone.now()
    context = {
        'first_name': user.first_name,
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M'),
        'forgot_password_url': f"{settings.SITE_URL}/auth/forgot-password/",
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/password_changed.html', context)
    return send_email(user.email, "Your CampusFix password has been changed", html_content)

def send_issue_status_update_email(user, issue, old_status, new_status, feedback_token=None):
    """Send issue status update email to the reporter."""
    # Check preferences
    if not user.email_issue_updates:
        return False

    status_colors = {
        'open': '#70757a',
        'in-progress': '#1967d2',
        'awaiting_verification': '#f9ab00',
        'resolved': '#188038',
        'reopened': '#d93025',
        'closed': '#3c4043',
    }
    
    context = {
        'first_name': user.first_name,
        'issue_title': issue.title,
        'location': issue.location,
        'status_display': issue.get_status_display(),
        'status_color': status_colors.get(new_status, '#1a73e8'),
        'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        'issue_id': issue.id,
        'resolution_summary': issue.resolution_summary if new_status == 'resolved' else None,
        'is_resolved': new_status == 'resolved',
        'feedback_token': feedback_token,
        'SITE_URL': settings.SITE_URL,
        'show_preferences': True
    }
    html_content = render_to_string('emails/issue_status_update.html', context)
    return send_email(user.email, f"Update on your issue: {issue.title}", html_content)

def send_issue_assigned_email(user, issue):
    """Send email to staff when an issue is assigned."""
    priority_colors = {
        'low': '#188038',
        'medium': '#f9ab00',
        'high': '#e67c73',
        'critical': '#d93025',
    }
    
    context = {
        'first_name': user.first_name,
        'issue_title': issue.title,
        'issue_id': issue.id,
        'location': issue.location,
        'category': issue.get_category_display(),
        'priority_display': issue.get_priority_display(),
        'priority_color': priority_colors.get(issue.priority, '#1a73e8'),
        'deadline': issue.sla_deadline.strftime('%Y-%m-%d %H:%M') if issue.sla_deadline else 'N/A',
        'reporter_name': issue.reporter.get_full_name() or issue.reporter.email,
        'reported_at': issue.created_at.strftime('%Y-%m-%d'),
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/issue_assigned_staff.html', context)
    return send_email(user.email, f"New issue assigned to you: {issue.title}", html_content)

def send_sla_breach_email(admin_user, issue):
    """Send SLA breach alert to admin."""
    from django.utils import timezone
    delta = timezone.now() - issue.sla_deadline
    hours = int(delta.total_seconds() // 3600)
    
    context = {
        'issue_id': issue.id,
        'issue_title': issue.title,
        'location': issue.location,
        'staff_name': issue.assigned_to.get_full_name() if issue.assigned_to else "Unassigned",
        'deadline': issue.sla_deadline.strftime('%Y-%m-%d %H:%M'),
        'relative_time': f"{hours} hours" if hours < 24 else f"{hours // 24} days",
        'status': issue.get_status_display(),
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/sla_breach_admin.html', context)
    return send_email(admin_user.email, f"SLA Breach: Issue #{issue.id} — {issue.title}", html_content)

def send_maintenance_scheduled_email(user, window):
    """Send maintenance scheduled email to user."""
    if not user.email_maintenance_alerts:
        return False
        
    duration = window.scheduled_end - window.scheduled_start
    hours = int(duration.total_seconds() // 3600)
    
    context = {
        'date': window.scheduled_start.strftime('%Y-%m-%d'),
        'maintenance_title': window.title,
        'maintenance_description': window.description,
        'start_time': window.scheduled_start.strftime('%Y-%m-%d %H:%M'),
        'end_time': window.scheduled_end.strftime('%Y-%m-%d %H:%M'),
        'duration': f"{hours} hours",
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/maintenance_scheduled.html', context)
    return send_email(user.email, f"Scheduled Maintenance — {context['date']}", html_content)

def send_maintenance_reminder_email(user, window):
    """Send 24h maintenance reminder email."""
    if not user.email_maintenance_alerts:
        return False
        
    context = {
        'date': window.scheduled_start.strftime('%Y-%m-%d'),
        'time': window.scheduled_start.strftime('%H:%M'),
        'maintenance_title': window.title,
        'start_time': window.scheduled_start.strftime('%Y-%m-%d %H:%M'),
        'end_time': window.scheduled_end.strftime('%Y-%m-%d %H:%M'),
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/maintenance_reminder_24h.html', context)
    return send_email(user.email, f"Maintenance starts tomorrow — {context['date']} at {context['time']}", html_content)

def send_maintenance_ended_email(user, window):
    """Send maintenance ended confirmation email."""
    if not user.email_maintenance_alerts:
        return False
        
    context = {
        'SITE_URL': settings.SITE_URL
    }
    html_content = render_to_string('emails/maintenance_ended.html', context)
    return send_email(user.email, "CampusFix is back online", html_content)
