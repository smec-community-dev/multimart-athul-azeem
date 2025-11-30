"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
def redirect_to_user_home(request):
    return redirect("user:user_home")   # USER HOME

urlpatterns = [
    path('hello/', admin.site.urls),

    # Root redirects to user home
    path("", redirect_to_user_home, name="root"),

    # USER app (user home)
    path("user/", include("user.urls")),

    # SELLER app
    path("seller/", include("seller.urls")),

    # ADMIN PANEL (includes common auth + admin dashboard)
    path("", include(("core.urls", "admin_panel"), namespace="admin_panel")),  # ← NO PREFIX, includes /login/, /registration/, /admin-dashboard/


    # GOOGLE / ALLAUTH
    path("accounts/", include("allauth.urls")),

    path('notifications/', include('notifications.urls', namespace='not')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
