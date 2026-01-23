from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def page_not_found(request, exception=None):
    """404 Not Found エラーハンドラ"""
    return render(request, '404.html', status=404)


@require_http_methods(["GET"])
def server_error(request, exception=None):
    """500 Internal Server Error エラーハンドラ"""
    return render(request, '500.html', status=500)
