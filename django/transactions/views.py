from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction as db_transaction
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib import messages
from .models import Transaction, TransactionItem
from microcoupon.models import Card
from microcoupon.utils import log_activity
from products.models import Product
from account.models import Room
import json
import threading


def unlock_card_after_delay(card_id, delay=5):
    """指定秒数後にカードのロックを解除"""
    def unlock():
        import time
        time.sleep(delay)
        try:
            card = Card.objects.get(id=card_id)
            card.is_locked = False
            card.save()
        except Card.DoesNotExist:
            pass
    
    thread = threading.Thread(target=unlock)
    thread.daemon = True
    thread.start()
import threading


@login_required
def register_page(request):
    """レジページ（ログイン必須）"""
    # ユーザーの所属教室に応じて商品をフィルタリング
    if request.user.is_admin():
        # 管理者は全ての教室の商品を表示
        rooms = Room.objects.filter(is_active=True).prefetch_related('products')
    else:
        # 店員は自分の教室の商品のみ表示
        if request.user.room:
            rooms = Room.objects.filter(id=request.user.room.id, is_active=True).prefetch_related('products')
        else:
            rooms = Room.objects.none()
    
    # 今日の売上（教室別）
    today = timezone.now().date()
    today_sales_query = Transaction.objects.filter(
        created_at__date=today,
        status='completed'
    )
    
    # 店員は自分の教室の売上のみ
    if not request.user.is_admin() and request.user.room:
        today_sales_query = today_sales_query.filter(
            items__product__room=request.user.room
        ).distinct()
    
    today_sales = today_sales_query.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # 現在のユーザーの教室
    current_room = request.user.room if not request.user.is_admin() else None
    
    context = {
        'categories': rooms,  # テンプレート互換性のため
        'today_sales': today_sales['total'] or 0,
        'today_count': today_sales['count'] or 0,
        'current_room': current_room,
        'is_admin': request.user.is_admin(),
    }
    return render(request, 'transactions/register.html', context)


@require_POST
@login_required
def process_payment(request):
    """決済処理（二重決済防止機能付き）"""
    card = None
    try:
        data = json.loads(request.body)
        serial_number = data.get('serial_number')
        items = data.get('items', [])
        
        if not serial_number or not items:
            return JsonResponse({
                'success': False,
                'error': 'カード番号または商品が指定されていません'
            })
        
        # 合計金額計算
        total_amount = sum(item['price'] * item.get('quantity', 1) for item in items)
        
        # トランザクション開始
        with db_transaction.atomic():
            # カード取得（行ロック付き）
            card = Card.objects.select_for_update().get(serial_number=serial_number)
            
            # 二重決済防止チェック
            if card.is_locked:
                raise Exception('処理中です。しばらくお待ちください')
            
            # カードのステータスチェック
            if card.status != 'active':
                raise Exception('カードが有効ではありません')
            
            # 残高チェック
            if card.balance < total_amount:
                raise Exception(f'残高不足です（残高: {card.balance}pt, 必要: {total_amount}pt）')
            
            # カードをロック（処理中フラグ）
            card.is_locked = True
            card.save()
            
            try:
                # 残高減算
                card.balance -= total_amount
                if card.balance == 0:
                    card.status = 'used'
                    card.used_at = timezone.now()
                card.save()
                
                # 決済ログ作成
                transaction = Transaction.objects.create(
                    card=card,
                    total_amount=total_amount,
                    status='completed',
                    created_by=request.user.username
                )
                
                # 決済明細作成
                for item in items:
                    product = None
                    if item.get('product_id'):
                        product = Product.objects.filter(id=item['product_id']).first()
                    
                    TransactionItem.objects.create(
                        transaction=transaction,
                        product=product,
                        product_name=item['name'],
                        product_price=item['price'],
                        quantity=item.get('quantity', 1)
                    )
                
                # 決済完了後、5秒後にロックを解除
                unlock_card_after_delay(card.id, delay=5)
                
                # ログ記録
                log_activity(
                    user=request.user,
                    action='transaction_complete',
                    description=f'決済完了: {total_amount}pt (カード: {card.serial_number})',
                    target_model='Transaction',
                    target_id=transaction.id,
                    request=request
                )
                
                return JsonResponse({
                    'success': True,
                    'transaction_id': transaction.id,
                    'remaining_balance': card.balance,
                    'total_amount': total_amount
                })
                
            except Exception as e:
                # エラー時もロックを解除
                card.is_locked = False
                card.save()
                raise
        
    except Card.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'カードが見つかりません'
        })
    except Exception as e:
        # エラーログ記録
        if card:
            try:
                # ロックが残っている場合は解除
                if card.is_locked:
                    card.is_locked = False
                    card.save()
                
                Transaction.objects.create(
                    card=card,
                    total_amount=total_amount if 'total_amount' in locals() else 0,
                    status='failed',
                    error_message=str(e),
                    created_by=request.user.username
                )
            except:
                pass  # エラーログ記録失敗は無視
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@login_required
def transaction_history(request):
    """決済履歴（レジ用）"""
    # ユーザーの教室に応じてフィルタリング
    transactions = Transaction.objects.filter(status='completed').select_related('card').prefetch_related('items__product').order_by('-created_at')
    
    # 店員は自分の教室の売上のみ
    if not request.user.is_admin() and request.user.room:
        transactions = transactions.filter(
            items__product__room=request.user.room
        ).distinct()
    
    # 日付フィルター
    date_filter = request.GET.get('date', '')
    if date_filter:
        transactions = transactions.filter(created_at__date=date_filter)
    
    # 統計
    total_sales = transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_count = transactions.count()
    
    context = {
        'transactions': transactions,
        'total_sales': total_sales,
        'total_count': total_count,
        'date_filter': date_filter,
        'current_room': request.user.room if not request.user.is_admin() else None,
        'is_admin': request.user.is_admin(),
    }
    return render(request, 'transactions/history.html', context)
    return render(request, 'transactions/history.html', context)

@login_required
def register_product_create(request):
    """レジページから商品を追加（店員用）"""
    # 店員は自分の教室の商品のみ追加可能
    if request.user.is_admin():
        return redirect('transactions:register')
    
    if not request.user.room:
        messages.error(request, '教室が割り当てられていません')
        return redirect('transactions:register')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        
        try:
            product = Product.objects.create(
                room=request.user.room,
                name=name,
                price=int(price),
                description=description,
                display_order=int(display_order),
                is_active=True
            )
            
            # ログ記録
            log_activity(
                user=request.user,
                action='product_create',
                description=f'レジから商品作成: {product.name} ({product.price}pt)',
                target_model='Product',
                target_id=product.id,
                request=request
            )
            
            messages.success(request, f'商品「{product.name}」を追加しました')
            return redirect('transactions:register')
        except ValueError:
            messages.error(request, 'エラー: 価格または表示順に無効な値が入力されています')
        except Exception as e:
            messages.error(request, f'商品の追加に失敗しました: {str(e)}')
    
    return redirect('transactions:register')


@login_required
def register_product_edit(request, product_id):
    """レジページから商品を編集（店員用）"""
    product = get_object_or_404(Product, id=product_id)
    
    # 店員は自分の教室の商品のみ編集可能
    if not request.user.is_admin() and request.user.room != product.room:
        messages.error(request, '他の教室の商品は編集できません')
        return redirect('transactions:register')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            old_name = product.name
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
                description=f'レジから商品編集: {product.name} ({product.price}pt)',
                target_model='Product',
                target_id=product.id,
                request=request
            )
            
            messages.success(request, f'商品「{product.name}」を更新しました')
            return redirect('transactions:register')
        except ValueError:
            messages.error(request, 'エラー: 価格または表示順に無効な値が入力されています')
        except Exception as e:
            messages.error(request, f'商品の更新に失敗しました: {str(e)}')
    
    return redirect('transactions:register')


@require_POST
@login_required
def register_product_delete(request, product_id):
    """レジページから商品を削除（店員用）"""
    product = get_object_or_404(Product, id=product_id)
    
    # 店員は自分の教室の商品のみ削除可能
    if not request.user.is_admin() and request.user.room != product.room:
        messages.error(request, '他の教室の商品は削除できません')
        return redirect('transactions:register')
    
    product_name = product.name
    product_id_str = str(product.id)
    product.delete()
    
    # ログ記録
    log_activity(
        user=request.user,
        action='product_delete',
        description=f'レジから商品削除: {product_name}',
        target_model='Product',
        target_id=product_id_str,
        request=request
    )
    
    messages.success(request, f'商品「{product_name}」を削除しました')
    return redirect('transactions:register')

