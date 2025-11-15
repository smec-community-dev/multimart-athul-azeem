from django.contrib import admin
from django.urls import path
from seller import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("sellerdashboard/",views.view_product),
    path("login/",views.login_seller)
]