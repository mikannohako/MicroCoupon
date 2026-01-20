from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid


class Card(models.Model):
    """
    プリペイドカードモデル
    """
    STATUS_CHOICES = [
        ('unused', '未使用'),
        ('active', '有効'),
        ('used', '使用済み'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name='シリアル番号'
    )
    balance = models.PositiveIntegerField(default=1000, verbose_name='残高(pt)')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='unused',
        verbose_name='ステータス'
    )
    is_locked = models.BooleanField(default=False, verbose_name='ロック中（2重決済防止）')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name='有効化日時')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='使用済み日時')

    class Meta:
        verbose_name = 'カード'
        verbose_name_plural = 'カード'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.serial_number} - {self.get_status_display()} - {self.balance}pt"
    
    def save(self, *args, **kwargs):
        # serial_numberが未設定の場合のみUUIDを生成
        if not self.serial_number:
            self.serial_number = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def activate(self):
        """カードを有効化する"""
        if self.status == 'unused':
            self.status = 'active'
            self.activated_at = timezone.now()
            self.save()
            return True
        return False
    
    def mark_as_used(self):
        """カードを使用済みにする"""
        if self.status == 'active' and self.balance == 0:
            self.status = 'used'
            self.used_at = timezone.now()
            self.save()
            return True
        return False

    def deduct(self, amount):
        """
        カードからポイントを減算するメソッド
        同時アクセス時はトランザクション必須
        """
        if self.is_locked or self.status != 'active':
            raise Exception("カード利用不可")
        if self.balance < amount:
            raise Exception("残高不足")

        self.is_locked = True
        self.save(update_fields=['is_locked'])

        # 減算処理
        self.balance -= amount
        if self.balance == 0:
            self.status = 'used'
            self.used_at = timezone.now()
        self.is_locked = False
        self.save(update_fields=['balance', 'status', 'used_at', 'is_locked'])
