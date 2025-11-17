from django.shortcuts import render,redirect
from core.models import Category,SubCategory
from seller.models import Product
def  products(request):
    return render(request,"user/user_home.html")



def category_products(request,slug):
    try:
        category=Category.objects.get(slug=slug)
        products=Product.objects.filter(subcategory__category=category)
    except Category.DoesNotExist:
        category=None
        products=[]
    return render(request,"user/category_products.html",{"category":category,"products":products})



def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    return render(request, "user/product_detail.html", {"product": product})




