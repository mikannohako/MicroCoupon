from django.contrib.auth.models import AbstractUser
from django.db import models


class Room(models.Model):
    """教室モデル（旧ProductCategory）"""
    name = models.CharField('教室名', max_length=100)
    description = models.TextField('説明', blank=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '教室'
        verbose_name_plural = '教室'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """カスタムユーザーモデル"""
    USER_TYPE_CHOICES = [
        ('admin', '管理者'),
        ('staff', '店員'),
    ]
    
    user_type = models.CharField('ユーザータイプ', max_length=10, choices=USER_TYPE_CHOICES, default='staff')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属教室', related_name='users')
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'

    def is_admin(self):
        return self.user_type == 'admin'

    def is_staff_user(self):
        return self.user_type == 'staff'
