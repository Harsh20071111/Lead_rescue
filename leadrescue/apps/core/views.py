from django.http import JsonResponse
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    """Landing page — converts the provided React design to Django template."""

    template_name = "pages/home.html"


def health_check(request):
    """Simple health check endpoint for monitoring and load balancers."""
    return JsonResponse({"status": "ok"})


class ContactPageView(TemplateView):
    template_name = "pages/contact.html"
