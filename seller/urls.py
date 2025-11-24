from django.urls import path
from seller import views

urlpatterns = [
    path("view/", views.view_product, name='view_products'),
    path("", views.home, name='home'),
    path("registration/", views.seller_registration, name='registration'),
    path("profile/", views.seller_profile_view, name='profile'),
    path("login/", views.login_seller, name='login'),
    path("logout/", views.logout_seller, name='logout'),


    path("seller_dashboard/", views.view_product, name="seller_dashboard"),

    path("seller_dashboard/product/add", views.add_product, name='add'),
    path("seller_dashboard/product/update/<slug:slug>/", views.update_product, name='update'),
    path("seller_dashboard/product/delete/<slug:slug>/", views.delete_product, name='delete'),


    path("seller_dashboard/order/", views.order_product, name='order'),
    path("seller_dashboard/order/view/<int:id>/", views.order_detail, name="seller_order_view"),
    path("seller_dashboard/order/update/<int:id>/", views.update_order_status, name="update_order_status"),

    path("product/<slug:slug>/", views.product_details, name='product_details'),

    path("not-seller/", views.not_seller, name="not_seller"),
    path("choose-role/", views.choose_role, name="choose_role"),
    path("complete-customer/", views.complete_customer, name="complete_customer"),
    path("complete-seller/", views.complete_seller, name="complete_seller"),
path("social/error/", views.social_signup_error, name="social_error"),
    # Reviews
    path('seller_dashboard/reviews/', views.review_dashboard, name='review'),

    # DELETE REVIEW (Fix for delete button)
    path("seller/reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),

    # Download CSV
    path('reviews/download/csv/', views.download_reviews_csv, name='download_reviews_csv'),
    path('help-support/', views.help_support, name='help_support'),
    path('seller-guide/', views. seller_guide, name='seller_guide'),

]
