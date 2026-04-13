from django.conf import settings
from django.contrib.auth import authenticate, login, get_user_model, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from core.models import Category,SubCategory
from .decorators import user_required

User = get_user_model()
from seller.models import Product
from user.models import Cart, Wishlist, Review
from .models import Cart, Order, OrderItem
from django.db.models import Q
from difflib import get_close_matches
from django.core.paginator import Paginator
from .models import Address
from django.contrib.auth import update_session_auth_hash
import razorpay
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal


def products(request):
    # Show featured products that actually have images to avoid blank slider cards.
    featured_with_images = Product.objects.filter(is_featured=True, images__isnull=False).distinct()
    bestseller_products = featured_with_images[:4]
    slider_products = featured_with_images[:6]
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

@login_required(login_url="admin_panel:login")
def profile(request):
    address, created = Address.objects.get_or_create(user=request.user)

    # Check which section to show (profile or address)
    section = request.GET.get('section', 'profile')

    # FIXED: Use 'order_date' instead of 'created_at'
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    orders = Order.objects.filter(user=request.user).order_by('-order_date')  # CHANGED HERE

    # Handle PROFILE form submission
    if request.method == "POST" and 'username' in request.POST:
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        email = (request.POST.get("email") or "").strip().lower()
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
        "wishlist_items": wishlist_items,
        "orders": orders,
    })

def product_detail(request, slug):
    product = Product.objects.filter(slug=slug).first()

    if product is None:
        return redirect("user:user_home")

    # Main & Gallery Images
    main_image = product.images.filter(image_type='Main').first()
    gallery_images = product.images.filter(image_type='Gallery')

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
    user_review_exists = False

    if request.user.is_authenticated:
        has_delivered_order = OrderItem.objects.filter(
            order__user=request.user,
            order__status="Delivered",
            product=product
        ).exists()

        # Check if user already reviewed
        user_review_exists = Review.objects.filter(
            user=request.user, product=product
        ).exists()

    return render(request, "user/product_detail.html", {
        "product": product,
        "main_image": main_image,
        "gallery": gallery_images,
        "wishlist_count": wishlist_count,
        "in_wishlist": in_wishlist,
        "related_products": related_products,
        "has_delivered_order": has_delivered_order,
        "user_review_exists": user_review_exists,   # ADD THIS
    })

@login_required(login_url="admin_panel:login")
def add_to_cart(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("user:user_home")

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
    return redirect("user:cart_page")


@login_required(login_url="admin_panel:login")
def buy_now(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("user:user_home")

    quantity = int(request.GET.get("quantity", 1))

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity = quantity
        cart_item.save()

    return redirect("user:checkout")


@login_required(login_url="admin_panel:login")
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
        return redirect("user:cart_page")

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

    return redirect("user:cart_page")


def remove_cart_item(request, item_id):
    Cart.objects.filter(id=item_id, user=request.user).delete()
    return redirect("user:cart_page")

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
        return redirect('user:product_detail', slug=slug)

    # Check if user already reviewed
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, "You already reviewed this product.")
        return redirect('user:product_detail', slug=slug)

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
        return redirect('user:product_detail', slug=slug)

    return redirect('user:product_detail', slug=slug)





def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # Base queryset
    products = Product.objects.filter(subcategory__category=category)

    # ----- SEARCH -----
    search = request.GET.get("search", "")
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(subcategory__name__icontains=search)
        )
    # ----- FILTER -----
    selected_price = request.GET.get("price")
    if selected_price == "under_1000":
        products = products.filter(price__lt=1000)
    elif selected_price == "1000_10000":
        products = products.filter(price__gte=1000, price__lte=10000)
    elif selected_price == "10000_50000":
        products = products.filter(price__gte=10000, price__lte=50000)
    elif selected_price == "over_50000":
        products = products.filter(price__gt=50000)

    # ----- SORT -----
    sort = request.GET.get("sort", "featured")
    if sort == "low_to_high":
        products = products.order_by("price")
    elif sort == "high_to_low":
        products = products.order_by("-price")
    elif sort == "newest":
        products = products.order_by("-created_at")
    else:
        products = products.order_by("-is_featured")

    # ----- PAGINATION -----
    paginator = Paginator(products, 4)   # 8 items per page
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    # ----- FEATURED SLIDER PRODUCTS -----
    slider_products = Product.objects.filter(
        subcategory__category=category, is_featured=True
    )[:4]

    return render(request, "user/category_products.html", {
        "category": category,
        "products": products,
        "slider_products": slider_products,
        "selected_price": selected_price,
        "sort": sort,
        "search": search,
    })

@login_required(login_url="admin_panel:login")
def add_to_wishlist(request, slug):
    product = Product.objects.filter(slug=slug).first()
    if product is None:
        return redirect("user:user_home")

    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)

    if wishlist_item.exists():
        wishlist_item.delete()
        # messages.info(request, f"{product.name} removed from wishlist")
    else:
        Wishlist.objects.create(user=request.user, product=product)
        # messages.success(request, f"{product.name} added to wishlist")

    return redirect(request.META.get("HTTP_REFERER", "user_home"))

@login_required(login_url="admin_panel:login")
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
@login_required(login_url="admin_panel:login")
def checkout(request):
    buy_slug = request.GET.get("buy")
    quantity = request.GET.get("quantity", 1)

    # Get user's addresses and counts
    addresses = Address.objects.filter(user=request.user)
    cart_count = Cart.objects.filter(user=request.user).count()
    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    # BUY NOW MODE
    if buy_slug:
        try:
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
                "buy_now": True,
                "cart_count": cart_count,
                "wishlist_count": wishlist_count,
                "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID  # ADD THIS
            })
        except Product.DoesNotExist:
            messages.error(request, "Product not found")
            return redirect("user:cart_page")

    # NORMAL CART CHECKOUT
    items = Cart.objects.filter(user=request.user)
    if not items.exists():
        messages.error(request, "Your cart is empty")
        return redirect("user:cart_page")

    total = 0
    for item in items:
        item.subtotal = item.product.price * item.quantity
        total += item.subtotal

    return render(request, "user/checkout.html", {
        "items": items,
        "total": total,
        "addresses": addresses,
        "buy_now": False,
        "cart_count": cart_count,  # ADD THIS
        "wishlist_count": wishlist_count,  # ADD THIS
        "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID  # ADD THIS
    })


def _get_checkout_address_data(request):
    """
    Read shipping address from either selected saved address or checkout form fields.
    Supports both current field names and fallback aliases.
    """
    selected_address_id = request.POST.get("selected_address")
    if selected_address_id:
        try:
            address = Address.objects.get(id=selected_address_id, user=request.user)
        except Address.DoesNotExist:
            return None, "Invalid address selected."

        data = {
            "full_name": (address.full_name or "").strip(),
            "phone": (address.phone or "").strip(),
            "address_line1": (address.street or "").strip(),
            "address_line2": (address.landmark or "").strip(),
            "city": (address.city or "").strip(),
            "state": (address.state or "").strip(),
            "pincode": (address.pincode or "").strip(),
            "country": "India",
        }
    else:
        data = {
            "full_name": (request.POST.get("full_name") or request.POST.get("name") or "").strip(),
            "phone": (request.POST.get("phone") or "").strip(),
            "address_line1": (request.POST.get("address_line1") or request.POST.get("address") or "").strip(),
            "address_line2": (request.POST.get("address_line2") or "").strip(),
            "city": (request.POST.get("city") or "").strip(),
            "state": (request.POST.get("state") or "").strip(),
            "pincode": (request.POST.get("pincode") or "").strip(),
            "country": (request.POST.get("country") or "India").strip(),
        }

    required = ["full_name", "phone", "address_line1", "city", "pincode"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return None, "Please fill all required address fields."

    return data, None


def _format_shipping_address(address_data):
    parts = [
        address_data.get("full_name", ""),
        address_data.get("phone", ""),
        address_data.get("address_line1", ""),
        address_data.get("address_line2", ""),
        address_data.get("city", ""),
        address_data.get("state", ""),
        address_data.get("pincode", ""),
        address_data.get("country", "India"),
    ]
    return ", ".join([part for part in parts if part])


def _persist_user_address(user, address_data):
    # Keep user's latest checkout address available for reuse.
    Address.objects.update_or_create(
        user=user,
        defaults={
            "full_name": address_data.get("full_name", ""),
            "phone": address_data.get("phone", ""),
            "street": address_data.get("address_line1", ""),
            "city": address_data.get("city", ""),
            "state": address_data.get("state", ""),
            "pincode": address_data.get("pincode", ""),
            "landmark": address_data.get("address_line2", ""),
        },
    )


@login_required(login_url="admin_panel:login")
def create_order(request):
    if request.method == "POST":
        try:
            address_data, address_error = _get_checkout_address_data(request)
            if address_error:
                return JsonResponse({"error": address_error}, status=400)

            request.session['checkout_full_name'] = address_data["full_name"]
            request.session['checkout_phone'] = address_data["phone"]
            request.session['checkout_address_line1'] = address_data["address_line1"]
            request.session['checkout_address_line2'] = address_data["address_line2"]
            request.session['checkout_city'] = address_data["city"]
            request.session['checkout_state'] = address_data["state"]
            request.session['checkout_pincode'] = address_data["pincode"]
            request.session['checkout_country'] = address_data["country"]
            shipping_address = _format_shipping_address(address_data)
            _persist_user_address(request.user, address_data)

            # Save BUY NOW data in session if present
            if request.POST.get("buy_now_slug"):
                request.session["buy_now_slug"] = request.POST.get("buy_now_slug")
                request.session["buy_now_qty"] = request.POST.get("buy_now_qty")

            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                return JsonResponse({"error": "Razorpay is not configured on server."}, status=500)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Always compute amount on backend (paise) instead of trusting frontend.
            buy_slug = request.POST.get("buy_now_slug")
            buy_qty = request.POST.get("buy_now_qty")
            if buy_slug:
                try:
                    product = Product.objects.get(slug=buy_slug)
                    quantity = max(int(buy_qty or 1), 1)
                except (Product.DoesNotExist, ValueError):
                    return JsonResponse({"error": "Invalid buy-now product."}, status=400)
                amount_paise = int((Decimal(product.price) * quantity) * 100)
            else:
                items = Cart.objects.filter(user=request.user).select_related("product")
                if not items.exists():
                    return JsonResponse({"error": "Your cart is empty."}, status=400)
                total = sum((Decimal(item.product.price) * item.quantity for item in items), Decimal("0"))
                amount_paise = int(total * 100)

            if amount_paise < 100:
                amount_paise = 100

            # Store amount in session for potential refund
            request.session['payment_amount'] = amount_paise

            # Create Razorpay order
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
            }

            razorpay_order = client.order.create(order_data)

            # Save order + address before payment, then attach payment after success.
            previous_pending_id = request.session.get("pending_online_order_id")
            if previous_pending_id:
                Order.objects.filter(
                    id=previous_pending_id,
                    user=request.user,
                    payment_method="Online",
                    status="Pending",
                    razorpay_payment_id__isnull=True
                ).delete()

            if buy_slug:
                product = Product.objects.get(slug=buy_slug)
                quantity = max(int(buy_qty or 1), 1)
                total_amount = Decimal(product.price) * quantity
                pending_order = Order.objects.create(
                    user=request.user,
                    seller=product.seller,
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    payment_method="Online",
                    status="Pending",
                    razorpay_order_id=razorpay_order["id"],
                )
            else:
                items = Cart.objects.filter(user=request.user).select_related("product")
                first_item = items.first()
                total_amount = sum((Decimal(item.product.price) * item.quantity for item in items), Decimal("0"))
                pending_order = Order.objects.create(
                    user=request.user,
                    seller=first_item.product.seller,
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    payment_method="Online",
                    status="Pending",
                    razorpay_order_id=razorpay_order["id"],
                )

            request.session["pending_online_order_id"] = pending_order.id

            return JsonResponse({
                "id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "pending_order_id": pending_order.id,
            })

        except Exception as e:
            print("Create Order Error:", e)
            return JsonResponse({"error": f"Failed to create order: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)
@login_required(login_url="admin_panel:login")
def payment_verify(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                return JsonResponse({"success": False, "error": "Missing payment fields"})

            # Verify the payment signature
            params_dict = {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }

            client.utility.verify_payment_signature(params_dict)

            pending_order_id = request.session.get("pending_online_order_id")
            if not pending_order_id:
                return JsonResponse({"success": False, "error": "Address/order not saved before payment."})

            try:
                order = Order.objects.get(id=pending_order_id, user=request.user)
            except Order.DoesNotExist:
                return JsonResponse({"success": False, "error": "Pending order not found."})

            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_order_id = razorpay_order_id
            order.razorpay_signature = razorpay_signature
            order.status = "Processing"
            order.save(update_fields=["razorpay_payment_id", "razorpay_order_id", "razorpay_signature", "status"])

            # ==========================
            # HANDLE BUY NOW MODE
            # ==========================
            buy_slug = request.session.get("buy_now_slug")
            buy_qty = request.session.get("buy_now_qty")

            if buy_slug:
                try:
                    product = Product.objects.get(slug=buy_slug)
                    quantity = max(int(buy_qty or 1), 1)

                    if not OrderItem.objects.filter(order=order, product=product).exists():
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            unit_price=product.price
                        )

                    # Delete buy now session data
                    if "buy_now_slug" in request.session:
                        del request.session["buy_now_slug"]
                    if "buy_now_qty" in request.session:
                        del request.session["buy_now_qty"]

                except Product.DoesNotExist:
                    return JsonResponse({"success": False, "error": "Product not found"})

            else:
                items = Cart.objects.filter(user=request.user)

                if not items.exists():
                    # Refund the payment since cart is empty
                    try:
                        client.payment.refund(razorpay_payment_id, {"amount": request.session.get('payment_amount', 0)})
                    except:
                        pass  # If refund fails, log it but don't break

                    return JsonResponse({
                        "success": False,
                        "error": "No items in cart. Payment has been refunded."
                    })

                for item in items:
                    if not OrderItem.objects.filter(order=order, product=item.product).exists():
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            unit_price=item.product.price
                        )

                # Clear cart only after successful order creation
                items.delete()

            # Clear session address values
            address_keys = ['checkout_full_name', 'checkout_phone', 'checkout_address_line1',
                            'checkout_address_line2', 'checkout_city', 'checkout_state',
                            'checkout_pincode', 'checkout_country']
            for key in address_keys:
                request.session.pop(key, None)
            request.session.pop("pending_online_order_id", None)

            return JsonResponse({
                "success": True,
                "order_id": order.id,
                "message": "Payment verified & order created successfully"
            })

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"success": False, "error": "Signature verification failed"})
        except Exception as e:
            print("Payment Verification Error:", str(e))
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})
@login_required(login_url="admin_panel:login")
def clear_wishlist(request):
    Wishlist.objects.filter(user=request.user).delete()
    return redirect('user:wishlist_page')   # change to your wishlist page URL name

@login_required(login_url="admin_panel:login")
def place_order(request):
    if request.method == "POST":
        address_data, address_error = _get_checkout_address_data(request)
        if address_error:
            messages.error(request, address_error)
            return redirect('user:checkout')

        shipping_address = _format_shipping_address(address_data)
        _persist_user_address(request.user, address_data)

        # Determine payment method
        payment_method = request.POST.get("payment_method", "cod")
        if payment_method != "cod":
            messages.error(request, "For online payments, please use Razorpay checkout.")
            return redirect("user:checkout")

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
                payment_method=payment_method,
                status="Pending" if payment_method == "cod" else "Processing"
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )

            return redirect("user:order_success", order_id=order.id)

        # NORMAL CART MODE
        items = Cart.objects.filter(user=request.user)
        if not items.exists():
            messages.error(request, "No items in cart.")
            return redirect("user:cart_page")

        total = sum(item.product.price * item.quantity for item in items)

        order = Order.objects.create(
            user=request.user,
            seller=items.first().product.seller,
            total_amount=total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            status="Pending" if payment_method == "cod" else "Processing"
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price
            )

        items.delete()
        return redirect("user:order_success", order_id=order.id)

    return redirect("user:cart_page")

def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    items = OrderItem.objects.filter(order=order)

    # Clean split: Remove empty parts and strip spaces for no blank commas
    raw_parts = order.shipping_address.split(', ')
    address_parts = [part.strip() for part in raw_parts if part.strip()]  # Filter empties

    # Pad to exactly 8 indices if fewer (e.g., no landmark) to match template safely
    while len(address_parts) < 8:
        address_parts.append('')

    return render(request, "user/order_success.html", {
        "order": order,
        "items": items,
        "address_parts": address_parts,  # Pass clean list instead of raw string
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


@login_required(login_url="admin_panel:login")
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')

    # Add pagination if needed
    paginator = Paginator(orders, 4)  # 10 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    return render(request, "user/my_orders.html", {
        "orders": orders_page,
    })


@login_required(login_url="admin_panel:login")
def order_detail(request, order_id):
    """Buyer view: order summary, seller-style progress timeline, and line items."""
    order = get_object_or_404(
        Order.objects.select_related("seller__user", "user").prefetch_related(
            "items__product__images"
        ),
        id=order_id,
        user=request.user,
    )

    # Align timeline dates with seller dashboard (same fallbacks as seller order view).
    update_fields = []
    if not order.pending_date:
        order.pending_date = order.order_date
        update_fields.append("pending_date")
    if not order.processing_date and order.status in (
        "Processing",
        "Shipped",
        "Delivered",
    ):
        order.processing_date = order.order_date
        update_fields.append("processing_date")
    if not order.shipped_date and order.status in ("Shipped", "Delivered"):
        order.shipped_date = order.order_date
        update_fields.append("shipped_date")
    if not order.delivered_date and order.status == "Delivered":
        order.delivered_date = order.order_date
        update_fields.append("delivered_date")
    if update_fields:
        order.save(update_fields=update_fields)

    items = list(order.items.all())
    for item in items:
        item.line_total = item.unit_price * item.quantity
    total_quantity = sum(item.quantity for item in items)
    calculated_items_total = sum(
        (item.unit_price * item.quantity for item in items), Decimal("0")
    )
    amount_difference = order.total_amount - calculated_items_total

    # Horizontal progress lines between the four steps (avoid template logic duplication).
    st = order.status
    timeline_seg1 = st in ("Processing", "Shipped", "Delivered") or (
        st == "Cancelled" and order.processing_date
    )
    timeline_seg2 = st in ("Shipped", "Delivered") or (
        st == "Cancelled" and order.shipped_date
    )
    timeline_seg3 = st == "Delivered"

    return render(
        request,
        "user/order_detail.html",
        {
            "order": order,
            "items": items,
            "total_quantity": total_quantity,
            "calculated_items_total": calculated_items_total,
            "amount_difference": amount_difference,
            "has_discrepancy": abs(amount_difference) > Decimal("0.01"),
            "timeline_seg1": timeline_seg1,
            "timeline_seg2": timeline_seg2,
            "timeline_seg3": timeline_seg3,
        },
    )


# user/views.py
@login_required(login_url="admin_panel:login")
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ["Pending", "Processing"]:
        order.status = "Cancelled"
        order.save()
        messages.success(request, "Your order has been cancelled.")
    else:
        messages.error(request, "Order cannot be cancelled now.")

    return redirect("user:my_orders")


@login_required(login_url="admin_panel:login")
@require_POST
def delete_cancelled_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status != "Cancelled":
        messages.error(request, "Only cancelled orders can be removed from your list.")
        return redirect("user:my_orders")
    order.delete()
    messages.success(request, "Cancelled order removed from your history.")
    return redirect("user:my_orders")


@login_required(login_url="admin_panel:login")
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
        return redirect("user:profile")

    return render(request, "user/profile.html", {"address": address})

@login_required(login_url="admin_panel:login")
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
        return redirect("user:profile")

    return redirect("user:profile")

@login_required(login_url="admin_panel:login")
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
