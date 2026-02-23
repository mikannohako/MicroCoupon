from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.conf import settings
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from microcoupon.models import Card, ActivityLog, TemporaryCardCode
from microcoupon.utils import log_activity
from products.models import Product
from account.models import Room, User
from account.decorators import admin_required
from transactions.models import Transaction, TransactionItem
import uuid
import qrcode
from io import BytesIO
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import mm, inch


@admin_required
def dashboard(request):
    # 削除済み以外のカードを対象
    active_cards_qs = Card.objects.exclude(status='deleted')
    
    total_cards = active_cards_qs.count()
    unused_cards = active_cards_qs.filter(status='unused').count()
    active_cards = active_cards_qs.filter(status='active').count()
    used_cards = active_cards_qs.filter(status='used').count()
    total_balance = active_cards_qs.filter(status='active').aggregate(Sum('balance'))['balance__sum'] or 0
    total_sales = Transaction.objects.filter(status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    context = {
        'total_cards': total_cards,
        'unused_cards': unused_cards,
        'active_cards': active_cards,
        'used_cards': used_cards,
        'total_balance': total_balance,
        'used_balance': total_sales,
        'total_products': total_products,
        'active_products': active_products,
    }
    return render(request, 'dashboard/dashboard.html', context)


@admin_required
def card_list(request):
    status_filter = request.GET.get('status', '')
    # 削除済みのカードは非表示
    cards = Card.objects.exclude(status='deleted')
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
            print(f"DEBUG: card_create - Attempting to log activity for card {card.id}")
            log_activity(request.user, 'card_create', 
                        f'カード {card.serial_number} を作成（残高: {balance}pt）',
                        'Card', card.id, request, {'balance': int(balance)})
            print(f"DEBUG: card_create - Activity logged successfully")
            messages.success(request, 'カードを作成しました')
            return redirect('dashboard:card_detail', card_id=card.id)
        except ValueError:
            messages.error(request, 'エラー: 残高に無効な値が入力されています')
        except Exception as e:
            print(f"DEBUG: card_create - Exception: {e}")
            messages.error(request, f'カードの作成に失敗しました: {str(e)}')
    return render(request, 'dashboard/card_create.html')


@admin_required
def card_bulk_create(request):
    if request.method == 'POST':
        count = request.POST.get('count')
        balance = request.POST.get('balance', 0)
        export_pdf = request.POST.get('export_pdf') == 'on'
        try:
            count_int = max(0, int(count)) if count is not None else 0
            balance_int = int(balance)
            if count_int <= 0:
                messages.error(request, '作成する枚数を1以上で指定してください。')
                return redirect('dashboard:card_list')
            import uuid
            cards = [Card(balance=balance_int, serial_number=str(uuid.uuid4())) for _ in range(count_int)]
            created_cards = Card.objects.bulk_create(cards)
            log_activity(request.user, 'card_create', 
                        f'{count_int}枚のカードを一括作成（残高: {balance_int}pt）',
                        'Card', '', request, {'count': count_int, 'balance': balance_int})
            messages.success(request, f'{count_int}枚のカードを一括作成しました（初期残高: {balance_int}pt）。')
            
            # PDF出力が指定された場合
            if export_pdf and created_cards:
                return generate_cards_pdf(created_cards)
        except ValueError:
            messages.error(request, '枚数と残高は数値で入力してください。')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    return redirect('dashboard:card_list')


@admin_required
def card_bulk_delete(request):
    if request.method == 'POST':
        delete_status = request.POST.get('delete_status', 'unused')
        delete_count = request.POST.get('delete_count')
        try:
            qs = Card.objects.filter(status=delete_status)
            if delete_count:
                limit = max(0, int(delete_count))
                qs = qs.order_by('created_at')[:limit]
            deleted = qs.count()
            if deleted == 0:
                messages.info(request, '削除対象のカードがありません。')
                return redirect('dashboard:card_list')
            
            # 論理削除（ステータスを'deleted'に変更）
            for card in qs:
                card.status = 'deleted'
                card.save()
                log_activity(request.user, 'card_delete', 
                           f'カード {card.serial_number} を削除済みに変更',
                           'Card', card.id, request,
                           {'old_status': delete_status, 'balance': card.balance})
            
            messages.success(request, f'{deleted}枚のカードを削除済みに変更しました（旧ステータス: {delete_status}）。')
        except ValueError:
            messages.error(request, '削除枚数は数値で入力してください。')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    return redirect('dashboard:card_list')


@admin_required
def card_edit(request, card_id):
    card = get_object_or_404(Card, id=card_id)
    if request.method == 'POST':
        balance = request.POST.get('balance')
        status = request.POST.get('status')
        is_locked = request.POST.get('is_locked') == 'on'
        try:
            new_balance = int(balance)
            old_balance = card.balance
            
            card.balance = new_balance
            card.status = status
            card.is_locked = is_locked
            
            # 残高が0になったら使用済みにする
            if card.balance == 0:
                card.status = 'used'
            
            card.save()
            log_activity(request.user, 'card_edit', 
                        f'カード {card.serial_number} を編集（残高: {old_balance}→{new_balance}pt, ステータス: {status}）',
                        'Card', card.id, request,
                        {'old_balance': old_balance, 'new_balance': new_balance, 'status': status})
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
def card_delete(request, card_id):
    """カード削除（論理削除）"""
    card = get_object_or_404(Card, id=card_id)
    
    if request.method == 'POST':
        serial_number = card.serial_number
        old_status = card.status
        
        # ステータスを削除済みに変更
        card.status = 'deleted'
        card.save()
        
        log_activity(request.user, 'card_delete',
                    f'カード {serial_number} を削除済みに変更（旧ステータス: {old_status}）',
                    'Card', card.id, request,
                    {'old_status': old_status, 'balance': card.balance})
        
        messages.success(request, 'カードを削除しました')
        return redirect('dashboard:card_list')
    
    return render(request, 'dashboard/card_delete_confirm.html', {'card': card})


@admin_required
def product_list(request):
    room_filter = request.GET.get('room', '')
    products = Product.objects.select_related('room').filter(is_active=True)
    rooms = Room.objects.filter(is_active=True)
    if room_filter:
        products = products.filter(room_id=room_filter)
    context = {
        'products': products,
        'categories': rooms,
        'category_filter': room_filter,
    }
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
            
            # ログ記録
            log_activity(
                user=request.user,
                action='product_create',
                description=f'商品作成: {product.name} ({product.price}pt)',
                target_model='Product',
                target_id=product.id,
                request=request
            )
            
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
            
            # ログ記録
            log_activity(
                user=request.user,
                action='product_edit',
                description=f'商品編集: {product.name} ({product.price}pt)',
                target_model='Product',
                target_id=product.id,
                request=request
            )
            
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
        product_id_str = str(product.id)
        product.delete()
        
        # ログ記録
        log_activity(
            user=request.user,
            action='product_delete',
            description=f'商品削除: {product_name}',
            target_model='Product',
            target_id=product_id_str,
            request=request
        )
        
        messages.success(request, '商品を削除しました')
        return redirect('dashboard:product_list')
    return render(request, 'dashboard/product_delete_confirm.html', {'product': product})


@admin_required
def card_activate(request):
    result = None
    if request.method == 'POST':
        card_input = request.POST.get('card_input', '').strip()
        if card_input:
            try:
                used_temporary_code = False
                temp_code_to_consume = None
                with db_transaction.atomic():
                    try:
                        card = Card.objects.select_for_update().get(serial_number=card_input)
                    except Card.DoesNotExist:
                        temp_code_to_consume = TemporaryCardCode.objects.select_for_update().filter(
                            code=card_input,
                            expires_at__gt=timezone.now(),
                        ).first()
                        if not temp_code_to_consume:
                            raise Card.DoesNotExist
                        card = Card.objects.select_for_update().get(id=temp_code_to_consume.card_id)
                        used_temporary_code = True

                if card.status == 'unused':
                    card.status = 'active'
                    card.activated_at = timezone.now()
                    card.save()
                    if temp_code_to_consume:
                        temp_code_to_consume.delete()
                    log_activity(request.user, 'card_activate', 
                               f'カード {card.serial_number} を有効化',
                               'Card', card.id, request,
                               {
                                   'balance': card.balance,
                                   'used_temporary_code': used_temporary_code,
                               })
                    result = {'success': True, 'message': 'カードを有効化しました', 'card': card}
                elif card.status == 'active':
                    result = {'success': False, 'message': 'このカードは既に有効化されています', 'card': card}
                elif card.status == 'used':
                    result = {'success': False, 'message': 'このカードは使用済みです', 'card': card}
                elif card.status == 'deleted':
                    result = {'success': False, 'message': 'このカードは削除済みです', 'card': card}
            except Card.DoesNotExist:
                result = {'success': False, 'message': 'カードが見つかりません（4桁コードの有効期限切れの可能性があります）'}
        else:
            result = {'success': False, 'message': '4桁コードまたはシリアル番号を入力してください'}
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


def generate_cards_pdf(cards):
    """
    複数のカード（QRコード+シリアルナンバー）を名刺サイズで印字したPDFを生成
    A4横向きに3x5=15枚のカード配置
    カードサイズ: 54mm x 91mm (名刺サイズ)
    """
    import tempfile
    import os
    
    # ページサイズ
    page_width, page_height = landscape(letter)  # 11in x 8.5in
    
    # 名刺サイズ: 幅91mm × 高さ54mm
    card_width = 91 * mm
    card_height = 54 * mm
    
    # レイアウト計算（A4横向き）
    margin_top = 0.4 * inch
    margin_left = 0.4 * inch
    
    # PDFバッファ作成
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # ページ座標系: 左下が原点
    cards_per_page = 15  # 3列 x 5行
    
    for card_index, card in enumerate(cards):
        # ページ変更判定
        if card_index > 0 and card_index % cards_per_page == 0:
            c.showPage()
        
        # カード内でのインデックス
        page_local_index = card_index % cards_per_page
        col = page_local_index % 3       # 0, 1, 2 (左から右)
        row = page_local_index // 3      # 0, 1, 2, 3, 4 (上から下)
        
        # カード左下の座標を計算
        x = margin_left + col * card_width
        y = page_height - margin_top - (row + 1) * card_height
        
        # カード背景（白）とボーダー
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.setFillColorRGB(1, 1, 1)  # 白
        c.rect(x, y, card_width, card_height, fill=1, stroke=1)
        
        # QRコード生成と描画
        try:
            qr_url = f"{settings.BASE_URL}/cards/{card.serial_number}/"
            qr_PIL = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr_PIL.add_data(qr_url)
            qr_PIL.make(fit=True)
            qr_img = qr_PIL.make_image(fill_color="black", back_color="white")
            
            # テンポラリファイルに保存（ReportLabで読み込むため）
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                qr_img.save(tmp.name, format='PNG')
                qr_file = tmp.name
            
            # QRコードをカード内に描画（左側、中央縦配置）
            qr_size = 28 * mm
            qr_x = x + 2 * mm
            qr_y = y + (card_height - qr_size) / 2
            c.drawImage(qr_file, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
            
            # テンポラリファイル削除
            try:
                os.unlink(qr_file)
            except:
                pass
        except Exception as e:
            # QRコード生成エラー時はスキップ（テキストのみ表示）
            pass
        
        # テキスト描画のため色を黒に設定
        c.setFillColorRGB(0, 0, 0)
        
        # シリアルナンバーを描画（右側）
        text_x = x + 38 * mm
        text_y = y + card_height - 6 * mm
        
        # ラベル
        c.setFont("Helvetica-Bold", 8)
        c.drawString(text_x, text_y, "Serial:")
        
        # シリアルナンバー（複数行）
        c.setFont("Courier-Bold", 6)
        serial = card.serial_number
        # シリアルナンバーを折り返す（12文字ごと）
        lines = [serial[i:i+12] for i in range(0, len(serial), 12)]
        line_height = 4 * mm
        for i, line in enumerate(lines):
            line_y = text_y - (i + 1) * line_height
            c.drawString(text_x, line_y, line)
        
        # 残高情報を下に表示（金額表記）
        balance_y = y + 3 * mm
        c.setFont("Helvetica-Bold", 9)
        balance_text = f"{card.balance}pt"
        c.drawString(text_x, balance_y, balance_text)
        
        # ステータスラベルを左下に表示
        status_y = y + 2 * mm
        c.setFont("Helvetica", 5)
        c.drawString(x + 2 * mm, status_y, card.get_status_display())
    
    c.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="cards.pdf"'
    return response


# ユーザー管理ビュー

@admin_required
def user_list(request):
    """ユーザー一覧"""
    users = User.objects.all().order_by('-date_joined')
    context = {'users': users}
    return render(request, 'dashboard/user_list.html', context)


@admin_required
def user_create(request):
    """ユーザー作成"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        user_type = request.POST.get('user_type', 'staff')
        room_id = request.POST.get('room')
        
        try:
            # バリデーション
            if not username:
                messages.error(request, 'ユーザー名を入力してください')
                return render(request, 'dashboard/user_create.html', {'rooms': Room.objects.filter(is_active=True)})
            
            if not password:
                messages.error(request, 'パスワードを入力してください')
                return render(request, 'dashboard/user_create.html', {'rooms': Room.objects.filter(is_active=True)})
            
            if password != password_confirm:
                messages.error(request, 'パスワードと確認パスワードが一致しません')
                return render(request, 'dashboard/user_create.html', {'rooms': Room.objects.filter(is_active=True)})
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'このユーザー名は既に使用されています')
                return render(request, 'dashboard/user_create.html', {'rooms': Room.objects.filter(is_active=True)})
            
            # ユーザー作成
            room = None
            if room_id:
                room = get_object_or_404(Room, id=room_id)
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                user_type=user_type,
                room=room
            )
            
            messages.success(request, f'ユーザー「{username}」を作成しました')
            return redirect('dashboard:user_list')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    
    rooms = Room.objects.filter(is_active=True)
    return render(request, 'dashboard/user_create.html', {'rooms': rooms})


@admin_required
def user_edit(request, user_id):
    """ユーザー編集"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        user_type = request.POST.get('user_type', 'staff')
        room_id = request.POST.get('room')
        
        try:
            # パスワード確認（変更時のみ）
            if password:
                if password != password_confirm:
                    messages.error(request, 'パスワードと確認パスワードが一致しません')
                    rooms = Room.objects.filter(is_active=True)
                    return render(request, 'dashboard/user_edit.html', {'user': user, 'rooms': rooms})
                user.set_password(password)
            
            # その他の情報を更新
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.user_type = user_type
            
            if room_id:
                user.room = get_object_or_404(Room, id=room_id)
            else:
                user.room = None
            
            user.save()
            messages.success(request, 'ユーザー情報を更新しました')
            return redirect('dashboard:user_list')
        except Exception as e:
            messages.error(request, f'エラー: {str(e)}')
    
    rooms = Room.objects.filter(is_active=True)
    return render(request, 'dashboard/user_edit.html', {'user': user, 'rooms': rooms})


@admin_required
def user_delete(request, user_id):
    """ユーザー削除"""
    user = get_object_or_404(User, id=user_id)
    
    # 自分自身は削除できない
    if user.id == request.user.id:
        messages.error(request, '自分自身は削除できません')
        return redirect('dashboard:user_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        log_activity(request.user, 'user_delete', f'ユーザー「{username}」を削除', 
                    'User', user.id, request)
        messages.success(request, f'ユーザー「{username}」を削除しました')
        return redirect('dashboard:user_list')
    
    return render(request, 'dashboard/user_delete_confirm.html', {'user': user})


@admin_required
def activity_log_list(request):
    """アクティビティログ一覧"""
    logs = ActivityLog.objects.select_related('user').all()
    
    # フィルター
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if date_from:
        logs = logs.filter(created_at__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__lte=date_to + ' 23:59:59')
    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query) |
            Q(target_id__icontains=search_query)
        )
    
    # ページネーション
    paginator = Paginator(logs, 50)  # 50件ごと
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    # フィルター用データ
    all_users = User.objects.filter(is_active=True).order_by('username')
    action_choices = ActivityLog.ACTION_CHOICES
    
    context = {
        'logs': logs_page,
        'all_users': all_users,
        'action_choices': action_choices,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    return render(request, 'dashboard/activity_log_list.html', context)


@admin_required
def activity_log_detail(request, log_id):
    """アクティビティログ詳細"""
    log = get_object_or_404(ActivityLog.objects.select_related('user'), id=log_id)
    context = {
        'log': log,
    }
    return render(request, 'dashboard/activity_log_detail.html', context)


@admin_required
def transaction_log_list(request):
    """取引ログ一覧"""
    transactions = Transaction.objects.select_related('card').prefetch_related('items__product').all()
    
    # フィルター
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    if date_from:
        transactions = transactions.filter(created_at__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__lte=date_to + ' 23:59:59')
    if search_query:
        transactions = transactions.filter(
            Q(card__serial_number__icontains=search_query) |
            Q(created_by__icontains=search_query)
        )
    
    # ページネーション
    paginator = Paginator(transactions, 50)  # 50件ごと
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)
    
    # フィルター用データ
    status_choices = [
        ('completed', '完了'),
        ('failed', '失敗'),
        ('cancelled', 'キャンセル'),
    ]
    
    context = {
        'transactions': transactions_page,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    return render(request, 'dashboard/transaction_log_list.html', context)


@admin_required
def transaction_log_detail(request, transaction_id):
    """取引ログ詳細"""
    transaction = get_object_or_404(Transaction.objects.select_related('card').prefetch_related('items__product'), id=transaction_id)
    context = {
        'transaction': transaction,
    }
    return render(request, 'dashboard/transaction_log_detail.html', context)
