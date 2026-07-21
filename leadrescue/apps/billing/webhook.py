import json
import hmac
import hashlib
import logging

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from apps.billing.models import UpgradeRequest

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
    if not signature:
        logger.warning("Razorpay webhook missing signature header")
        return HttpResponseBadRequest("Missing signature")

    body = request.body
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Razorpay webhook signature mismatch")
        return HttpResponseBadRequest("Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Razorpay webhook invalid JSON")
        return HttpResponseBadRequest("Invalid JSON")

    event = payload.get("event", "")
    if event == "payment_link.paid":
        payment_link = payload.get("payload", {}).get("payment_link", {})
        payment_link_id = payment_link.get("id")
        if not payment_link_id:
            logger.warning("payment_link.paid event missing payment_link.id")
            return JsonResponse({"status": "ignored"}, status=200)

        try:
            upgrade = UpgradeRequest.objects.get(razorpay_payment_link_id=payment_link_id)
        except UpgradeRequest.DoesNotExist:
            logger.info(
                "No UpgradeRequest found for payment_link_id=%s — ignoring",
                payment_link_id,
            )
            return JsonResponse({"status": "ignored"}, status=200)

        now = timezone.now()
        upgrade.status = UpgradeRequest.Status.PAID
        upgrade.paid_at = now
        upgrade.save(update_fields=["status", "paid_at"])

        upgrade.agency.plan_tier = upgrade.requested_plan
        upgrade.agency.save(update_fields=["plan_tier"])

        upgrade.status = UpgradeRequest.Status.ACTIVATED
        upgrade.activated_at = now
        upgrade.save(update_fields=["status", "activated_at"])

        logger.info(
            "Agency %s activated on %s via webhook (link %s)",
            upgrade.agency_id, upgrade.requested_plan, payment_link_id,
        )
        return JsonResponse({"status": "activated"}, status=200)

    logger.debug("Razorpay webhook received unhandled event: %s", event)
    return JsonResponse({"status": "ignored"}, status=200)
