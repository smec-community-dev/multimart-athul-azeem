from functools import wraps
from django.shortcuts import redirect

def user_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # Check if user is logged in
        if not request.user.is_authenticated:
            return redirect('user:user_home')  # or your login page

        # If the logged-in user is seller, block access to user pages
        if hasattr(request.user, "seller_details"):
            return redirect("seller:not_seller")  # redirect to not seller page or home

        return view_func(request, *args, **kwargs)

    return wrapper
