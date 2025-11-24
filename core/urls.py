from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='admin_dashboard'),

    # Users Management
    path('users/', views.users_list, name='admin_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/block/', views.block_user, name='block_user'),
    path('users/<int:user_id>/unblock/', views.unblock_user, name='unblock_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    # Sellers Management
    path('sellers/', views.sellers_list, name='admin_sellers'),
    path('sellers/add/', views.add_seller, name='add_seller'),
    path('sellers/<int:pk>/', views.seller_detail, name='seller_detail'),
    path('sellers/<int:seller_id>/block/', views.block_seller_user, name='block_seller_user'),
    path('sellers/<int:seller_id>/unblock/', views.unblock_seller_user, name='unblock_seller_user'),
    path('sellers/<int:seller_id>/approve/', views.approve_seller, name='approve_seller'),
    path('sellers/<int:seller_id>/delete/', views.delete_seller, name='delete_seller'),

    # Products Management
    path('products/', views.products_list, name='admin_products'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),

    # Orders Management
    path('orders/', views.orders_list, name='admin_orders'),
    path('orders/<int:order_id>/detail/', views.order_detail, name='admin_order_detail'),
    path('orders/<int:order_id>/delete/', views.delete_order, name='admin_delete_order'),
    path('orders/export/', views.export_orders, name='admin_export_orders'),

    # Reviews Management
    path('reviews/', views.reviews_list, name='admin_reviews'),
]