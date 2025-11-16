from django.contrib import admin
from django.urls import path
from seller import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("view/",views.view_product),
<<<<<<< HEAD
    path('registration/',views.seller_registration),
    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller,)
=======
    path('add/',views.add_product)
>>>>>>> feature/seller-add-products
]