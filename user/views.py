
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from core.models import Category,SubCategory
User = get_user_model()
from seller.models import Product
from user.models import Cart, Wishlist, Review
from .models import Cart, Order, OrderItem
from django.db.models import Q
from difflib import get_close_matches
from django.core.paginator import Paginator
from .models import Address
from django.contrib.auth import update_session_auth_hash

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


def productslist(request):
    products = Product.objects.all()

    # SEARCH FEATURE
    query = request.GET.get("q", "")
    if query:
        # Normal contains search first
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(subcategory__name__icontains=query) |
            Q(subcategory__category__name__icontains=query)
        )

        # If nothing found => fuzzy match
        if not products.exists():
            product_names = list(Product.objects.values_list("name", flat=True))
            close_matches = get_close_matches(query, product_names, n=5, cutoff=0.3)

            if close_matches:
                products = Product.objects.filter(name__in=close_matches)

    # FILTER VALUES
    price = request.GET.get("price")
    category = request.GET.get("category")
    rating = request.GET.get("rating")
    sort = request.GET.get("sort")

    # PRICE FILTER
    if price == "under_1000":
        products = products.filter(price__lt=1000)
    elif price == "1000_10000":
        products = products.filter(price__gte=1000, price__lte=10000)
    elif price == "10000_50000":
        products = products.filter(price__gte=10000, price__lte=50000)
    elif price == "over_50000":
        products = products.filter(price__gt=50000)

    # CATEGORY FILTER
    if category:
        products = products.filter(subcategory__category__name__iexact=category)

    # RATING FILTER
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

    # PAGINATION
    paginator = Paginator(products, 4)  # 4 per page
    page_number = request.GET.get("page")
    products_page = paginator.get_page(page_number)

    return render(request, "user/products.html", {
        "products": products_page,
        "query": query,
        "selected_price": price,
        "selected_category": category,
        "selected_rating": rating,
        "sort": sort,
        "paginator": paginator,
        "page_obj": products_page,
    })


@login_required(login_url="login")
def profile(request):
    address, created = Address.objects.get_or_create(user=request.user)

    # Check which section to show (profile or address)
    section = request.GET.get('section', 'profile')

    # Handle PROFILE form submission
    if request.method == "POST" and 'username' in request.POST:
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone_number")

        # Split full name into first & last
        first, *last = full_name.split(" ", 1)

        user = request.user
        user.first_name = first
        user.last_name = last[0] if last else ""
        user.username = username
        user.email = email
        user.phone_number = phone
        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("/user/profile/?section=profile")


    # Handle ADDRESS form submission
    if request.method == "POST" and 'street' in request.POST:
        address.full_name = request.POST.get("full_name")
        address.phone = request.POST.get("phone")
        address.street = request.POST.get("street")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.landmark = request.POST.get("landmark")
        address.save()

        messages.success(request, "Address updated successfully!")
        return redirect("/user/profile/?section=address")


    return render(request, "user/profile.html", {
        "address": address,
        "active_section": section,
    })



def product_detail(request, slug):
    product = Product.objects.filter(slug=slug).first()

    if product is None:
        return redirect("user_home")

    # Main & Gallery Images
    main_image = product.images.filter(image_type='Main').first()
    gallery_images = product.images.all()

    # Wishlist count
    wishlist_count = Wishlist.objects.filter(
        user=request.user
    ).count() if request.user.is_authenticated else 0

    # Wishlist check for this product
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, product=product
        ).exists()

    # ==== RELATED PRODUCTS (same SubCategory) ====
    related_products = Product.objects.filter(
        subcategory=product.subcategory
    ).exclude(id=product.id)[:4]

    # ==== Check if user bought AND delivered this product ====
    has_delivered_order = False
    if request.user.is_authenticated:
        has_delivered_order = OrderItem.objects.filter(
            order__user=request.user,
            order__status="Delivered",
            product=product
        ).exists()

    return render(request, "user/product_detail.html", {
        "product": product,
        "main_image": main_image,
        "gallery": gallery_images,
        "wishlist_count": wishlist_count,
        "in_wishlist": in_wishlist,
        "related_products": related_products,
        "has_delivered_order": has_delivered_order,
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
    search_query = request.GET.get("search", "")  # search text from input box

    cart_items = Cart.objects.filter(user=request.user)

    # Simple filtering by product name only
    if search_query:
        cart_items = cart_items.filter(product__name__icontains=search_query)

    # Calculate total
    total_amount = 0
    for item in cart_items:
        item.subtotal = item.product.price * item.quantity
        total_amount += item.subtotal

    return render(request, "user/cart.html", {
        "cart_items": cart_items,
        "total": total_amount,
        "search": search_query,
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

from .models import OrderItem  # already imported at top
@login_required
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug)

    # Check if user purchased product and order is delivered
    has_bought = OrderItem.objects.filter(
        order__user=request.user,
        order__status='Delivered',
        product=product
    ).exists()

    if not has_bought:
        messages.error(request, "You can review only products you have purchased and are delivered.")
        return redirect('product_detail', slug=slug)

    # Check if user already reviewed
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, "You already reviewed this product.")
        return redirect('product_detail', slug=slug)

    # Submit review
    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        Review.objects.create(
            user=request.user,
            product=product,
            rating=rating,
            comment=comment,
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
    search = request.GET.get("search", "")

    wishlist_items = Wishlist.objects.filter(user=request.user)

    if search:
        wishlist_items = wishlist_items.filter(
            product__name__icontains=search
        )

    return render(request, "user/wishlist.html", {
        "wishlist_items": wishlist_items,
        "search": search,
    })

@login_required(login_url="login")
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

    total = 0
    for item in items:
        item.subtotal = item.product.price * item.quantity   # <-- ADD THIS
        total += item.subtotal

    return render(request, "user/checkout.html", {
        "items": items,
        "total": total,
        "addresses": addresses,
        "buy_now": False
    })

@login_required(login_url="login")
def clear_wishlist(request):
    Wishlist.objects.filter(user=request.user).delete()
    return redirect('wishlist_page')   # change to your wishlist page URL name

@login_required(login_url="login")
def place_order(request):
    if request.method == "POST":

        # Get values safely (None -> "" prevents 'None' printing)
        full_name = request.POST.get("full_name", "") or ""
        phone = request.POST.get("phone_number", "") or ""
        address_line1 = request.POST.get("address_line1", "") or ""
        address_line2 = request.POST.get("address_line2", "") or ""
        city = request.POST.get("city", "") or ""
        state = request.POST.get("state", "") or ""
        pincode = request.POST.get("pincode", "") or ""
        country = request.POST.get("country", "") or ""

        # Final formatted shipping address string
        shipping_address = f"{full_name}, {phone}, {address_line1}, {address_line2}, {city}, {state}, {pincode}, {country}"

        # BUY NOW MODE
        buy_now_slug = request.POST.get("buy_now_slug")
        buy_now_qty = request.POST.get("buy_now_qty")

        if buy_now_slug:
            product = Product.objects.get(slug=buy_now_slug)
            quantity = int(buy_now_qty)
            total = product.price * quantity

            order = Order.objects.create(
                user=request.user,
                seller=product.seller,
                total_amount=total,
                shipping_address=shipping_address,
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
            shipping_address=shipping_address,
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

    # Split the shipping address into list parts
    address_parts = order.shipping_address.split(",")

    return render(request, "user/order_success.html", {
        "order": order,
        "items": items,
        "address_parts": address_parts,  # send to template
    })

def deals_and_offers(request):
    return render(request,"user/deals_and_offers.html")

from django.contrib import messages

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


@login_required(login_url="login")
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')

    # Add pagination if needed
    paginator = Paginator(orders, 4)  # 10 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    return render(request, "user/my_orders.html", {
        "orders": orders_page,
    })


# user/views.py

def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ["Pending", "Processing"]:
        order.status = "Cancelled"
        order.save()
        messages.success(request, "Your order has been cancelled.")
    else:
        messages.error(request, "Order cannot be cancelled now.")

    return redirect("my_orders")




@login_required(login_url="login")
def manage_address(request):
    address, created = Address.objects.get_or_create(user=request.user)

    if request.method == "POST":
        address.full_name = request.POST.get("name")
        address.phone = request.POST.get("phone")
        address.street = request.POST.get("street")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.landmark = request.POST.get("landmark")
        address.save()

        messages.success(request, "Address updated successfully!")
        return redirect("profile")

    return render(request, "user/profile.html", {"address": address})

@login_required(login_url="login")
def update_profile(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone_number")  # <- CHANGE NAME here

        # Split full name into first & last
        first, *last = full_name.split(" ", 1)

        user = request.user
        user.first_name = first
        user.last_name = last[0] if last else ""
        user.username = username
        user.email = email
        user.phone_number = phone   # <- SAVE PHONE IN USER MODEL
        user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return redirect("profile")

@login_required(login_url="login")
def change_password(request):
    if request.method == "POST":
        old = request.POST.get("old_password")
        new1 = request.POST.get("new_password1")
        new2 = request.POST.get("new_password2")

        if new1 != new2:
            messages.error(request, "New password & confirm password do not match")
            return redirect("/user/profile/?section=password")


        if not request.user.check_password(old):
            messages.error(request, "Old password is incorrect")
            return redirect("/user/profile/?section=password")

        request.user.set_password(new1)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, "Password updated successfully!")
        return redirect("/user/profile/?section=password")


    return redirect("/user/profile/?section=password")
