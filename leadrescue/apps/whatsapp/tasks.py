import logging

from celery import shared_task

from apps.agencies.models import Agency
from apps.whatsapp.services.qualification import handle_inbound_message
from apps.whatsapp.services.webhooks import (
    iter_inbound_messages,
    message_is_interactive,
    message_text,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_whatsapp_webhook(self, agency_id, payload):
    agency = Agency.objects.get(pk=agency_id)
    for phone_number_id, message in iter_inbound_messages(payload):
        if phone_number_id != agency.whatsapp_phone_number_id:
            logger.warning(
                "Webhook payload phone_number_id %s did not match agency %s",
                phone_number_id,
                agency_id,
            )
            continue
        message_id = message.get("id")
        customer_phone = message.get("from")
        if not message_id or not customer_phone:
            logger.warning("Skipping malformed WhatsApp message for agency %s", agency_id)
            continue

        content = message_text(message)
        is_interactive = message_is_interactive(message)

        handle_inbound_message(
            agency, customer_phone, message_id, content,
            is_interactive=is_interactive,
        )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_whatsapp_list_message(self, agency_id, phone, header, body, button_text, sections):
    from apps.whatsapp.services.interactive import send_list_message
    agency = Agency.objects.get(pk=agency_id)
    return send_list_message(agency, phone, header, body, button_text, sections)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_whatsapp_button_message(self, agency_id, phone, header, body, buttons):
    from apps.whatsapp.services.interactive import send_button_message
    agency = Agency.objects.get(pk=agency_id)
    return send_button_message(agency, phone, header, body, buttons)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_whatsapp_document(self, agency_id, phone, document_url, caption, filename=None):
    from apps.whatsapp.services.interactive import send_document_message
    agency = Agency.objects.get(pk=agency_id)
    return send_document_message(agency, phone, document_url, caption, filename)
