from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from microcoupon.utils import log_activity


def login_view(request):
    """ログイン画面"""
    if request.user.is_authenticated:
        # すでにログインしている場合はリダイレクト
        if request.user.is_admin():
            return redirect('dashboard:dashboard')
        else:
            return redirect('transactions:register')
    
    # GETリクエスト時（ログインページ表示時）に前のセッションのメッセージをクリア
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for _ in storage:
            pass  # メッセージを消費してクリア
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            
            # ログイン記録
            log_activity(
                user=user,
                action='user_login',
                description=f'{user.username} がログインしました',
                request=request
            )
            
            # ユーザータイプによって遷移先を変更
            if user.is_admin():
                return redirect('dashboard:dashboard')
            else:
                return redirect('transactions:register')
        else:
            messages.error(request, 'ユーザー名またはパスワードが正しくありません')
    
    return render(request, 'account/login.html')


@login_required
def logout_view(request):
    """ログアウト"""
    # ログアウト前にユーザー情報を保存
    user = request.user
    username = user.username
    
    # メッセージをクリアしてからログアウト
    storage = messages.get_messages(request)
    storage.used = True
    
    # ログアウト記録
    log_activity(
        user=user,
        action='user_logout',
        description=f'{username} がログアウトしました',
        request=request
    )
    
    # ログアウト処理（セッション全体をクリア）
    auth_logout(request)
    return redirect('account:login')
