import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def _send_leadsathi_email(subject, template_name, context, recipient_list):
    """
    Shared private helper for rendering and sending LeadSathi emails.
    """
    try:
        html_content = render_to_string(template_name, context)
        # Fallback to plain text for email clients that don't support HTML
        text_content = strip_tags(html_content)
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@leadsathi.in')
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(
            "Failed to send %s email to %s: %s",
            template_name, recipient_list, e, exc_info=True
        )
        return False


def send_welcome_email(user):
    """
    Sends a welcome email to a newly created agent/owner.
    """
    # Assuming login_url points to dashboard or login
    context = {
        'user': user,
        'login_url': f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}/login/",
    }
    
    # We construct the URL securely if possible, or just a relative path if the domain is known
    # Note: For production, we typically use the Sites framework or an explicit env var for the domain
    # Here we just use a generic path assuming they know where they signed up
    context['login_url'] = "https://leadsathi.in/login/" if not settings.DEBUG else "http://localhost:8000/login/"
    
    return _send_leadsathi_email(
        subject=f"Welcome to LeadSathi, {user.first_name or 'Agent'}!",
        template_name="emails/welcome.html",
        context=context,
        recipient_list=[user.email]
    )

def send_agent_invite_email(invite):
    """
    Sends an invitation email to a new agent.
    """
    context = {
        'inviter_name': invite.agency.owner_email, # Simple fallback if owner name isn't on agency
        'invite_url': f"https://leadsathi.in/invites/accept/{invite.token}/" if not settings.DEBUG else f"http://localhost:8000/invites/accept/{invite.token}/",
    }
    return _send_leadsathi_email(
        subject="You've been invited to join LeadSathi",
        template_name="emails/agent_invite.html",
        context=context,
        recipient_list=[invite.email]
    )

def send_followup_reminder(task):
    """
    Sends a reminder for an upcoming follow-up task.
    """
    context = {
        'agent': task.assigned_to.user,
        'task': task,
        'lead': getattr(task, 'lead', None),
        'task_url': f"https://leadsathi.in/dashboard/" if not settings.DEBUG else f"http://localhost:8000/dashboard/",
    }
    return _send_leadsathi_email(
        subject=f"Upcoming Follow-up Reminder: {task.title}",
        template_name="emails/followup_reminder.html",
        context=context,
        recipient_list=[task.assigned_to.user.email]
    )

# --- Placeholders for future emails (Phase 4 / Notifications) ---

def send_lead_assigned_email(lead):
    pass

def send_lead_status_changed_email(lead, old_status, new_status):
    pass

def send_daily_reminder(agent):
    pass

def send_weekly_summary(agent):
    pass
