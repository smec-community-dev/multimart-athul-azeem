from django.contrib import admin
from django.urls import path
from user import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("products/",views.products),
    path("register/",views.user_register),
    path("login/",views.user_login)
]
