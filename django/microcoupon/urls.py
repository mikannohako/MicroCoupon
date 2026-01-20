from django.urls import path
from . import views

app_name = 'microcoupon'

urlpatterns = [
    path('<str:serial_number>/', views.card_balance, name='card_balance'),
]
