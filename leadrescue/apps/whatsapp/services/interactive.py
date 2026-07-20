"""WhatsApp Cloud API interactive message helpers.

List Messages  — up to 10 rows per section, multiple sections
Button Messages — up to 3 buttons
Document Messages — send brochures as PDFs
"""

import logging

from apps.agencies.models import Agency
from apps.whatsapp.services.client import _require_credentials, _post_message

logger = logging.getLogger(__name__)


def send_list_message(agency, phone, header, body, button_text, sections):
    """Send an interactive list message.

    sections: list of dicts
        [{"title": "Section title", "rows": [{"id": "unique_id", "title": "Row label", "description": "..."}]}]
    """
    _require_credentials(agency)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        },
    }
    return _post_message(agency, payload)


def send_button_message(agency, phone, header, body, buttons):
    """Send an interactive button message (max 3 buttons).

    buttons: list of dicts
        [{"id": "unique_id", "title": "Button label"}]
    """
    _require_credentials(agency)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": btn["id"], "title": btn["title"]},
                    }
                    for btn in buttons
                ],
            },
        },
    }
    return _post_message(agency, payload)


def send_document_message(agency, phone, document_url, caption, filename=None):
    """Send a document (PDF brochure) via link."""
    _require_credentials(agency)
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "document",
        "document": {
            "link": document_url,
            "caption": caption or "",
        },
    }
    if filename:
        payload["document"]["filename"] = filename
    return _post_message(agency, payload)


def send_text_reply(agency, phone, body):
    """Send a simple text reply."""
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    return _post_message(agency, payload)
