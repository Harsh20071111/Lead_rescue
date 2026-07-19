import logging

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import authenticate
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY = "admin_login_attempts"
RATE_LIMIT_MAX = 5
RATE_LIMIT_TIMEOUT = 60 * 15


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(ip):
    key = f"{RATE_LIMIT_KEY}:{ip}"
    return cache.get(key, 0) >= RATE_LIMIT_MAX


def record_failed_attempt(ip):
    key = f"{RATE_LIMIT_KEY}:{ip}"
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, RATE_LIMIT_TIMEOUT)
    return RATE_LIMIT_MAX - (attempts + 1)


def clear_attempts(ip):
    cache.delete(f"{RATE_LIMIT_KEY}:{ip}")


# Apply custom settings to the default admin site
admin.site.site_header = "LeadSathi Administration"
admin.site.site_title = "LeadSathi Admin"
admin.site.index_title = "Site Administration"
admin.site.login_template = "admin/login.html"

# Save the original login method
_original_admin_login = admin.site.login

@method_decorator(csrf_protect)
@method_decorator(never_cache)
def admin_login_view(request, extra_context=None):
    ip = _get_client_ip(request)

    if request.method == "POST":
        if is_rate_limited(ip):
            logger.warning("Admin login rate limited for IP %s", ip)
            extra_context = extra_context or {}
            extra_context["error_message"] = (
                "Too many failed attempts. Try again in 15 minutes."
            )
            return _original_admin_login(request, extra_context=extra_context)

        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            remaining = record_failed_attempt(ip)
            logger.warning(
                "Failed admin login for '%s' from IP %s (%d left)",
                username, ip, remaining,
            )
            extra_context = extra_context or {}
            if remaining <= 2:
                extra_context["error_message"] = (
                    f"Invalid credentials. {remaining} attempt(s) before lockout."
                )
        else:
            clear_attempts(ip)

    return _original_admin_login(request, extra_context=extra_context)

# Monkey-patch the login view
admin.site.login = admin_login_view


class AdminOnlyMiddleware:
    """Block non-superusers from accessing admin and protect old /admin/ URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith("/admin/"):
            from django.http import Http404
            raise Http404

        return self.get_response(request)
