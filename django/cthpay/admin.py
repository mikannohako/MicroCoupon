from django.contrib import admin
from .models import Card

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'balance', 'status', 'is_locked', 'created_at', 'used_at')
    list_filter = ('status', 'is_locked')
    search_fields = ('serial_number',)
