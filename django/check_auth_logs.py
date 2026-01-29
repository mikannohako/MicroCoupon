import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from microcoupon.models import ActivityLog

# ログイン/ログアウトのログを確認
logs = ActivityLog.objects.filter(action__in=['user_login', 'user_logout']).order_by('-created_at')[:10]

print("\n=== ログイン/ログアウトのログ (上位10件) ===\n")
if logs.exists():
    for log in logs:
        username = log.user.username if log.user else "Unknown"
        date = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
        action = log.get_action_display()
        print(f"{date} - {username} - {action} - {log.description}")
else:
    print("ログイン/ログアウトのログはまだありません")

print(f"\n総ログイン/ログアウトログ数: {logs.count()}\n")
