import hashlib
import hmac


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
    message_type = message.get("type")
    if message_type == "text":
        return message.get("text", {}).get("body", "").strip()
    return f"[{message_type or 'unsupported'} message]"

