import sys

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

from user import views as user_views

def redirect_to_user_home(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect("admin_panel:admin_dashboard")
        if hasattr(request.user, "seller_details") and request.user.seller_details:
            return redirect("seller:seller_dashboard")
        return redirect("user:user_home")
    return redirect("admin_panel:login")

urlpatterns = [
    path('admin/', admin.site.urls),  # Fixed: was 'hello/'

    # Root redirects to user home
    path("", redirect_to_user_home, name="root"),

    # USER app (user home)
    path("user/", include("user.urls")),
    path(
        "order/<int:order_id>/",
        user_views.order_detail,
        name="user_order_track",
    ),

    # SELLER app
    path("seller/", include("seller.urls")),

    # ADMIN PANEL (includes common auth + admin dashboard)
    path("", include(("core.urls", "admin_panel"), namespace="admin_panel")),  # ← NO PREFIX, includes /login/, /registration/, /admin-dashboard/

    # GOOGLE / ALLAUTH
    path("accounts/", include("allauth.urls")),

    path('not/', include('notifications.urls', namespace='not')),
]

if settings.DEBUG or "runserver" in sys.argv:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)