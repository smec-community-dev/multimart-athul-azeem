from tkinter.font import names

from django.urls import path
from seller import views

urlpatterns = [

    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller,)
]