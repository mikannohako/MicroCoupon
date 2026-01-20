from django.contrib import admin
from django.utils.html import format_html
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'room',
        'price',
        'stock_badge',
        'is_active',
        'display_order',
        'created_at'
    ]
    list_filter = ['room', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'room__name']
    list_editable = ['display_order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['room']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('room', 'name', 'description')
        }),
        ('価格・在庫', {
            'fields': ('price', 'stock_quantity')
        }),
        ('表示設定', {
            'fields': ('display_order', 'is_active')
        }),
        ('日時情報', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def stock_badge(self, obj):
        """在庫状態をバッジで表示"""
        if obj.stock_quantity == 0:
            color = '#dc3545'
            text = '在庫切れ'
        elif obj.stock_quantity < 10:
            color = '#ffc107'
            text = f'残り{obj.stock_quantity}'
        else:
            color = '#28a745'
            text = f'{obj.stock_quantity}個'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            text
        )
    stock_badge.short_description = '在庫'

