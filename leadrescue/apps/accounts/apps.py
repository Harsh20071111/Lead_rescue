from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self):
        from django.contrib import admin
        admin.site.login_template = "admin/login.html"
        admin.site.site_header = "LeadSathi Administration"
        admin.site.site_title = "LeadSathi Admin"
        admin.site.index_title = "Site Administration"
