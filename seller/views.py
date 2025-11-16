from django.contrib.auth import authenticate
from django.utils.text import slugify
from django.shortcuts import render, redirect

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
    subcategories = SubCategory.objects.all()
    return render(request, "seller/features.html", {"subcategories": subcategories,"products":products})

