#!/usr/bin/env python
"""
PDF生成のテストスクリプト
"""
import os
import sys
import django

# Djangoの初期化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from dashboard.views import generate_cards_pdf
from microcoupon.models import Card

# テスト用カードを取得
cards = Card.objects.order_by('-created_at')[:3]
print(f'テスト対象カード: {len(cards)}枚')
for i, card in enumerate(cards):
    print(f'  {i+1}. {card.serial_number[:16]}... ({card.balance}pt, {card.status})')

# PDF生成テスト
try:
    response = generate_cards_pdf(cards)
    pdf_size = len(response.content)
    print(f'\n✓ PDF生成成功')
    print(f'  ファイルサイズ: {pdf_size} bytes')
    print(f'  Content-Type: {response["Content-Type"]}')
    
    # PDFをファイルに保存（デバッグ用）
    with open('/tmp/test_cards.pdf', 'wb') as f:
        f.write(response.content)
    print(f'  テストPDF保存: /tmp/test_cards.pdf')
except Exception as e:
    print(f'✗ エラー: {type(e).__name__}: {str(e)}')
    import traceback
    traceback.print_exc()
