from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.conf import settings
from .models import Card
import uuid
import qrcode
from io import BytesIO
import base64


@login_required
def dashboard(request):
    """ダッシュボード"""
    total_cards = Card.objects.count()
    unused_cards = Card.objects.filter(status='unused').count()
    active_cards = Card.objects.filter(status='active').count()
    used_cards = Card.objects.filter(status='used').count()
    total_balance = Card.objects.aggregate(Sum('balance'))['balance__sum'] or 0
    
    context = {
        'total_cards': total_cards,
        'unused_cards': unused_cards,
        'active_cards': active_cards,
        'used_cards': used_cards,
        'total_balance': total_balance,
    }
    return render(request, 'microcoupon/dashboard.html', context)


@login_required
def card_list(request):
    """カード一覧"""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    cards = Card.objects.all().order_by('-created_at')
    
    if status_filter:
        cards = cards.filter(status=status_filter)
    
    if search:
        cards = cards.filter(serial_number__icontains=search)
    
    context = {
        'cards': cards,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'microcoupon/card_list.html', context)


@login_required
def card_create(request):
    """カード発行"""
    if request.method == 'POST':
        balance = request.POST.get('balance', 1000)
        try:
            card = Card.objects.create(
                serial_number=str(uuid.uuid4()),
                balance=int(balance),
                status='unused'
            )
            messages.success(request, f'カード {card.serial_number} を発行しました')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
        return redirect('microcoupon:card_list')
    
    return render(request, 'microcoupon/card_create.html')


@login_required
def card_activate(request, card_id):
    """カード有効化"""
    card = get_object_or_404(Card, id=card_id)
    
    if card.status == 'unused':
        card.status = 'active'
        card.save()
        messages.success(request, f'カード {card.serial_number} を有効化しました')
    else:
        messages.error(request, 'このカードは有効化できません')
    
    return redirect('microcoupon:card_list')


@login_required
def card_detail(request, card_id):
    """カード詳細"""
    card = get_object_or_404(Card, id=card_id)
    
    # QRコード生成 - BASE_URLを使用
    qr_url = f"{settings.BASE_URL}/cards/{card.serial_number}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'microcoupon/card_detail.html', {
        'card': card,
        'qr_code': qr_code_base64,
        'qr_url': qr_url,
    })


def card_lookup(request):
    """カード残高照会ランディングページ（公開ページ - ログイン不要）"""
    return render(request, 'microcoupon/card_lookup.html')


def card_balance(request, serial_number):
    """カード残高表示（公開ページ - ログイン不要）"""
    card = get_object_or_404(Card, serial_number=serial_number)
    
    # 取引履歴を取得（完了した取引のみ）
    transactions = card.transactions.filter(status='completed').select_related('card').prefetch_related('items__product').order_by('-created_at')[:10]
    
    # QRコード生成
    qr_url = f"{settings.BASE_URL}/cards/{card.serial_number}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'microcoupon/card_balance.html', {
        'card': card,
        'transactions': transactions,
        'qr_code': qr_code_base64,
        'qr_url': qr_url,
    })
