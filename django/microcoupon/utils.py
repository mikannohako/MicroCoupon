"""
ユーティリティ関数
"""
from .models import ActivityLog
import logging

logger = logging.getLogger(__name__)


def log_activity(user, action, description, target_model='', target_id='', 
                 request=None, extra_data=None):
    """
    アクティビティログを記録する
    
    Args:
        user: ユーザーオブジェクト
        action: アクション種別 (ActivityLog.ACTION_CHOICES)
        description: 説明文
        target_model: 対象モデル名 (optional)
        target_id: 対象ID (optional)
        request: HTTPリクエストオブジェクト (optional)
        extra_data: 追加データ (dict, optional)
    """
    ip_address = None
    user_agent = ''
    
    if request:
        # IPアドレスを取得（プロキシ経由の場合も考慮）
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # ユーザーエージェントを取得
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # 長さ制限
    
    try:
        ActivityLog.objects.create(
            user=user,
            action=action,
            description=description,
            target_model=target_model,
            target_id=str(target_id) if target_id else '',
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {}
        )
        logger.info(f"Activity logged: {action} by {user}")
    except Exception as e:
        # ログ記録の失敗はメイン処理に影響させない
        logger.error(f"Failed to log activity: {action} - {e}", exc_info=True)


def get_client_ip(request):
    """リクエストからクライアントIPアドレスを取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
