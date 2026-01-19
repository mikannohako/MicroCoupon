from django.db import models
from django.utils import timezone
import uuid

class Card(models.Model):
    STATUS_CHOICES = [
        ('unused', '未使用'),
        ('active', '有効'),
        ('used', '使用済み'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    serial_number = models.CharField(max_length=50, unique=True)
    balance = models.PositiveIntegerField(default=1000)  # 初期pt
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unused')
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.serial_number} - {self.status} - {self.balance}pt"

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
