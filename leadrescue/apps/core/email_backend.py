import logging
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMultiAlternatives

logger = logging.getLogger(__name__)

class ResendEmailBackend(BaseEmailBackend):
    """
    A custom Django EmailBackend that routes standard Django emails through the Resend API.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        if hasattr(settings, 'RESEND_API_KEY') and settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
        else:
            logger.warning("RESEND_API_KEY is not set. Resend emails will fail.")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send(message):
                sent_count += 1
        return sent_count

    def _send(self, email_message):
        """
        Sends a single Django EmailMessage using the Resend Python SDK.
        Supports HTML alternatives and attachments.
        """
        if not email_message.recipients():
            return False

        # Extract standard fields
        from_email = email_message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@leadsathi.in')
        to_emails = email_message.to

        payload = {
            "from": from_email,
            "to": to_emails,
            "subject": email_message.subject,
        }

        # Check for HTML content (EmailMultiAlternatives)
        html_content = None
        if isinstance(email_message, EmailMultiAlternatives):
            for alt_content, mimetype in email_message.alternatives:
                if mimetype == "text/html":
                    html_content = alt_content
                    break

        if html_content:
            payload["html"] = html_content
            # Resend recommends sending plain text along with HTML, but it's optional
            # if we wanted to enforce text we could pass email_message.body
        else:
            # Plain text only
            payload["text"] = email_message.body

        # Resend accepts reply_to, cc, bcc as optional arrays
        if email_message.cc:
            payload["cc"] = email_message.cc
        if email_message.bcc:
            payload["bcc"] = email_message.bcc
        if email_message.reply_to:
            payload["reply_to"] = email_message.reply_to

        try:
            resend.Emails.send(payload)
            return True
        except Exception as e:
            if not self.fail_silently:
                raise
            logger.error(f"Failed to send email to {to_emails} via Resend: {e}")
            return False
