# admin_panel/urls.py
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
    path('reviews/<int:review_id>/detail/', views.review_detail, name='admin_review_detail'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='admin_delete_review'),
    path('reviews/<int:review_id>/approve/', views.approve_review, name='admin_approve_review'),
    path('reviews/<int:review_id>/reject/', views.reject_review, name='admin_reject_review'),

    # Admin Profile and Settings
    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('settings/', views.admin_settings, name='admin_settings'),

    # Support Pages
    path('help-center/', views.help_center, name='help_center'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('feedback/', views.feedback, name='feedback'),

    # Logout
    path('logout/', views.admin_logout, name='admin_logout'),
    path('categories/', views.admin_categories, name='admin_categories'),
    path('categories/add/', views.admin_category_add, name='admin_category_add'),
    path('categories/edit/<int:pk>/', views.admin_category_edit, name='admin_category_edit'),
    path('categories/delete/<int:pk>/', views.admin_category_delete, name='admin_category_delete'),

    path('subcategories/', views.admin_subcategories, name='admin_subcategories'),
    path('subcategories/add/', views.admin_subcategory_add, name='admin_subcategory_add'),
    path('subcategories/edit/<int:pk>/', views.admin_subcategory_edit, name='admin_subcategory_edit'),
    path('subcategories/delete/<int:pk>/', views.admin_subcategory_delete, name='admin_subcategory_delete'),
    # Existing URLs...

]