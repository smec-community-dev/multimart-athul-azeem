from tkinter.font import names

from django.contrib import admin
from django.urls import path
from seller import views

urlpatterns = [

    path("view/",views.view_product),
    path('home/',views.home,name='home'),
    path('registration/',views.seller_registration,name='registration'),
    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller,name='login'),
    path("logout/", views.logout_seller, name='logout'),
    path("seller_dashboard/add/",views.add_product,name='add')
]