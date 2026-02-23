from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
import uuid
import secrets

User = get_user_model()


class Card(models.Model):
    """
    プリペイドカードモデル
    """
    STATUS_CHOICES = [
        ('unused', '未使用'),
        ('active', '有効'),
        ('used', '使用済み'),
        ('deleted', '削除済み'),
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

    def issue_temporary_code(self, valid_minutes=5):
        """このカード用の4桁一時コードを発行する（既存未使用コードは破棄）"""
        return TemporaryCardCode.issue_for_card(self, valid_minutes=valid_minutes)

    @staticmethod
    def resolve_identifier(identifier, consume_temp_code=False):
        """シリアル番号または4桁一時コードからカードを解決する。"""
        token = (identifier or '').strip()
        if not token:
            return None

        try:
            return Card.objects.get(serial_number=token)
        except Card.DoesNotExist:
            temp_code = TemporaryCardCode.get_valid_code(token)
            if not temp_code:
                return None
            card = temp_code.card
            if consume_temp_code:
                temp_code.delete()
            return card


class TemporaryCardCode(models.Model):
    """手入力用の4桁一時コード"""
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='temporary_codes', verbose_name='カード')
    code = models.CharField(max_length=4, db_index=True, verbose_name='一時コード')
    expires_at = models.DateTimeField(db_index=True, verbose_name='有効期限')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        verbose_name = 'カード一時コード'
        verbose_name_plural = 'カード一時コード'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.card.serial_number})"

    @classmethod
    def get_valid_code(cls, code):
        now = timezone.now()
        return cls.objects.select_related('card').filter(
            code=code,
            expires_at__gt=now,
        ).first()

    @classmethod
    def issue_for_card(cls, card, valid_minutes=5):
        """カードに対して未使用コードを1つだけ有効化して返す。"""
        now = timezone.now()
        with db_transaction.atomic():
            # 同一カードの有効コードは常に1つだけにする
            cls.objects.filter(card=card, expires_at__gt=now).delete()

            for _ in range(30):
                code = f"{secrets.randbelow(10000):04d}"
                exists = cls.objects.filter(code=code, expires_at__gt=now).exists()
                if not exists:
                    return cls.objects.create(
                        card=card,
                        code=code,
                        expires_at=now + timezone.timedelta(minutes=valid_minutes),
                    )

        raise Exception('一時コードの発行に失敗しました')


class ActivityLog(models.Model):
    """
    システムアクティビティログモデル
    編集・削除不可の監査ログ
    """
    ACTION_CHOICES = [
        ('card_create', 'カード作成'),
        ('card_activate', 'カード有効化'),
        ('card_edit', 'カード編集'),
        ('card_delete', 'カード削除'),
        ('product_create', '商品作成'),
        ('product_edit', '商品編集'),
        ('product_delete', '商品削除'),
        ('transaction_create', '取引作成'),
        ('transaction_complete', '取引完了'),
        ('transaction_cancel', '取引キャンセル'),
        ('user_create', 'ユーザー作成'),
        ('user_edit', 'ユーザー編集'),
        ('user_delete', 'ユーザー削除'),
        ('user_login', 'ログイン'),
        ('user_logout', 'ログアウト'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='実行ユーザー')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name='アクション')
    description = models.TextField(verbose_name='説明')
    target_model = models.CharField(max_length=50, blank=True, verbose_name='対象モデル')
    target_id = models.CharField(max_length=100, blank=True, verbose_name='対象ID')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IPアドレス')
    user_agent = models.TextField(blank=True, verbose_name='ユーザーエージェント')
    extra_data = models.JSONField(default=dict, blank=True, verbose_name='追加データ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='実行日時', db_index=True)
    
    class Meta:
        verbose_name = 'アクティビティログ'
        verbose_name_plural = 'アクティビティログ'
        ordering = ['-created_at']
        permissions = [
            ('view_activity_log', 'アクティビティログを閲覧可能'),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else '不明'
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {user_str} - {self.get_action_display()}"
    
    def save(self, *args, **kwargs):
        # 新規作成のみ許可（更新は不可）
        # force_insert=True は create() メソッドで自動的に設定される
        if 'force_insert' not in kwargs and self.pk is not None:
            # 既に PK があり force_insert でない = 更新処理
            raise Exception('ログの更新は許可されていません')
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # 削除を禁止
        raise Exception('ログの削除は許可されていません')
