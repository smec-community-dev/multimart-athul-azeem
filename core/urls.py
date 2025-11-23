from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('users/', views.users_list, name='admin_users'),
    path('sellers/', views.sellers_list, name='admin_sellers'),
    path('products/', views.products_list, name='admin_products'),
    path('orders/', views.orders_list, name='admin_orders'),
    path('reviews/', views.reviews_list, name='admin_reviews'),
]