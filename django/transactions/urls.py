from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('register/', views.register_page, name='register'),
    path('process/', views.process_payment, name='process_payment'),
    path('history/', views.transaction_history, name='history'),
    path('register/product/create/', views.register_product_create, name='register_product_create'),
    path('register/product/<int:product_id>/edit/', views.register_product_edit, name='register_product_edit'),
    path('register/product/<int:product_id>/delete/', views.register_product_delete, name='register_product_delete'),
]
