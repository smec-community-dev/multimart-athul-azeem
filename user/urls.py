
from django.urls import path
from user import views


urlpatterns = [
    path("home/",views.products,name="user_home"),
    path("profile/", views.profile, name="profile"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("products/",views.productslist,name="products_list"),
    path("deals-and-offers/",views.deals_and_offers,name="deals_and_offers"),
    path("contact/",views.contact,name="contact"),
    path("about/",views.about,name="about"),
    path("add-to-cart/<slug:slug>",views.add_to_cart,name="add_to_cart"),
    path("cart/",views.cart_page,name="cart_page"),
    path("cart/update/<int:item_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("buy-now/<slug:slug>/", views.buy_now, name="buy_now"),
    path("add-to-wishlist/<slug:slug>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/", views.wishlist_page, name="wishlist_page"),
    path("add-review/<slug:slug>/",views.add_review, name="add_review"),
    path("checkout",views.checkout,name="checkout"),
    path('place-order/', views.place_order, name='place_order'),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
    path("category/<slug:slug>/",views.category_products,name="category_products"),
    path("register/",views.user_register,name="register"),
    path("login/",views.user_login,name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("help-center/",views.help_center, name="help_center"),
    path("returns/",views.returns, name="returns"),
    path("shipping-info/",views.shipping_info, name="shipping_info"),
    path("privacy-policy/",views.privacy_policy, name="privacy_policy"),

]
