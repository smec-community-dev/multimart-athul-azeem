from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import render,redirect

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")

            if user.role == "seller":
                return redirect("seller_dashboard")

            return redirect("/user/home")

        messages.error(request, "Invalid username or password")
        return redirect("/user/login")

    return render(request, "user/login.html")

def products(request):
    return render(request,"user/user_home.html")