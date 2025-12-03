# main/urls.py (corrected)
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def redirect_to_user_home(request):
    # Implement your redirect logic here, e.g., to user dashboard
    if request.user.is_authenticated:
        if hasattr(request.user, 'seller_details') and request.user.seller_details:
            return redirect('seller:seller_dashboard')
        else:
            return redirect('user:home')
    return redirect('admin_panel:login')  # Or registration

urlpatterns = [
    path('admin/', admin.site.urls),  # Fixed: was 'hello/'

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

    path('not/', include('notifications.urls', namespace='not')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)