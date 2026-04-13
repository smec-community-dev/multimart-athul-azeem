from django.urls import path

from notifications import views as notification_views
from seller import views

app_name = 'seller'
urlpatterns = [
    path(
        "notifications/",
        notification_views.seller_notifications_page,
        name="seller_notifications",
    ),
    # ==================== SELLER DASHBOARD ====================
    path("seller_dashboard/", views.view_product, name="seller_dashboard"),


    # SELLER FEATURES
    path("seller_dashboard/profile/", views.seller_profile_view, name="profile"),
    path("seller_dashboard/product/add/", views.add_product, name='add'),
    path("seller_dashboard/product/update/<slug:slug>/", views.update_product, name='update'),
    path("seller_dashboard/product/delete/<slug:slug>/", views.delete_product, name='delete'),
    path("seller_dashboard/order/", views.order_product, name='order'),
    path("seller_dashboard/order/view/<int:id>/", views.order_detail, name="seller_order_view"),
    path(
        "seller_dashboard/order/<int:order_id>/buyer-snapshot/",
        views.order_buyer_snapshot,
        name="order_buyer_snapshot",
    ),
    path("seller_dashboard/order/update/<int:id>/", views.update_order_status, name="update_order_status"),
    path("seller_dashboard/product/<slug:slug>/", views.product_details, name='product_details'),
    path("seller_dashboard/reviews/", views.review_dashboard, name='review'),
    path("seller_dashboard/reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),
    path("seller_dashboard/reviews/download-csv/", views.download_reviews_csv, name='download_reviews_csv'),
    path("seller_dashboard/help-support/", views.help_support, name='help_support'),
    path("seller_dashboard/seller-guide/", views.seller_guide, name='seller_guide'),

    # Not seller page
    path("not-seller/", views.not_seller, name="not_seller"),
    path("seller_dashboard/privacypolicy/", views.privacypolicy, name='privacy'),
    path("seller_dashboard/contact-us/", views.contact, name='contact'),
    path("seller_dashboard/terms-of-service/", views.service, name='service'),
    path("seller_dashboard/feedback/", views.feedback, name='feedback'),
    path("seller_dashboard/complete_customer/", views.complete_customer, name='complete_customer'),
    path("seller_dashboard/complete_seller/", views.complete_seller, name='complete_seller'),
]
