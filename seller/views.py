from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Product, User, SellerDetails


def view_product(request):
    products=Product.objects.all()
    return render(request,"seller/sellerdashboard.html",{"product":products})

def update_product(request):
    products = Product.objects.all()
    return  render(request,"seller/features.html")

def seller_registration(request):
    if request.method=="POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        role = request.POST.get("role")
        shop_name = request.POST.get("shop_name")
        shop_address = request.POST.get("shop_address")
        business_type = request.POST.get("business_type")
        gst_number = request.POST.get("gst_number")
        bank_account = request.POST.get("bank_account")


        if User.objects.filter(username=username).exists():
            messages.error(request, f" username {username} already exists")
            return render(request, "seller/seller_registration.html")

        user=User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role


        )
        SellerDetails.objects.create(
            user=user,
            shop_name=shop_name,
            shop_address=shop_address,
            business_type=business_type,
            gst_number=gst_number,
            bank_account=bank_account
        )

        messages.success(request, "Registration successful! Please log in.")
        return redirect('/login')






    return render(request,"seller/seller_registration.html")

