from django.db import models
from django.core.validators import MinValueValidator


class Product(models.Model):
    """商品"""
    room = models.ForeignKey(
        'account.Room',
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='店舗',
        null=True
    )
    name = models.CharField(max_length=200, verbose_name='品目')
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='値段(pt)'
    )
    description = models.TextField(blank=True, verbose_name='説明')
    is_active = models.BooleanField(default=True, verbose_name='販売中')
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='在庫数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['room', 'display_order', 'name']
        unique_together = [['room', 'name']]

    def __str__(self):
        return f"{self.room.name} - {self.name} ({self.price}pt)"

    def is_in_stock(self):
        """在庫があるかチェック"""
        return self.stock_quantity > 0

    def reduce_stock(self, quantity=1):
        """在庫を減らす"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save(update_fields=['stock_quantity'])
            return True
        return False

