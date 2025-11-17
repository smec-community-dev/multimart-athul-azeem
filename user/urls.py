from django.contrib import admin
from django.urls import path
from user import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("home/",views.products),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("add-to-cart/<slug:slug>",views.add_to_cart,name="add_to_cart"),
    path("cart/",views.cart_page,name="cart_page"),


]

