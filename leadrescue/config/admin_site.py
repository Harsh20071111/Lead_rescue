from django.contrib import admin

# Apply custom settings to the default admin site
admin.site.site_header = "LeadSathi Administration"
admin.site.site_title = "LeadSathi Admin"
admin.site.index_title = "Site Administration"
admin.site.login_template = "admin/login.html"


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
