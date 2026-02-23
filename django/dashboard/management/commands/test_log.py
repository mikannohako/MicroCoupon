from django.core.management.base import BaseCommand
from microcoupon.models import ActivityLog
from account.models import User


class Command(BaseCommand):
    help = 'テストログを作成'

    def handle(self, *args, **options):
        user = User.objects.filter(user_type='admin').first()
        if not user:
            user = User.objects.first()
        
        if user:
            log = ActivityLog.objects.create(
                user=user,
                action='card_create',
                description='テストログです',
                target_model='Card',
                target_id='test-001'
            )
            self.stdout.write(self.style.SUCCESS(f'ログを作成しました: {log}'))
            self.stdout.write(self.style.SUCCESS(f'総ログ数: {ActivityLog.objects.count()}'))
        else:
            self.stdout.write(self.style.ERROR('ユーザーが見つかりません'))
