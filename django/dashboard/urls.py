from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # ダッシュボード
    path('', views.dashboard, name='dashboard'),
    
    # 売上管理
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:transaction_id>/', views.sales_detail, name='sales_detail'),
    
    # カード管理
    path('cards/', views.card_list, name='card_list'),
    path('cards/create/', views.card_create, name='card_create'),
    path('cards/bulk-create/', views.card_bulk_create, name='card_bulk_create'),
    path('cards/bulk-delete/', views.card_bulk_delete, name='card_bulk_delete'),
    path('cards/activate/', views.card_activate, name='card_activate'),
    path('cards/<uuid:card_id>/', views.card_detail, name='card_detail'),
    path('cards/<uuid:card_id>/edit/', views.card_edit, name='card_edit'),
    path('cards/<uuid:card_id>/delete/', views.card_delete, name='card_delete'),
    
    # 商品管理
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    
    # ユーザー管理
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    
    # アクティビティログ
    path('logs/', views.activity_log_list, name='activity_log_list'),
    path('logs/<uuid:log_id>/', views.activity_log_detail, name='activity_log_detail'),
    
    # 取引ログ
    path('transactions/', views.transaction_log_list, name='transaction_log_list'),
    path('transactions/<int:transaction_id>/', views.transaction_log_detail, name='transaction_log_detail'),
]
