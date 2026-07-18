import logging

from celery import shared_task

from apps.agencies.models import Agency
from apps.whatsapp.services.qualification import handle_inbound_text
from apps.whatsapp.services.webhooks import iter_inbound_messages, message_text

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
        handle_inbound_text(agency, customer_phone, message_id, message_text(message))

