from django.urls import path
from . import views

app_name = 'microcoupon'

urlpatterns = [
    path('', views.card_lookup, name='card_lookup'),
    path('<str:serial_number>/', views.card_balance, name='card_balance'),
]
