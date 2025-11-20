
from django.urls import path
from user import views


urlpatterns = [
    path("home/",views.products,name="user_home"),
    path("profile/", views.profile, name="profile"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("add-to-cart/<slug:slug>",views.add_to_cart,name="add_to_cart"),
    path("cart/",views.cart_page,name="cart_page"),
    path("cart/update/<int:item_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("add-to-wishlist/<slug:slug>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/", views.wishlist_page, name="wishlist_page"),
    path("category/<slug:slug>/",views.category_products,name="category_products"),
    path("register/",views.user_register,name="register"),
    path("login/",views.user_login,name="login"),
    path("logout/", views.user_logout, name="logout"),

]
