import os
import django


def main() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    from account.models import User
    from microcoupon.models import Card
    from microcoupon.utils import log_activity

    # 管理者ユーザー取得
    user = User.objects.filter(is_staff=True).first()

    # テストカード作成
    card = Card.objects.create(
        balance=1000
    )

    # ログ記録
    try:
        log_activity(
            user=user,
            action='card_create',
            description=f'テストカード作成: {card.serial_number}',
            target_model='Card',
            target_id=card.id
        )
        print(f"✓ カード {card.serial_number} 作成成功")
        print(f"✓ アクティビティログ記録成功")
    except Exception as e:
        print(f"✗ ログ記録エラー: {e}")


if __name__ == '__main__':
    main()
