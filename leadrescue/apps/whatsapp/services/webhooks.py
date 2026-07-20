import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_signature(body, signature_header, app_secret):
    if not app_secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def iter_inbound_messages(payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
            for message in value.get("messages", []):
                yield phone_number_id, message


def message_text(message):
    """Extract text from an inbound message (text or interactive reply)."""
    message_type = message.get("type")
    if message_type == "text":
        return message.get("text", {}).get("body", "").strip()
    if message_type == "interactive":
        interactive = message.get("interactive", {})
        reply_type = interactive.get("type")
        if reply_type == "list_reply":
            reply = interactive.get("list_reply", {})
            return reply.get("id", "").strip()
        if reply_type == "button_reply":
            reply = interactive.get("button_reply", {})
            return reply.get("id", "").strip()
    logger.debug("Unhandled message type %s: %s", message_type, message)
    return ""


def message_is_interactive(message):
    """Check if the inbound message is an interactive reply."""
    return message.get("type") == "interactive"
