from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from seller.models import Product
from user.models import Cart


def  products(request):
    return render(request,"user/user_home.html")

def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    return render(request, "user/product_detail.html", {"product": product})

@login_required(login_url="login")
def add_to_cart(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("user/user_home")

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f"{product.name} added to cart")
    return redirect("cart_page")



@login_required(login_url="login")
def cart_page(request):
    cart_items = Cart.objects.filter(user=request.user)

    total_amount = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, "user/cart.html", {
        "cart_items": cart_items,
        "total": total_amount
    })
