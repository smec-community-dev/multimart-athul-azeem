"""
Restrict the custom MultiMart admin dashboard to Django superusers only.
Staff who are not superusers cannot access /admin-dashboard/*.
"""

from django.contrib import messages
from django.shortcuts import redirect


ADMIN_DASHBOARD_PREFIX = "/admin-dashboard"


class SuperuserAdminDashboardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(ADMIN_DASHBOARD_PREFIX):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect("admin_panel:login")

        if not request.user.is_superuser:
            messages.error(
                request,
                "Access denied. Only site administrators can open the admin dashboard.",
            )
            return redirect("user:user_home")

        return self.get_response(request)
