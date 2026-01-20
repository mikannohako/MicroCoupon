from django.shortcuts import redirect
from functools import wraps


def admin_required(view_func):
    """管理者のみアクセス可能にするデコレータ"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account:login')
        if not request.user.is_admin():
            return redirect('transactions:register')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """店員のみアクセス可能にするデコレータ"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account:login')
        if request.user.is_admin():
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper
