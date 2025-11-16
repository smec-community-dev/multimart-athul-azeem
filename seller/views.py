from django.contrib.auth import authenticate
from django.core.checks import messages
from django.utils.text import slugify
from django.shortcuts import render, redirect

from core.models import User
from .models import Product, SellerDetails
from django.contrib.auth import authenticate, login
from core.models import SubCategory
from .models import Product, SellerDetails


def view_product(request):
    products=Product.objects.all()
    return render(request,"seller/sellerdashboard.html",{"product":products})

def add_product(request):
    if request.method=="POST":
        print(".,,,")
        seller = SellerDetails.objects.get(user=request.user)
        subcategory_id = request.POST.get("subcategory")
        name = request.POST.get("name")
        description = request.POST.get("description")
        price = request.POST.get("price")
        stock = request.POST.get("stock")
        color = request.POST.get("color")
        size = request.POST.get("size")
        slug = slugify(name)
        subcategory = SubCategory.objects.get(id=subcategory_id)

        Product.objects.create(
            seller=seller,
            subcategory=subcategory,
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock=stock,
            color=color,
            size=size,
        )
        return redirect("seller_dashboard")

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
        return redirect('seller/login')






    return render(request,"seller/seller_registration.html")



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
                print(".............")
                return redirect('seller_dashboard')

            else:
                return redirect('/home')
        return render(request,"seller/login.html",{"error":"invalid username or password"})
    return render(request,"seller/login.html")



    subcategories = SubCategory.objects.all()
    return render(request, "seller/features.html", {"subcategories": subcategories,"products":products})

