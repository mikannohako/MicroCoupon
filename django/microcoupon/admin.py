from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import Card


@admin.action(description='選択されたカードを有効化')
def activate_cards(modeladmin, request, queryset):
    """選択されたカードを有効化する一括操作"""
    updated = 0
    for card in queryset.filter(status='unused'):
        if card.activate():
            updated += 1
    messages.success(request, f'{updated}枚のカードを有効化しました。')


@admin.action(description='選択されたカードを使用済みにする')
def mark_cards_as_used(modeladmin, request, queryset):
    """選択されたカードを使用済みにする一括操作"""
    updated = 0
    for card in queryset.filter(status='active', balance=0):
        if card.mark_as_used():
            updated += 1
    messages.success(request, f'{updated}枚のカードを使用済みにしました。')


@admin.action(description='選択されたカードの残高をリセット')
def reset_balance(modeladmin, request, queryset):
    """選択されたカードの残高をリセットする一括操作"""
    updated = queryset.update(balance=0)
    messages.success(request, f'{updated}枚のカードの残高をリセットしました。')


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = [
        'serial_number',
        'balance',
        'status_badge',
        'locked_badge',
        'created_at',
        'activated_at',
        'used_at',
    ]
    list_filter = ['status', 'is_locked', 'created_at', 'activated_at']
    search_fields = ['serial_number']
    readonly_fields = ['id', 'created_at', 'activated_at', 'used_at', 'serial_number']
    list_per_page = 50
    actions = [activate_cards, mark_cards_as_used, reset_balance]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('id', 'serial_number', 'balance', 'status')
        }),
        ('セキュリティ', {
            'fields': ('is_locked',)
        }),
        ('日時情報', {
            'fields': ('created_at', 'activated_at', 'used_at')
        }),
    )
    
    def status_badge(self, obj):
        """ステータスをバッジで表示"""
        colors = {
            'unused': '#6c757d',
            'active': '#28a745',
            'used': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'
    
    def locked_badge(self, obj):
        """ロック状態をバッジで表示"""
        if obj.is_locked:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">🔒 ロック中</span>'
            )
        return format_html(
            '<span style="background-color: #e9ecef; color: black; padding: 3px 10px; border-radius: 3px;">🔓 解除</span>'
        )
    locked_badge.short_description = 'ロック'
    
    def save_model(self, request, obj, form, change):
        """モデル保存時の処理"""
        if change:
            if 'status' in form.changed_data:
                if obj.status == 'active' and not obj.activated_at:
                    obj.activated_at = timezone.now()
                elif obj.status == 'used' and not obj.used_at:
                    obj.used_at = timezone.now()
        super().save_model(request, obj, form, change)
