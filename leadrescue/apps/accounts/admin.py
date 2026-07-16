from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from .models import User, AgentProfile

@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    pass

@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency', 'role', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('role', 'agency')
