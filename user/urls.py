from django.contrib import admin
from django.urls import path
from user import views
from user.views import category_products

urlpatterns = [
    path('admin/', admin.site.urls),
    path("home/",views.products),
    path("category/<slug:slug>/",views.category_products,name="category_products"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail")


]
