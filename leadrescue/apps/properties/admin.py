from django.contrib import admin
from .models import Property

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'agency', 'price', 'bhk', 'city', 'status')
    search_fields = ('title', 'location', 'city')
    list_filter = ('status', 'agency')
