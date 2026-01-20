from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction, TransactionItem


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_price', 'quantity', 'subtotal']
    can_delete = False

    def subtotal(self, obj):
        return f"{obj.subtotal}pt"
    subtotal.short_description = '小計'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'card_serial',
        'total_amount',
        'status_badge',
        'created_by',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['card__serial_number', 'created_by']
    readonly_fields = ['card', 'total_amount', 'status', 'error_message', 'created_at', 'created_by']
    inlines = [TransactionItemInline]
    
    fieldsets = (
        ('決済情報', {
            'fields': ('card', 'total_amount', 'status', 'error_message')
        }),
        ('操作情報', {
            'fields': ('created_at', 'created_by')
        }),
    )
    
    def card_serial(self, obj):
        """カードシリアル番号"""
        return obj.card.serial_number
    card_serial.short_description = 'カード'
    
    def status_badge(self, obj):
        """ステータスバッジ"""
        colors = {
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'product_name', 'product_price', 'quantity', 'subtotal']
    list_filter = ['transaction__created_at']
    readonly_fields = ['transaction', 'product', 'product_name', 'product_price', 'quantity']
    
    def subtotal(self, obj):
        return f"{obj.subtotal}pt"
    subtotal.short_description = '小計'

