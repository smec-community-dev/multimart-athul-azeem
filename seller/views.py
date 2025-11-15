from django.shortcuts import render, redirect
from .models import Product, SellerDetails
from django.contrib.auth import authenticate, login

def view_product(request):
    products=Product.objects.all()
    return render(request,"seller/sellerdashboard.html",{"product":products})


def update_product(request):
    products = Product.objects.all()
    return  render(request,"seller/features.html")

def login_seller(request):
    if request.method =="POST":
        username=request.POST.get("username")
        password=request.POST.get("password")
        print(username,password)


        user=authenticate(request,username=username,password=password)
        print(user)
        if user is not None:
            login(request, user)

            is_seller=SellerDetails.objects.filter(user=user).exists()
            if is_seller:
                return redirect('seller_dashboard')
            else:
                return redirect('user/user_dashboard')
        return render(request,"seller/login.html",{"error":"invalid username or password"})
    return render(request,"seller/login.html")


