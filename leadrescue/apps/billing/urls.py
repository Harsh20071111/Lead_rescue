from django.urls import path
from apps.billing.views import (
    UpgradeRequiredView,
    UpgradeView,
    UpgradeConfirmationView,
    RazorpayCallbackView,
    BillingHomeView,
)
from apps.billing.webhook import razorpay_webhook

urlpatterns = [
    path("upgrade/", UpgradeRequiredView.as_view(), name="upgrade_required"),
    path("upgrade/<str:plan>/", UpgradeView.as_view(), name="billing_upgrade"),
    path("confirmation/", UpgradeConfirmationView.as_view(), name="billing_confirmation"),
    path("callback/", RazorpayCallbackView.as_view(), name="billing_razorpay_callback"),
    path("", BillingHomeView.as_view(), name="billing_home"),
    path("webhook/razorpay/", razorpay_webhook, name="billing_razorpay_webhook"),
]
