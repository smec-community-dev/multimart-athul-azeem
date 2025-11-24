import os
import time

from django.core.checks import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import (
    Count, Sum, F, ExpressionWrapper, DecimalField, Q, Avg, Value, IntegerField
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils.text import slugify
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta

# ============================================================================
# IMPORTS - Project Models
# ============================================================================
from core.models import User, SubCategory, Category
from seller.decorators import seller_required
from seller.models import Product, SellerDetails, ProductImage
from user.models import Order, Review, OrderItem


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(filename):
    """
    Sanitize filename for secure file uploads.
    - Removes invalid characters (keeps alphanumeric, space, dash, underscore)
    - Limits length to 100 characters
    - Adds timestamp to prevent collisions

    Args:
        filename (str): Original filename

    Returns:
        str: Sanitized filename with timestamp
    """
    base, ext = os.path.splitext(filename)
    # Remove invalid chars (Windows/Linux safe: alnum, space, -, _ only)
    base = ''.join(c for c in base if c.isalnum() or c in (' ', '-', '_')).rstrip()
    # Limit length
    if len(base) > 100:
        base = base[:100]
    # Add timestamp to avoid collisions
    timestamp = int(time.time())
    return f"{base}_{timestamp}{ext}"


# ============================================================================
# DASHBOARD & ANALYTICS VIEWS
# ============================================================================

@login_required
@seller_required
def view_product(request):
    """
    Seller Dashboard - Main overview page.

    Displays:
    - Total revenue and orders
    - Product count and ratings
    - Top 3 products (prioritizing low stock items)
    - Recent orders (last 4)
    - Weekly sales chart data
    """
    seller = request.user.seller_details

    # Calculate total revenue from all orders
    total_revenue = (
            OrderItem.objects.filter(order__seller=seller)
            .aggregate(total=Sum(F("unit_price") * F("quantity")))["total"]
            or 0
    )

    # Count total orders
    total_orders = Order.objects.filter(seller=seller).count()

    # Count total products
    products_count = Product.objects.filter(seller=seller).count()

    # Placeholder for pending products (implement if needed)
    pending_products = 0

    # Calculate average rating and count
    rating_data = Review.objects.filter(product__seller=seller).aggregate(
        avg=Avg("rating"),
        count=Count("id")
    )
    avg_rating = rating_data["avg"] or 0
    rating_count = rating_data["count"]

    # Low stock threshold (customize based on business logic)
    low_stock_threshold = 10

    # Get top 3 products (prioritize low stock items)
    top_low_stock_products = (
        Product.objects.filter(seller=seller, stock__lt=low_stock_threshold)
        .annotate(
            total_sold=Coalesce(
                Sum("orderitem__quantity"),
                Value(0, output_field=IntegerField())
            )
        )
        .order_by("-total_sold")[:3]
    )

    # Get overall top products queryset
    overall_top_qs = (
        Product.objects.filter(seller=seller)
        .annotate(
            total_sold=Coalesce(
                Sum("orderitem__quantity"),
                Value(0, output_field=IntegerField())
            )
        )
        .order_by("-total_sold")
    )

    # Combine: prioritize low-stock ones, fill gaps with overall top
    top_products = list(top_low_stock_products)
    if len(top_products) < 3:
        excluded_ids = [p.id for p in top_products]
        fillers = overall_top_qs.exclude(id__in=excluded_ids)[:3 - len(top_products)]
        top_products += list(fillers)

    # Get recent orders (last 4)
    recent_orders = (
        Order.objects.filter(seller=seller)
        .select_related("user")
        .prefetch_related("items", "items__product")
        .order_by("-order_date")[:4]
    )

    # Calculate weekly sales data (last 7 days)
    today = now().date()
    last_week = today - timedelta(days=6)

    orders = Order.objects.filter(
        seller=seller,
        order_date__date__range=[last_week, today]
    ).prefetch_related("items")

    # Mon-Sun format for chart
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_data = {day: 0 for day in week_days}

    for order in orders:
        day = order.order_date.strftime("%a")
        total = sum(item.unit_price * item.quantity for item in order.items.all())
        week_data[day] += float(total)

    sales_labels = list(week_data.keys())
    sales_values = list(week_data.values())

    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "products_count": products_count,
        "pending_products": pending_products,
        "avg_rating": round(avg_rating, 1),
        "rating_count": rating_count,
        "top_products": top_products,
        "recent_orders": recent_orders,
        "low_stock_threshold": low_stock_threshold,
        "sales_labels": sales_labels,
        "sales_values": sales_values,
    }

    return render(request, "seller/sellerdashboard.html", context)


# ============================================================================
# PRODUCT MANAGEMENT VIEWS
# ============================================================================

@login_required
@seller_required
def add_product(request):
    """
    Add new product and view all products with filtering/pagination.

    POST: Creates new product with images
    GET: Displays product list with filters:
        - Search by name
        - Filter by category
        - Filter by status (active/low_stock/out_of_stock)
        - Pagination (10 per page)
    """
    seller = request.user.seller_details

    # Handle POST - Create new product
    if request.method == "POST":
        name = request.POST.get('name')
        subcat_id = request.POST.get('subcategory')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        color = request.POST.get('color')
        size = request.POST.get('size')

        main_image = request.FILES.get('main_image')
        gallery_images = request.FILES.getlist('gallery_images')

        subcategory = SubCategory.objects.get(id=subcat_id)

        # Create product
        product = Product.objects.create(
            seller=seller,
            subcategory=subcategory,
            name=name,
            description=description,
            price=price,
            stock=stock,
            color=color,
            size=size,
            slug=slugify(name)
        )

        # Save main image with sanitized filename
        if main_image:
            sanitized_filename = sanitize_filename(main_image.name)
            main_image.name = sanitized_filename
            ProductImage.objects.create(
                product=product,
                image=main_image,
                image_type="Main"
            )

        # Save gallery images with sanitized filenames
        for img in gallery_images:
            sanitized_filename = sanitize_filename(img.name)
            img.name = sanitized_filename
            ProductImage.objects.create(
                product=product,
                image=img,
                image_type="Gallery"
            )

        return redirect("seller_dashboard")

    # Handle GET - Display products with filters
    products_qs = Product.objects.filter(seller=seller).order_by('-id')

    # Apply search filter
    search = request.GET.get('search', '').strip()
    if search:
        products_qs = products_qs.filter(name__icontains=search)

    # Apply category filter
    category_id = request.GET.get('category')
    if category_id:
        products_qs = products_qs.filter(subcategory__category_id=category_id)

    # Apply status filter based on stock levels
    status = request.GET.get('status')
    if status == 'active':
        products_qs = products_qs.filter(stock__gt=10)
    elif status == 'low_stock':
        products_qs = products_qs.filter(stock__gt=0, stock__lte=10)
    elif status == 'out_of_stock':
        products_qs = products_qs.filter(stock__lte=0)

    # Pagination (10 products per page)
    paginator = Paginator(products_qs, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    # Get categories and subcategories for filters
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    # Get selected category for display
    selected_category = None
    if category_id:
        try:
            selected_category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            pass

    context = {
        "products": products,
        "categories": categories,
        "subcategories": subcategories,
        "selected_category": selected_category,
    }
    return render(request, "seller/features.html", context)


@login_required
@seller_required
def update_product(request, slug):
    """
    Update existing product details and images.

    Args:
        slug (str): Product slug identifier
    """
    product = get_object_or_404(Product, slug=slug)

    if request.method == "POST":
        # Update product fields
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        product.color = request.POST.get("color")
        product.size = request.POST.get("size")
        product.subcategory_id = request.POST.get("subcategory")

        # Regenerate slug if name changed
        new_name = request.POST.get("name")
        if new_name != product.name:
            product.slug = None
            product.name = new_name

        # Add new main image if uploaded
        if "main_image" in request.FILES:
            ProductImage.objects.create(
                product=product,
                image=request.FILES["main_image"],
                image_type="Main"
            )

        # Add new gallery images if uploaded
        if "gallery_images" in request.FILES:
            for img in request.FILES.getlist("gallery_images"):
                ProductImage.objects.create(
                    product=product,
                    image=img,
                    image_type="Gallery"
                )

        product.save()
        return redirect("add")

    subcategories = SubCategory.objects.all()
    return render(request, "seller/update_product.html", {
        "product": product,
        "subcategories": subcategories
    })


@login_required
@seller_required
def delete_product(request, slug):
    """
    Delete a product permanently.

    Args:
        slug (str): Product slug identifier
    """
    product = get_object_or_404(Product, slug=slug)
    product.delete()
    return redirect("add")


@login_required
@seller_required
def product_details(request, slug):
    """
    View detailed product information including reviews and sales stats.

    Displays:
    - Product information and images
    - Reviews with average rating
    - Total quantity sold
    - Number of orders containing this product

    Args:
        slug (str): Product slug identifier
    """
    product = get_object_or_404(
        Product,
        slug=slug,
        seller=request.user.seller_details
    )

    # Get all subcategories for dropdown
    subcategories = SubCategory.objects.all()

    # Fetch reviews with user details
    reviews = (
        Review.objects.filter(product=product)
        .select_related("user")
        .order_by("-created_at")
    )

    # Calculate average rating
    avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    # Get order items for this product
    order_items = OrderItem.objects.filter(product=product)

    # Calculate total quantity sold
    total_quantity_sold = (
            order_items.aggregate(q=Sum("quantity"))["q"] or 0
    )

    # Count unique orders
    order_count = order_items.values("order").distinct().count()

    # Get product images
    images = product.images.all()
    main_image = product.images.first()

    return render(
        request,
        "seller/seller_product_details.html",
        {
            "product": product,
            "subcategories": subcategories,
            "reviews": reviews,
            "avg_rating": round(avg_rating, 1),
            "total_quantity_sold": total_quantity_sold,
            "order_count": order_count,
            "images": images,
            "main_image": main_image,
        }
    )


# ============================================================================
# ORDER MANAGEMENT VIEWS
# ============================================================================

@login_required
@seller_required
def order_product(request):
    """
    View all orders for the seller with filtering and pagination.

    Features:
    - Search by order ID, username, or product name
    - Filter by order status (Pending/Processing/Shipped/Delivered)
    - Pagination (10 orders per page)
    - Shows notification count for pending orders
    """
    seller = getattr(request.user, "seller_details", None)

    if not seller:
        return HttpResponse("You are not a seller")

    # Get base queryset with aggregations
    orders = (
        Order.objects.filter(seller=seller)
        .prefetch_related("items", "items__product")
        .annotate(
            items_count=Count("items"),
            total_price=Sum(F("items__unit_price") * F("items__quantity")),
            total_qty=Sum("items__quantity")
        )
    )

    # Apply search filter
    search = request.GET.get("search", "").strip()
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(items__product__name__icontains=search)
        ).distinct()

    # Apply status filter
    status = request.GET.get('status', None)
    if status and status != 'all':
        orders = orders.filter(status=status.capitalize())

    # Pagination (10 orders per page)
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Count pending orders for notifications
    notification_count = Order.objects.filter(seller=seller, status='Pending').count()

    return render(
        request,
        "seller/seller_order.html",
        {
            "orders": page_obj.object_list,
            "page_obj": page_obj,
            "notification_count": notification_count,
            "search_query": search,
            "current_status": status if status else 'all'
        }
    )


@login_required
@seller_required
def order_detail(request, id):
    """
    View detailed information for a specific order.

    Features:
    - Order timeline with status dates
    - Order items with quantities and prices
    - Automatic fallback dates for historical orders
    - Total amount validation and discrepancy detection

    Args:
        id (int): Order ID
    """
    try:
        seller = request.user.seller_details

        # Get order with related data
        order = get_object_or_404(
            Order.objects.select_related('user')
            .prefetch_related('items__product'),
            id=id,
            seller=seller
        )

        # Set fallback dates for timeline (historical accuracy)
        # Pending: Always fallback to order_date if null
        if not order.pending_date:
            order.pending_date = order.order_date
            order.save(update_fields=['pending_date'])

        # Processing: Set if status implies it happened (and null)
        if not order.processing_date and order.status in ['Processing', 'Shipped', 'Delivered']:
            order.processing_date = order.order_date
            order.save(update_fields=['processing_date'])

        # Shipped: Set if status implies it happened (and null)
        if not order.shipped_date and order.status in ['Shipped', 'Delivered']:
            order.shipped_date = order.order_date
            order.save(update_fields=['shipped_date'])

        # Delivered: Ensure if viewing Delivered status
        if not order.delivered_date and order.status == 'Delivered':
            order.delivered_date = order.order_date
            order.save(update_fields=['delivered_date'])

        # Get order items
        items = order.items.all()

        # Recalculate total amount
        order.total_amount = sum(item.unit_price * item.quantity for item in items)
        order.save(update_fields=['total_amount'])

        # Calculate total quantity
        total_quantity = items.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0

        # Calculate items total price
        calculated_items_total = sum(item.unit_price * item.quantity for item in items)

        # Check for discrepancies
        amount_difference = order.total_amount - calculated_items_total

        context = {
            "order": order,
            "items": items,
            "total_quantity": total_quantity,
            "calculated_items_total": calculated_items_total,
            "amount_difference": amount_difference,
            "has_discrepancy": abs(amount_difference) > 0.01,
        }

        return render(request, "seller/seller_order_product_detail.html", context)

    except Exception as e:
        return HttpResponse(f"Error: {e}")


@login_required
@seller_required
def update_order_status(request, id):
    """
    Update order status and timeline dates.

    Updates:
    - Order status (Pending/Processing/Shipped/Delivered)
    - Corresponding timeline dates (only sets once)

    Args:
        id (int): Order ID
    """
    if request.method == "POST":
        order = get_object_or_404(Order, id=id, seller=request.user.seller_details)
        new_status = request.POST.get("status")

        # Update status
        order.status = new_status

        # Update timeline dates (only set once per status)
        if new_status == "Processing" and not order.processing_date:
            order.processing_date = timezone.now()

        if new_status == "Shipped" and not order.shipped_date:
            order.shipped_date = timezone.now()

        if new_status == "Delivered" and not order.delivered_date:
            order.delivered_date = timezone.now()

        order.save()

        # Redirect back to order detail page
        return redirect("seller_order_view", id=id)

    # If GET request, redirect to order detail page
    return redirect("seller_order_view", id=id)


# ============================================================================
# AUTHENTICATION & REGISTRATION VIEWS
# ============================================================================

def seller_registration(request):
    """
    Register new seller account with business details.

    Creates:
    - User account with seller role
    - SellerDetails profile with business information

    Auto-logout: If authenticated user accesses this page, they are logged out
    """
    # Auto-logout if logged-in user opens this page
    if request.user.is_authenticated:
        logout(request)
        return redirect("login")

    if request.method == "POST":
        # Get user fields
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Get seller fields
        role = request.POST.get("role")
        shop_name = request.POST.get("shop_name")
        shop_address = request.POST.get("shop_address")
        business_type = request.POST.get("business_type")
        gst_number = request.POST.get("gst")
        bank_account = request.POST.get("bank_account")

        # Validate username uniqueness
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username {username} already exists")
            return render(request, "seller/seller_registration.html")

        # Validate email uniqueness
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists. Please login.")
            return redirect("login")

        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        # Create seller profile
        if role == "seller":
            SellerDetails.objects.create(
                user=user,
                shop_name=shop_name,
                shop_address=shop_address,
                business_type=business_type,
                gst_number=gst_number,
                bank_account=bank_account
            )

        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "seller/seller_registration.html")


def login_seller(request):
    """
    Authenticate and login seller users.

    Redirects:
    - Sellers to dashboard
    - Regular users to home page
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Check if user is a seller
            is_seller = SellerDetails.objects.filter(user=user).exists()
            if is_seller:
                return redirect('seller_dashboard')
            else:
                return redirect('home')

        return render(request, "seller/login.html", {
            "error": "Invalid username or password"
        })

    return render(request, "seller/login.html")


def logout_seller(request):
    """Logout current user and redirect to home page."""
    logout(request)
    return redirect('home')


# ============================================================================
# PROFILE & SETTINGS VIEWS
# ============================================================================

@login_required
@seller_required
def seller_profile_view(request):
    """
    View and edit seller profile information.

    Handles two forms:
    1. Business Information (shop details, GST, bank account)
    2. Password Change (with validation)
    """
    # Get or create seller details for the user
    seller, created = SellerDetails.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Handle business information update
        if form_type == 'business_info':
            seller.shop_name = request.POST.get('shop_name', '')
            seller.shop_address = request.POST.get('shop_address', '')
            seller.business_type = request.POST.get('business_type', '')
            seller.phone_number = request.POST.get('phone_number', '')
            seller.gst_number = request.POST.get('gst_number', '')
            seller.bank_account = request.POST.get('bank_account', '')

            try:
                seller.save()
                messages.success(request, 'Business information updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating business information: {str(e)}')

            return redirect('profile')

        # Handle password change
        elif form_type == 'change_password':
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            # Validate old password
            if not request.user.check_password(old_password):
                messages.error(request, 'Your current password was entered incorrectly.')
                return redirect('profile')

            # Check if new passwords match
            if new_password1 != new_password2:
                messages.error(request, 'The two new password fields didn\'t match.')
                return redirect('profile')

            # Validate new password strength
            try:
                validate_password(new_password1, request.user)
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
                return redirect('profile')

            # Set new password and keep user logged in
            request.user.set_password(new_password1)
            request.user.save()
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')

    context = {
        'seller': seller,
    }

    return render(request, 'seller/profile.html', context)


# ============================================================================
# SOCIAL AUTH & ROLE SELECTION VIEWS
# ============================================================================

@login_required(login_url="login")
def choose_role(request):
    """
    Role selection page after social authentication.

    Redirects existing users to their appropriate dashboard.
    Shows role selection for new social auth users.
    """
    user = request.user

    # Redirect existing customer
    if user.role == "customer" and hasattr(user, "customer"):
        return redirect("home")

    # Redirect existing seller
    if user.role == "seller" and hasattr(user, "sellerdetails"):
        return redirect("seller_dashboard")

    return render(request, "auth/choose_role.html", {"user": user})


@login_required
def complete_customer(request):
    """
    Complete customer profile after Google signup.

    Sets user role to customer and redirects to home page.
    """
    user = request.user
    user.role = "customer"
    user.save()

    # Later you can create a Customer profile here if needed
    return redirect("home")


@login_required
def complete_seller(request):
    """
    Complete seller profile after Google signup.

    Collects business information and creates SellerDetails profile.
    """
    user = request.user

    # Already a seller - just set role and redirect
    if hasattr(user, "seller_details"):
        user.role = "seller"
        user.save()
        return redirect("seller_dashboard")

    if request.method == "POST":
        shop_name = request.POST.get("shop_name")
        shop_address = request.POST.get("shop_address")
        business_type = request.POST.get("business_type")
        gst_number = request.POST.get("gst_number")
        bank_account = request.POST.get("bank_account")

        # Validate required fields
        if not shop_name:
            return render(request, "auth/seller_complete_form.html", {
                "error": "Shop name is required."
            })

        # Create seller profile
        SellerDetails.objects.create(
            user=user,
            shop_name=shop_name,
            shop_address=shop_address or "",
            business_type=business_type or "",
            gst_number=gst_number or "",
            bank_account=bank_account or "",
        )

        user.role = "seller"
        user.save()

        return redirect("seller_dashboard")

    # Prepopulate form with user data
    initial = {
        "shop_name": f"{user.first_name}'s Shop" if user.first_name else "",
        "email": user.email,
    }
    return render(request, "auth/seller_complete_form.html", {"initial": initial})


def social_signup_error(request):
    """
    Handle social signup errors (e.g., email already registered).
    """
    messages.error(request, "This email is already registered. Please login.")
    return redirect("login")


# ============================================================================
# ERROR & UTILITY VIEWS
# ============================================================================

def home(request):
    """Seller homepage/landing page."""
    return render(request, "seller/seller_home.html")


def not_seller(request):
    """Error page for non-sellers trying to access seller pages."""
    return HttpResponse("⛔ You are not allowed to access seller pages.")