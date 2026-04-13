from django.shortcuts import redirect
from functools import wraps

def seller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect('admin_panel:login')

        # Check if user has seller_details
        if not hasattr(request.user, "seller_details"):
            return redirect("seller:not_seller")  # or show error page

        return view_func(request, *args, **kwargs)
    return wrapper
