from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from core.models import Category,SubCategory
from seller.models import Product
User = get_user_model()
from seller.models import Product
from user.models import Cart


def  products(request):
    return render(request,"user/user_home.html")
def profile(request):
    return render(request, "user/profile.html")

def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    main_image = product.images.filter(image_type='Main').first()
    gallery_images = product.images.all()

    return render(request, "user/product_detail.html", {
        "product": product,
        "main_image": main_image,
        "gallery": gallery_images
    })


@login_required(login_url="login")
def add_to_cart(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("user/user_home")

    quantity = int(request.GET.get("quantity", 1))

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity = quantity


        if cart_item.quantity > product.stock:
            cart_item.quantity = product.stock

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


def user_login(request):
    if request.user.is_authenticated:
        return redirect("user_home")


    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # messages.info(request, "Login successful!")

            if user.role == "seller":
                return redirect("seller_dashboard")

            return redirect("user_home")

        messages.error(request, "Invalid username or password")
        return redirect("login")

    return render(request, "user/login.html")




def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("/user/home")


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




def category_products(request,slug):
    try:
        category=Category.objects.get(slug=slug)
        products=Product.objects.filter(subcategory__category=category)
    except Category.DoesNotExist:
        category=None
        products=[]
    return render(request,"user/category_products.html",{"category":category,"products":products})







