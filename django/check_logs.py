import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from microcoupon.models import ActivityLog

# 最新のログを10件表示
logs = ActivityLog.objects.all().order_by('-created_at')[:10]
print(f"\n=== 最新のアクティビティログ (上位10件) ===\n")
for log in logs:
    username = log.user.username if log.user else "Unknown"
    date = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
    action = log.get_action_display()
    print(f"{date} - {username} - {action} - {log.description}")

print(f"\n総ログ数: {ActivityLog.objects.count()}\n")
