from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def login_view(request):
    """ログイン画面"""
    if request.user.is_authenticated:
        # すでにログインしている場合はリダイレクト
        if request.user.is_admin():
            return redirect('dashboard:dashboard')
        else:
            return redirect('transactions:register')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            
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
    auth_logout(request)
    messages.success(request, 'ログアウトしました')
    return redirect('account:login')
