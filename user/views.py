
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from core.models import Category,SubCategory
User = get_user_model()
from seller.models import Product
from user.models import Cart, Wishlist, Review
from .models import Cart, Order, OrderItem
from django.db.models import Q
from difflib import get_close_matches
from django.core.paginator import Paginator

def products(request):
    bestseller_products = Product.objects.filter(is_featured=True)[:4]
    slider_products = Product.objects.filter(is_featured=True)
    query = request.GET.get("q", "")
    all_products = Product.objects.all()
    results = all_products

    if query:
        # First normal search
        results = all_products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(subcategory__name__icontains=query) |
            Q(subcategory__category__name__icontains=query)
        )

        # If nothing found -> do fuzzy match
        if not results.exists():
            product_names = list(all_products.values_list("name", flat=True))
            close_matches = get_close_matches(query, product_names, n=5, cutoff=0.3)

            if close_matches:
                results = all_products.filter(name__in=close_matches)

    return render(request, "user/user_home.html", {
        "products": results,
        "slider_products": slider_products,
        "query": query,
        "bestseller_products": bestseller_products,
    })

from django.core.paginator import Paginator

def productslist(request):
    products = Product.objects.all()

    # Get filter values
    price = request.GET.get("price")
    category = request.GET.get("category")
    rating = request.GET.get("rating")
    sort = request.GET.get("sort")

    # PRICE filter
    if price == "under_1000":
        products = products.filter(price__lt=1000)
    elif price == "1000_10000":
        products = products.filter(price__gte=1000, price__lte=10000)
    elif price == "10000_50000":
        products = products.filter(price__gte=10000, price__lte=50000)
    elif price == "over_50000":
        products = products.filter(price__gt=50000)

    # CATEGORY filter
    if category:
        products = products.filter(subcategory__category__name__iexact=category)

    # RATING filter
    if rating:
        products = products.filter(average_rating__gte=rating)

    # SORTING
    if sort == "featured":
        products = products.filter(is_featured=True)
    elif sort == "low_to_high":
        products = products.order_by("price")
    elif sort == "high_to_low":
        products = products.order_by("-price")
    elif sort == "newest":
        products = products.order_by("-created_at")

    # PAGINATION MUST COME LAST
    paginator = Paginator(products, 4)  # 4 products each page
    page_number = request.GET.get("page")
    products_page = paginator.get_page(page_number)

    return render(request, "user/products.html", {
        "products": products_page,
        "selected_price": price,
        "selected_category": category,
        "selected_rating": rating,
        "sort": sort,
        "paginator": paginator,
        "page_obj": products_page,
    })



def profile(request):
    return render(request, "user/profile.html")

def product_detail(request, slug):
    product = Product.objects.filter(slug=slug).first()

    if product is None:
        return redirect("user_home")

    # Main & Gallery Images
    main_image = product.images.filter(image_type='Main').first()
    gallery_images = product.images.all()

    # Wishlist count
    wishlist_count = Wishlist.objects.filter(user=request.user).count() if request.user.is_authenticated else 0

    # Wishlist check for this product
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    # ==== RELATED PRODUCTS (using same SubCategory) ====
    related_products = Product.objects.filter(
        subcategory=product.subcategory
    ).exclude(id=product.id)[:4]

    return render(request, "user/product_detail.html", {
        "product": product,
        "main_image": main_image,
        "gallery": gallery_images,
        "wishlist_count": wishlist_count,
        "in_wishlist": in_wishlist,
        "related_products": related_products,
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

    # messages.success(request, f"{product.name} added to cart")
    return redirect("cart_page")


@login_required(login_url="login")
def buy_now(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("user_home")

    quantity = int(request.GET.get("quantity", 1))

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity = quantity
        cart_item.save()

    return redirect("checkout")



@login_required(login_url="login")
def cart_page(request):
    cart_items = Cart.objects.filter(user=request.user)

    total_amount = 0
    for item in cart_items:
        item.subtotal = item.product.price * item.quantity
        total_amount += item.subtotal

    return render(request, "user/cart.html", {
        "cart_items": cart_items,
        "total": total_amount
    })



def update_cart(request, item_id):
    item = Cart.objects.filter(id=item_id, user=request.user).first()

    if not item:
        return redirect("cart_page")

    action = request.POST.get("action")

    if action == "increase":
        item.quantity += 1
        item.save()

    elif action == "decrease":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

    return redirect("cart_page")


def remove_cart_item(request, item_id):
    Cart.objects.filter(id=item_id, user=request.user).delete()
    return redirect("cart_page")


@login_required
def add_review(request, slug):
    product = Product.objects.filter(slug=slug).first()

    if not product:
        messages.error(request, "Product not found!")
        return redirect("home_page")

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        if Review.objects.filter(user=request.user, product=product).exists():
            messages.error(request, "You already reviewed this product.")
            return redirect('product_detail', slug=slug)

        Review.objects.create(
            user=request.user,
            product=product,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Review submitted successfully!")
        return redirect('product_detail', slug=slug)

    return redirect('product_detail', slug=slug)



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


def category_products(request, slug):
    category = Category.objects.get(slug=slug)

    # Base queryset: only products inside this category
    products = Product.objects.filter(subcategory__category=category)

    search = request.GET.get("search")  # <-- NEW

    # Search Filter
    if search:
        products = products.filter(name__icontains=search)

    # Get filters from query params
    selected_price = request.GET.get("price")
    sort = request.GET.get("sort", "featured")
    page_number = request.GET.get("page", 1)

    # PRICE FILTERING
    if selected_price == "under_1000":
        products = products.filter(price__lt=1000)

    elif selected_price == "1000_10000":
        products = products.filter(price__gte=1000, price__lte=10000)

    elif selected_price == "10000_50000":
        products = products.filter(price__gte=10000, price__lte=50000)

    elif selected_price == "over_50000":
        products = products.filter(price__gt=50000)

    # SORTING
    if sort == "low_to_high":
        products = products.order_by("price")

    elif sort == "high_to_low":
        products = products.order_by("-price")

    elif sort == "newest":
        products = products.order_by("-created_at")

    else:
        products = products.order_by("-is_featured")

    # PAGINATION (4 per page)
    paginator = Paginator(products, 4)
    products = paginator.get_page(page_number)

    # FEATURED SLIDER PRODUCTS
    slider_products = Product.objects.filter(subcategory__category=category, is_featured=True)[:4]

    return render(request, "user/category_products.html", {
        "category": category,
        "products": products,
        "slider_products": slider_products,
        "selected_price": selected_price,
        "sort": sort,
        "search":search
    })




@login_required(login_url="login")
def add_to_wishlist(request, slug):
    product = Product.objects.filter(slug=slug).first()
    if product is None:
        return redirect("user_home")

    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)

    if wishlist_item.exists():
        wishlist_item.delete()
        # messages.info(request, f"{product.name} removed from wishlist")
    else:
        Wishlist.objects.create(user=request.user, product=product)
        # messages.success(request, f"{product.name} added to wishlist")

    return redirect(request.META.get("HTTP_REFERER", "user_home"))

@login_required(login_url="login")
def wishlist_page(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, "user/wishlist.html", {"wishlist_items": wishlist_items})


@login_required
def checkout(request):
    buy_slug = request.GET.get("buy")
    quantity = request.GET.get("quantity", 1)

    addresses = []  # always define addresses to avoid NameError

    # BUY NOW MODE
    if buy_slug:
        product = Product.objects.get(slug=buy_slug)

        item = {
            "product": product,
            "quantity": int(quantity),
            "subtotal": product.price * int(quantity)
        }

        total = item["subtotal"]

        return render(request, "user/checkout.html", {
            "items": [item],
            "total": total,
            "addresses": addresses,
            "buy_now": True
        })

    # NORMAL CART CHECKOUT
    items = Cart.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)

    return render(request, "user/checkout.html", {
        "items": items,
        "total": total,
        "addresses": addresses,
        "buy_now": False
    })


@login_required
@login_required
def place_order(request):
    if request.method == "POST":

        # BUY NOW hidden values from checkout.html
        buy_now_slug = request.POST.get("buy_now_slug")
        buy_now_qty = request.POST.get("buy_now_qty")

        # BUY-NOW MODE
        if buy_now_slug:
            product = Product.objects.get(slug=buy_now_slug)
            quantity = int(buy_now_qty)
            total = product.price * quantity

            order = Order.objects.create(
                user=request.user,
                seller=product.seller,
                total_amount=total,
                shipping_address=f"{request.POST.get('address_line1')}, "
                                 f"{request.POST.get('address_line2')}, "
                                 f"{request.POST.get('city')}, "
                                 f"{request.POST.get('state')}, "
                                 f"{request.POST.get('pincode')}, "
                                 f"{request.POST.get('country')}",
                payment_method=request.POST.get("payment_method"),
                status="Pending"
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )

            return redirect("order_success", order_id=order.id)

        # NORMAL CART MODE
        items = Cart.objects.filter(user=request.user)
        if not items.exists():
            messages.error(request, "No items in cart.")
            return redirect("cart_page")

        total = sum(item.product.price * item.quantity for item in items)

        order = Order.objects.create(
            user=request.user,
            seller=items.first().product.seller,
            total_amount=total,
            shipping_address=f"{request.POST.get('address_line1')}, "
                             f"{request.POST.get('address_line2')}, "
                             f"{request.POST.get('city')}, "
                             f"{request.POST.get('state')}, "
                             f"{request.POST.get('pincode')}, "
                             f"{request.POST.get('country')}",
            payment_method=request.POST.get("payment_method"),
            status="Pending"
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price
            )

        items.delete()
        return redirect("order_success", order_id=order.id)

    return redirect("cart_page")

def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    items = OrderItem.objects.filter(order=order)

    return render(request, "user/order_success.html", {
        "order": order,
        "items": items,
    })
def deals_and_offers(request):
    return render(request,"user/deals_and_offers.html")


def contact(request):
    return render(request,"user/contact.html")


def about(request):
    return render(request,"user/about.html")



def help_center(request):
    return render(request, "user/help_center.html")

def returns(request):
    return render(request, "user/returns.html")

def shipping_info(request):
    return render(request, "user/shipping_info.html")

def privacy_policy(request):
    return render(request, "user/privacy_policy.html")
