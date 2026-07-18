from django.contrib import admin

from .models import WhatsAppConversation, WhatsAppMessage


class WhatsAppMessageInline(admin.TabularInline):
    model = WhatsAppMessage
    extra = 0
    readonly_fields = ("direction", "message_id", "content", "created_at")
    can_delete = False


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ("agency", "customer_phone", "state", "lead", "is_active", "updated_at")
    list_filter = ("state", "is_active", "agency")
    search_fields = ("customer_phone", "lead__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [WhatsAppMessageInline]


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "direction", "message_id", "created_at")
    list_filter = ("direction",)
    search_fields = ("message_id", "content", "conversation__customer_phone")
    readonly_fields = ("created_at",)

