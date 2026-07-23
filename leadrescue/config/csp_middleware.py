"""
Content-Security-Policy middleware for LeadSathi.
Adds a restrictive CSP header to all responses in production.
"""


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only add CSP in production (when DEBUG is False)
        from django.conf import settings
        if not settings.DEBUG:
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://js.razorpay.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https://res.cloudinary.com; "
                "media-src 'self' https://res.cloudinary.com; "
                "connect-src 'self' https://api.cloudinary.com https://api.razorpay.com wss:; "
                "frame-src https://js.razorpay.com; "
            )

        return response
