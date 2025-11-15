from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.products, name="products"),
    path("register/", views.user_register, name="register"),
    path("login/", views.user_login, name="login"),
]
