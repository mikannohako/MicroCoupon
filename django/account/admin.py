from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'user_type', 'room', 'is_active', 'is_staff']
    list_filter = ['user_type', 'room', 'is_active', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('追加情報', {'fields': ('user_type', 'room')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('追加情報', {'fields': ('user_type', 'room')}),
    )
