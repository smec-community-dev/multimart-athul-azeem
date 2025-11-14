
from django.shortcuts import render
from  .models import Product

def view_product(request):
    products=Product.objects.all()
    return render(request,"seller/sellerdashboard.html",{"product":products})

def update_product(request):
    products = Product.objects.all()
    return  render(request,"seller/features.html")