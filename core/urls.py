# admin_panel/urls.py
from django.urls import path

from . import password_reset
from . import views

urlpatterns = [
    # ==================== COMMON AUTH (ROOT LEVEL) ====================
    path("login/", views.normal_login_view, name="login"),  # ✅ Normal login
    path("logout/", views.custom_logout_view, name="logout"),
    path("registration/", views.registration_view, name="registration"),  # ✅ Normal registration

    path(
        "forgot-password/",
        password_reset.forgot_password_view,
        name="forgot_password",
    ),
    path(
        "verify-otp/",
        password_reset.verify_otp_view,
        name="verify_otp",
    ),
    path(
        "reset-password/",
        password_reset.reset_password_view,
        name="reset_password",
    ),

    # ==================== SOCIAL AUTH (Google Only) ====================
    path("choose-role/", views.choose_role, name="choose_role"),  # Only for Google users
    path("complete-registration/", views.complete_registration, name="complete_registration"),  # Only for Google users

    # ==================== ADMIN DASHBOARD ====================
    path("admin-dashboard/", views.dashboard, name="admin_dashboard"),

    # Users Management
    path('admin-dashboard/users/', views.users_list, name='admin_users'),
    path('admin-dashboard/users/add/', views.add_user, name='add_user'),
    path('admin-dashboard/users/<int:pk>/', views.user_detail, name='user_detail'),
    path('admin-dashboard/users/<int:user_id>/block/', views.block_user, name='block_user'),
    path('admin-dashboard/users/<int:user_id>/unblock/', views.unblock_user, name='unblock_user'),
    path('admin-dashboard/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin-dashboard/users/<int:user_id>/send-email/', views.send_user_email, name='send_user_email'),

    # Sellers Management
    path('admin-dashboard/sellers/', views.sellers_list, name='admin_sellers'),
    path('admin-dashboard/sellers/add/', views.add_seller, name='add_seller'),
    path('admin-dashboard/sellers/<int:pk>/', views.seller_detail, name='seller_detail'),
    path('admin-dashboard/sellers/<int:seller_id>/block/', views.block_seller_user, name='block_seller_user'),
    path('admin-dashboard/sellers/<int:seller_id>/unblock/', views.unblock_seller_user, name='unblock_seller_user'),
    path('admin-dashboard/sellers/<int:seller_id>/approve/', views.approve_seller, name='approve_seller'),
    path('admin-dashboard/sellers/<int:seller_id>/delete/', views.delete_seller, name='delete_seller'),
    path('admin-dashboard/sellers/<int:seller_id>/send-email/', views.send_seller_email, name='send_seller_email'),

    # Products Management
    path('admin-dashboard/products/', views.products_list, name='admin_products'),
    path('admin-dashboard/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('admin-dashboard/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),

    # Orders Management
    path('admin-dashboard/orders/', views.orders_list, name='admin_orders'),
    path('admin-dashboard/orders/<int:order_id>/detail/', views.order_detail, name='admin_order_detail'),
    path('admin-dashboard/orders/<int:order_id>/delete/', views.delete_order, name='admin_delete_order'),
    path('admin-dashboard/orders/export/', views.export_orders, name='admin_export_orders'),

    # Reviews Management
    path('admin-dashboard/reviews/', views.reviews_list, name='admin_reviews'),
    path('admin-dashboard/reviews/<int:review_id>/detail/', views.review_detail, name='admin_review_detail'),
    path('admin-dashboard/reviews/<int:review_id>/delete/', views.delete_review, name='admin_delete_review'),
    path('admin-dashboard/reviews/<int:review_id>/approve/', views.approve_review, name='admin_approve_review'),
    path('admin-dashboard/reviews/<int:review_id>/reject/', views.reject_review, name='admin_reject_review'),

    # Admin Profile and Settings
    path('admin-dashboard/profile/', views.admin_profile, name='admin_profile'),
    path('admin-dashboard/profile/edit/', views.edit_profile, name='edit_profile'),
    path('admin-dashboard/settings/', views.admin_settings, name='admin_settings'),

    # Support Pages
    path('admin-dashboard/help-center/', views.help_center, name='help_center'),
    path('admin-dashboard/contact-us/', views.contact_us, name='contact_us'),
    path('admin-dashboard/privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('admin-dashboard/terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('admin-dashboard/feedback/', views.feedback, name='feedback'),

    # Categories
    path('admin-dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('admin-dashboard/categories/add/', views.admin_category_add, name='admin_category_add'),
    path('admin-dashboard/categories/edit/<int:pk>/', views.admin_category_edit, name='admin_category_edit'),
    path('admin-dashboard/categories/delete/<int:pk>/', views.admin_category_delete, name='admin_category_delete'),
    path('admin-dashboard/category/<int:category_id>/products/', views.category_products, name='category_products'),

    # Subcategories
    path('admin-dashboard/subcategories/', views.admin_subcategories, name='admin_subcategories'),
    path('admin-dashboard/subcategory/add/', views.admin_subcategory_add, name='admin_subcategory_add'),
    path('admin-dashboard/subcategory/<int:subcategory_id>/edit/', views.admin_subcategory_edit,
         name='admin_subcategory_edit'),
    path('admin-dashboard/subcategory/<int:subcategory_id>/delete/', views.admin_subcategory_delete,
         name='admin_subcategory_delete'),
    path('admin-dashboard/subcategory/<int:subcategory_id>/products/', views.subcategory_products,
         name='subcategory_products'),
]