import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from apps.agencies.models import Agency
from apps.billing.decorators import RequireFeatureMixin
from apps.billing.entitlements import has_feature
from apps.core.mixins import OwnerRequiredMixin
from apps.whatsapp.forms import WhatsAppSettingsForm
from apps.whatsapp.services.webhooks import verify_signature
from apps.whatsapp.tasks import process_whatsapp_webhook

logger = logging.getLogger(__name__)

DEFAULT_BUDGET_BRACKETS = ["Under 50L", "50L–1Cr", "1Cr–2Cr", "2Cr+"]


class WhatsAppSettingsView(OwnerRequiredMixin, RequireFeatureMixin, View):
    template_name = "whatsapp/settings.html"
    required_feature = "whatsapp_bot"

    def get(self, request):
        brackets = self.agency.budget_brackets or DEFAULT_BUDGET_BRACKETS
        form = WhatsAppSettingsForm(
            agency=self.agency,
            initial={
                "phone_number_id": self.agency.whatsapp_phone_number_id,
                "business_account_id": self.agency.whatsapp_business_account_id,
                "display_name": self.agency.whatsapp_display_name,
                "budget_brackets": ", ".join(brackets),
            },
        )
        return render(request, self.template_name, {"form": form, "agency": self.agency})

    def post(self, request):
        form = WhatsAppSettingsForm(request.POST, agency=self.agency)
        if form.is_valid():
            phone_number_id = form.cleaned_data.get("phone_number_id", "").strip()

            if phone_number_id:
                # Connect mode
                self.agency.whatsapp_phone_number_id = phone_number_id
                self.agency.whatsapp_business_account_id = form.cleaned_data["business_account_id"]
                self.agency.whatsapp_access_token = form.cleaned_data["access_token"]
                self.agency.whatsapp_display_name = (
                    form.cleaned_data["display_name"]
                    or form.cleaned_data.get("meta_details", {}).get("verified_name")
                    or self.agency.name
                )
                self.agency.whatsapp_status = Agency.WhatsAppStatus.CONNECTED
                self.agency.whatsapp_connected_at = timezone.now()

            brackets = form.cleaned_data.get("budget_brackets")
            if brackets is not None:
                self.agency.budget_brackets = brackets

            self.agency.save(
                update_fields=[
                    "whatsapp_phone_number_id",
                    "whatsapp_business_account_id",
                    "whatsapp_access_token",
                    "whatsapp_display_name",
                    "whatsapp_status",
                    "whatsapp_connected_at",
                    "budget_brackets",
                ]
            )
            messages.success(request, "WhatsApp settings saved.")
            return redirect("whatsapp:settings")
        return render(request, self.template_name, {"form": form, "agency": self.agency})


@require_POST
@login_required
def disconnect_whatsapp(request):
    if request.user.agent_profile.role != "owner":
        return HttpResponseForbidden()
    agency = request.user.agent_profile.agency
    agency.whatsapp_phone_number_id = None
    agency.whatsapp_business_account_id = None
    agency.whatsapp_access_token = None
    agency.whatsapp_display_name = None
    agency.whatsapp_status = Agency.WhatsAppStatus.NOT_CONNECTED
    agency.whatsapp_connected_at = None
    agency.save(
        update_fields=[
            "whatsapp_phone_number_id",
            "whatsapp_business_account_id",
            "whatsapp_access_token",
            "whatsapp_display_name",
            "whatsapp_status",
            "whatsapp_connected_at",
        ]
    )
    messages.success(request, "WhatsApp disconnected.")
    return redirect("whatsapp:settings")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if (
            mode == "subscribe"
            and token
            and token == getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        ):
            return HttpResponse(challenge or "")
        return HttpResponseForbidden()

    body = request.body
    if not verify_signature(
        body,
        request.headers.get("X-Hub-Signature-256"),
        getattr(settings, "WHATSAPP_APP_SECRET", ""),
    ):
        return HttpResponseForbidden()

    payload = json.loads(body.decode() or "{}")
    phone_number_id = _payload_phone_number_id(payload)
    agency = (
        Agency.objects.filter(
            whatsapp_phone_number_id=phone_number_id,
            whatsapp_status=Agency.WhatsAppStatus.CONNECTED,
        )
        .first()
    )
    if not agency:
        logger.warning("WhatsApp webhook received for unknown phone_number_id=%s", phone_number_id)
        return HttpResponse("ok")

    if not has_feature(agency, "whatsapp_bot"):
        logger.info("WhatsApp webhook ignored for free-tier agency=%s", agency.id)
        return HttpResponse("ok")

    process_whatsapp_webhook.delay(agency.id, payload)
    return HttpResponse("ok")


def _payload_phone_number_id(payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            phone_number_id = (
                change.get("value", {})
                .get("metadata", {})
                .get("phone_number_id")
            )
            if phone_number_id:
                return phone_number_id
    return None
