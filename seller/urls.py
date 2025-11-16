from tkinter.font import names

from django.contrib import admin
from django.urls import path
from seller import views

urlpatterns = [

    path("view/",views.view_product),
    path('registration/',views.seller_registration),
    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller),
    path("seller_dashboard/add/",views.add_product,name='add'),
    path('seller_dashboard/order/',views.order_product,name='order'),
    path("seller_dashboard/order/view/<int:id>/", views.order_detail, name="seller_order_view"),

]