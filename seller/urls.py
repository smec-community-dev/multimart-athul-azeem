from django.urls import path
from zope.interface import named

from seller import views

urlpatterns = [
    # ==================== SELLER DASHBOARD ====================
    path("seller_dashboard/", views.view_product, name="seller_dashboard"),


    # SELLER FEATURES
    path("seller_dashboard/profile/", views.seller_profile_view, name="profile"),
    path("seller_dashboard/product/add/", views.add_product, name='add'),
    path("seller_dashboard/product/update/<slug:slug>/", views.update_product, name='update'),
    path("seller_dashboard/product/delete/<slug:slug>/", views.delete_product, name='delete'),
    path("seller_dashboard/order/", views.order_product, name='order'),
    path("seller_dashboard/order/view/<int:id>/", views.order_detail, name="seller_order_view"),
    path("seller_dashboard/order/update/<int:id>/", views.update_order_status, name="update_order_status"),
    path("seller_dashboard/product/<slug:slug>/", views.product_details, name='product_details'),
    path("seller_dashboard/reviews/", views.review_dashboard, name='review'),
    path("seller_dashboard/reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),
    path("seller_dashboard/reviews/download/csv/", views.download_reviews_csv, name='download_reviews_csv'),
    path("seller_dashboard/help-support/", views.help_support, name='help_support'),
    path("seller_dashboard/seller-guide/", views.seller_guide, name='seller_guide'),

    # Not seller page
    path("not-seller/", views.not_seller, name="not_seller"),
    path('seller_dashboar/privacypolicy/',views.privacypolicy,name='privacy'),
path('seller_dashboar/Contact Us/',views.contact,name='contact'),
path('seller_dashboar/Terms of /',views.service,name='service'),
    path('seller_dashboar/Feedback/', views.feedback, name='feedback'),
]
