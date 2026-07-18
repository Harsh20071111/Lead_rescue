import logging

import requests

from apps.agencies.models import Agency

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


class WhatsAppClientError(Exception):
    pass


def _require_credentials(agency):
    if not agency.whatsapp_phone_number_id or not agency.whatsapp_access_token:
        raise WhatsAppClientError("Agency WhatsApp credentials are incomplete.")


def mark_agency_error(agency, reason):
    logger.error("WhatsApp credentials failed for agency %s: %s", agency.pk, reason)
    agency.whatsapp_status = Agency.WhatsAppStatus.ERROR
    agency.save(update_fields=["whatsapp_status"])


def validate_phone_number_token(phone_number_id, access_token):
    response = requests.get(
        f"{GRAPH_API_BASE}/{phone_number_id}",
        params={"fields": "id,display_phone_number,verified_name"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if response.status_code >= 400:
        raise WhatsAppClientError(response.text)
    return response.json()


def send_text(agency, phone, message):
    _require_credentials(agency)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    return _post_message(agency, payload)


def send_template(agency, phone, template_name, params=None):
    _require_credentials(agency)
    params = params or []
    components = []
    if params:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(value)} for value in params],
            }
        )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
            "components": components,
        },
    }
    return _post_message(agency, payload)


def _post_message(agency, payload):
    response = requests.post(
        f"{GRAPH_API_BASE}/{agency.whatsapp_phone_number_id}/messages",
        json=payload,
        headers={"Authorization": f"Bearer {agency.whatsapp_access_token}"},
        timeout=15,
    )
    if response.status_code >= 400:
        mark_agency_error(agency, response.text)
        raise WhatsAppClientError(response.text)
    return response.json()

