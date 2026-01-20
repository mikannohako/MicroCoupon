from django.db import models
from django.utils import timezone
from microcoupon.models import Card
from products.models import Product


class Transaction(models.Model):
    """決済ログ"""
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='カード'
    )
    total_amount = models.PositiveIntegerField(verbose_name='合計金額(pt)')
    status = models.CharField(
        max_length=20,
        choices=[
            ('completed', '完了'),
            ('failed', '失敗'),
            ('cancelled', 'キャンセル'),
        ],
        default='completed',
        verbose_name='ステータス'
    )
    error_message = models.TextField(blank=True, verbose_name='エラーメッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='決済日時')
    created_by = models.CharField(max_length=150, blank=True, verbose_name='操作者')

    class Meta:
        verbose_name = '決済ログ'
        verbose_name_plural = '決済ログ'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card.serial_number} - {self.total_amount}pt - {self.get_status_display()}"


class TransactionItem(models.Model):
    """決済明細"""
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='決済'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='商品'
    )
    product_name = models.CharField(max_length=200, verbose_name='品名')
    product_price = models.PositiveIntegerField(verbose_name='単価(pt)')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')

    class Meta:
        verbose_name = '決済明細'
        verbose_name_plural = '決済明細'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} = {self.subtotal}pt"

    @property
    def subtotal(self):
        """小計"""
        return self.product_price * self.quantity

