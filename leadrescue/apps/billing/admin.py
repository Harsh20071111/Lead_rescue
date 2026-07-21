from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

from apps.billing.models import UpgradeRequest


@admin.register(UpgradeRequest)
class UpgradeRequestAdmin(admin.ModelAdmin):
    list_display = [
        "agency", "requested_plan", "status", "amount",
        "created_at", "razorpay_link_display",
    ]
    list_filter = ["status", "requested_plan"]
    search_fields = ["agency__name", "razorpay_payment_link_id"]
    readonly_fields = ["created_at", "paid_at", "activated_at"]
    actions = ["generate_payment_link", "mark_paid_and_activate"]

    def razorpay_link_display(self, obj):
        if obj.razorpay_payment_link_url:
            return format_html(
                '<a href="{}" target="_blank">Open Link</a>',
                obj.razorpay_payment_link_url,
            )
        return "—"
    razorpay_link_display.short_description = "Payment Link"

    @admin.action(description="Generate Razorpay Payment Link")
    def generate_payment_link(self, request, queryset):
        for upgrade in queryset:
            if upgrade.status not in (UpgradeRequest.Status.PENDING,):
                self.message_user(
                    request,
                    f"Upgrade #{upgrade.pk} is already in status '{upgrade.status}'. Skipping.",
                    level=messages.WARNING,
                )
                continue
            try:
                import razorpay
                from django.conf import settings

                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                amount_paise = int(upgrade.amount * 100)
                callback_url = request.build_absolute_uri(
                    reverse("billing_razorpay_callback")
                )
                response = client.payment_link.create({
                    "amount": amount_paise,
                    "currency": "INR",
                    "description": f"Upgrade {upgrade.agency.name} → {upgrade.requested_plan}",
                    "callback_url": callback_url,
                    "callback_method": "get",
                    "notes": {
                        "upgrade_request_id": str(upgrade.pk),
                        "agency_name": upgrade.agency.name,
                    },
                })
                upgrade.razorpay_payment_link_id = response.get("id")
                upgrade.razorpay_payment_link_url = response.get("short_url")
                upgrade.status = UpgradeRequest.Status.LINK_SENT
                upgrade.save(update_fields=[
                    "razorpay_payment_link_id", "razorpay_payment_link_url",
                    "status",
                ])
                self.message_user(
                    request,
                    f"Payment link generated for {upgrade.agency.name}: {response.get('short_url')}",
                    level=messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to generate link for {upgrade.agency.name}: {e}",
                    level=messages.ERROR,
                )

    @admin.action(description="Mark as Paid & Activate")
    def mark_paid_and_activate(self, request, queryset):
        for upgrade in queryset:
            if upgrade.status in (UpgradeRequest.Status.ACTIVATED,):
                self.message_user(
                    request,
                    f"Upgrade #{upgrade.pk} already activated. Skipping.",
                    level=messages.WARNING,
                )
                continue
            now = timezone.now()
            upgrade.status = UpgradeRequest.Status.PAID
            upgrade.paid_at = now
            upgrade.save(update_fields=["status", "paid_at"])
            upgrade.agency.plan_tier = upgrade.requested_plan
            upgrade.agency.save(update_fields=["plan_tier"])
            upgrade.status = UpgradeRequest.Status.ACTIVATED
            upgrade.activated_at = now
            upgrade.save(update_fields=["status", "activated_at"])
            self.message_user(
                request,
                f"{upgrade.agency.name} activated on {upgrade.requested_plan} plan.",
                level=messages.SUCCESS,
            )
