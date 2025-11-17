from django.urls import path
from seller import views

urlpatterns = [

    path("view/",views.view_product),
    path('home/',views.home,name='home'),
    path('registration/',views.seller_registration,name='registration'),

    path('home/',views.home,name='home'),
    path('registration/',views.seller_registration,name='registration'),
    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller,name='login'),
    path("logout/", views.logout_seller, name='logout'),
    path('registration/',views.seller_registration),
    path("seller_dashboard/",views.view_product,name="seller_dashboard"),
    path("login/",views.login_seller,name='login'),
    path("logout/", views.logout_seller, name='logout'),
    path("seller_dashboard/add/",views.add_product,name='add')
    path("seller_dashboard/add/",views.add_product,name='add'),
    path('seller_dashboard/order/',views.order_product,name='order'),
    path("seller_dashboard/order/view/<int:id>/", views.order_detail, name="seller_order_view"),
    path('seller_dashboard/delete/<int:id>',views.delete_product,name='delete'),
    path("seller_dashboard/update/<int:id>", views.update_product, name='update')

]