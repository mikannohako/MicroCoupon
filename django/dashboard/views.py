from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.conf import settings
from microcoupon.models import Card
from products.models import Product
from account.models import Room
from account.decorators import admin_required
from transactions.models import Transaction, TransactionItem
import uuid
import qrcode
from io import BytesIO
import base64


@admin_required
def dashboard(request):
    total_cards = Card.objects.count()
    unused_cards = Card.objects.filter(status='unused').count()
    active_cards = Card.objects.filter(status='active').count()
    used_cards = Card.objects.filter(status='used').count()
    total_balance = Card.objects.filter(status='active').aggregate(Sum('balance'))['balance__sum'] or 0
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    context = {
        'total_cards': total_cards,
        'unused_cards': unused_cards,
        'active_cards': active_cards,
        'used_cards': used_cards,
        'total_balance': total_balance,
        'total_products': total_products,
        'active_products': active_products,
    }
    return render(request, 'dashboard/dashboard.html', context)


@admin_required
def card_list(request):
    status_filter = request.GET.get('status', '')
    cards = Card.objects.all()
    if status_filter:
        cards = cards.filter(status=status_filter)
    cards = cards.order_by('-created_at')
    context = {'cards': cards, 'status_filter': status_filter}
    return render(request, 'dashboard/card_list.html', context)


@admin_required
def card_detail(request, card_id):
    card = get_object_or_404(Card, id=card_id)
    url = f"{settings.BASE_URL}/cards/{card.serial_number}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    context = {'card': card, 'qr_image': f'data:image/png;base64,{img_base64}', 'qr_url': url}
    return render(request, 'dashboard/card_detail.html', context)


@admin_required
def card_create(request):
    if request.method == 'POST':
        balance = request.POST.get('balance', 0)
        try:
            card = Card.objects.create(balance=int(balance))
            messages.success(request, 'カードを作成しました')
            return redirect('dashboard:card_detail', card_id=card.id)
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    return render(request, 'dashboard/card_create.html')


@admin_required
def card_edit(request, card_id):
    card = get_object_or_404(Card, id=card_id)
    if request.method == 'POST':
        balance = request.POST.get('balance')
        status = request.POST.get('status')
        is_locked = request.POST.get('is_locked') == 'on'
        try:
            new_balance = int(balance)
            # 残高の手動追加を禁止（減少のみ許可）
            if new_balance > card.balance:
                messages.error(request, '残高を増やすことはできません。減少のみ可能です。')
                return redirect('dashboard:card_edit', card_id=card.id)
            
            card.balance = new_balance
            card.status = status
            card.is_locked = is_locked
            
            # 残高が0になったら使用済みにする
            if card.balance == 0:
                card.status = 'used'
            
            card.save()
            messages.success(request, 'カード情報を更新しました')
            return redirect('dashboard:card_detail', card_id=card.id)
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    url = f"{settings.BASE_URL}/cards/{card.serial_number}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return render(request, 'dashboard/card_edit.html', {'card': card, 'qr_image': f'data:image/png;base64,{img_base64}', 'qr_url': url})


@admin_required
def product_list(request):
    room_filter = request.GET.get('room', '')
    products = Product.objects.select_related('room').filter(is_active=True)
    rooms = Room.objects.filter(is_active=True)
    if room_filter:
        products = products.filter(room_id=room_filter)
    context = {'products': products, 'categories': rooms, 'category_filter': room_filter}
    return render(request, 'dashboard/product_list.html', context)


@admin_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'dashboard/product_detail.html', {'product': product})


@admin_required
def product_create(request):
    if request.method == 'POST':
        room_id = request.POST.get('category')
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        try:
            room = get_object_or_404(Room, id=room_id)
            product = Product.objects.create(room=room, name=name, price=int(price), description=description, display_order=int(display_order), is_active=True)
            messages.success(request, '商品を作成しました')
            return redirect('dashboard:product_list')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    categories = Room.objects.filter(is_active=True)
    return render(request, 'dashboard/product_create.html', {'categories': categories})


@admin_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        room_id = request.POST.get('category')
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        try:
            room = get_object_or_404(Room, id=room_id)
            product.room = room
            product.name = name
            product.price = int(price)
            product.description = description
            product.display_order = int(display_order)
            product.is_active = is_active
            product.save()
            messages.success(request, '商品を更新しました')
            return redirect('dashboard:product_list')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    categories = Room.objects.filter(is_active=True)
    return render(request, 'dashboard/product_edit.html', {'product': product, 'categories': categories})


@admin_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, '商品を削除しました')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/product_delete_confirm.html', {'product': product})


@admin_required
def card_activate(request):
    result = None
    if request.method == 'POST':
        serial_number = request.POST.get('serial_number', '').strip()
        if serial_number:
            try:
                card = Card.objects.get(serial_number=serial_number)
                if card.status == 'unused':
                    card.status = 'active'
                    card.save()
                    result = {'success': True, 'message': 'カードを有効化しました', 'card': card}
                elif card.status == 'active':
                    result = {'success': False, 'message': 'このカードは既に有効化されています', 'card': card}
                elif card.status == 'used':
                    result = {'success': False, 'message': 'このカードは使用済みです', 'card': card}
            except Card.DoesNotExist:
                result = {'success': False, 'message': 'カードが見つかりません'}
        else:
            result = {'success': False, 'message': 'シリアル番号を入力してください'}
    return render(request, 'dashboard/card_activate.html', {'result': result})


@admin_required
def sales_list(request):
    """売上一覧（教室ごと）"""
    from django.db.models import Count, Q
    
    # 全ての教室を取得
    rooms = Room.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # 各教室の売上を集計
    room_stats = []
    total_sales = 0
    total_count = 0
    
    for room in rooms:
        # この教室の商品が含まれる取引を取得
        room_transactions = Transaction.objects.filter(
            status='completed',
            items__product__room=room
        ).distinct()
        
        # 売上額を計算（この教室の商品分のみ）
        room_total = 0
        for transaction in room_transactions:
            for item in transaction.items.filter(product__room=room):
                room_total += item.product_price * item.quantity
        
        room_stats.append({
            'id': room.id,
            'name': room.name,
            'total_sales': room_total,
            'transaction_count': room_transactions.count()
        })
        
        total_sales += room_total
        total_count += room_transactions.count()
    
    context = {
        'rooms': room_stats,
        'total_sales': total_sales,
        'total_count': total_count,
    }
    return render(request, 'dashboard/sales_list.html', context)


@admin_required
def sales_detail(request, transaction_id):
    """教室ごとの売上詳細"""
    # transaction_idをroom_idとして扱う
    room = get_object_or_404(Room, id=transaction_id)
    
    # この教室の商品が含まれる取引を取得
    transactions = Transaction.objects.filter(
        status='completed',
        items__product__room=room
    ).distinct().select_related('card').prefetch_related('items__product').order_by('-created_at')
    
    # 日付フィルター
    date_filter = request.GET.get('date', '')
    if date_filter:
        transactions = transactions.filter(created_at__date=date_filter)
    
    # 統計（この教室の商品分のみ）
    total_sales = 0
    for transaction in transactions:
        for item in transaction.items.filter(product__room=room):
            total_sales += item.product_price * item.quantity
    
    total_count = transactions.count()
    
    context = {
        'room': room,
        'transactions': transactions,
        'total_sales': total_sales,
        'total_count': total_count,
        'date_filter': date_filter,
    }
    return render(request, 'dashboard/sales_detail.html', context)

