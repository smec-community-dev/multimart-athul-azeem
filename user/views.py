
from django.contrib.auth import authenticate, login
from django.shortcuts import render,redirect
from django.contrib.auth.hashers import make_password
from django.contrib import messages

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



def user_register(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        role = request.POST.get("role")
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Password and Confirm Password do not match")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")



        User.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            username=username,
            phone_number=phone,
            password=make_password(password),
        )

        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "user/register.html")

