import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from account.models import User
from django.test import RequestFactory
from account.views import login_view

# テスト用リクエストを作成
factory = RequestFactory()

# ログインテスト
request = factory.post('/account/login/', {
    'username': 'mikannohako',
    'password': 'AdminMikan1144'  # 実際のパスワードに置き換えてください
})

# セッションを有効にするための設定
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

msg_middleware = MessageMiddleware(lambda x: None)
msg_middleware.process_request(request)

# ログイン実行
response = login_view(request)

print(f"ログインテスト実行完了")
print(f"レスポンスステータス: {response.status_code}")

# ログを確認
from microcoupon.models import ActivityLog

recent_login_logs = ActivityLog.objects.filter(action='user_login').order_by('-created_at')[:3]
print(f"\n最新のログインログ:")
for log in recent_login_logs:
    print(f"  - {log.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {log.user.username if log.user else 'Unknown'} - {log.description}")
