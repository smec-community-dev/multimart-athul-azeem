# admin_panel/views.py
import calendar

from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import timedelta, timezone as dt_timezone
import calendar
from django.contrib.auth import get_user_model
User = get_user_model()

from django.contrib.auth import get_user_model
from seller.models import SellerDetails
from seller.models import Product
from user.models import Order, Review


def dashboard(request):
    today = timezone.now()

    # --- MONTH RANGE CALCULATIONS ---
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_month_end.replace(day=1)

    # --- CURRENT MONTH METRICS ---
    users_this_month = User.objects.filter(date_joined__gte=first_day_this_month).count()
    orders_this_month = Order.objects.filter(order_date__gte=first_day_this_month).count()
    revenue_this_month = (
        Order.objects.filter(order_date__gte=first_day_this_month, status='Delivered')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    # --- LAST MONTH METRICS ---
    users_last_month = User.objects.filter(
        date_joined__gte=first_day_last_month,
        date_joined__lt=first_day_this_month
    ).count()

    orders_last_month = Order.objects.filter(
        order_date__gte=first_day_last_month,
        order_date__lt=first_day_this_month
    ).count()

    revenue_last_month = (
        Order.objects.filter(
            order_date__gte=first_day_last_month,
            order_date__lt=first_day_this_month,
            status='Delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
    )

    # --- PERCENT GROWTH FUNCTION ---
    def percent_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    users_growth = percent_change(users_this_month, users_last_month)
    orders_growth = percent_change(orders_this_month, orders_last_month)
    revenue_growth = percent_change(revenue_this_month, revenue_last_month)

    # --- OVERALL TOTAL COUNTS ---
    total_users = User.objects.count()
    total_sellers = SellerDetails.objects.count()
    total_orders = Order.objects.count()
    total_revenue = (
        Order.objects.filter(status='Delivered')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )
    pending_orders = Order.objects.filter(status='Pending').count()

    # --- LATEST ORDERS FOR TABLE ---
    latest_orders = (
        Order.objects.select_related('user', 'seller__user')
        .prefetch_related('items__product')
        .order_by('-order_date')[:10]
    )

    # --- LOW STOCK PRODUCTS ---
    low_stock_products = (
        Product.objects.filter(stock__lte=5)
        .select_related('subcategory__category', 'subcategory', 'seller__user')
        .order_by('stock')[:10]
    )

    # --- MONTHLY REVENUE CHART DATA ---
    monthly_revenue = []
    current_year = today.year

    for month in range(1, 13):
        start_date = timezone.datetime(current_year, month, 1, tzinfo=dt_timezone.utc)

        if month == 12:
            end_date = timezone.datetime(current_year + 1, 1, 1, tzinfo=dt_timezone.utc)
        else:
            end_date = timezone.datetime(current_year, month + 1, 1, tzinfo=dt_timezone.utc)

        revenue = (
            Order.objects.filter(
                status='Delivered',
                order_date__gte=start_date,
                order_date__lt=end_date
            ).aggregate(total=Sum('total_amount'))['total'] or 0
        )

        monthly_revenue.append(float(revenue))

    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    # --- CONTEXT ---
    context = {
        # total stats
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,

        # growth metrics
        'users_growth': users_growth,
        'orders_growth': orders_growth,
        'revenue_growth': revenue_growth,

        # extra dashboard data
        'latest_orders': latest_orders,
        'low_stock_products': low_stock_products,

        # chart data
        'month_labels': month_labels,
        'monthly_revenue': monthly_revenue,
    }

    return render(request, 'admin/dashboard.html', context)


def users_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    users_qs = User.objects.all()

    if q:
        users_qs = users_qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if status == 'active':
        users_qs = users_qs.filter(is_blocked=False)
    elif status == 'blocked':
        users_qs = users_qs.filter(is_blocked=True)

    users = users_qs.select_related().order_by('-date_joined')  # Use users_qs here

    context = {'users': users}
    return render(request, 'admin/users.html', context)


def sellers_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')

    sellers_qs = SellerDetails.objects.select_related('user')

    # Search by seller name, shop name, or user email
    if q:
        sellers_qs = sellers_qs.filter(
            Q(user__username__icontains=q) |
            Q(shop_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    # Filter by status
    if status == 'pending':
        # Pending approval and not blocked
        sellers_qs = sellers_qs.filter(is_verified=False, user__is_blocked=False)

    elif status == 'approved':
        # Approved and not blocked
        sellers_qs = sellers_qs.filter(is_verified=True, user__is_blocked=False)

    elif status == 'blocked':
        # Blocked sellers
        sellers_qs = sellers_qs.filter(user__is_blocked=True)

    # Ordering
    sellers = sellers_qs.order_by('-user__date_joined')

    context = {
        'sellers': sellers,
        'search_query': q,
        'selected_status': status,
    }
    return render(request, 'admin/sellers.html', context)


def products_list(request):
    all_products = Product.objects.all()  # Your query

    # Paginate with 10 items per page (adjust as needed)
    paginator = Paginator(all_products, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'products': products,
        'page_obj': products,
        'is_paginated': products.has_other_pages(),
    }
    return render(request, 'admin/products.html', context)

def orders_list(request):
    orders = Order.objects.select_related(
        "user",
        "seller__user"
    ).prefetch_related(
        "items__product"
    ).order_by("-order_date")

    return render(request, "admin/orders.html", {"orders": orders})


def reviews_list(request):
    reviews = Review.objects.select_related('product__seller__user', 'user', 'product__subcategory__category').order_by('-created_at')
    context = {'reviews': reviews}
    return render(request, 'admin/reviews.html', context)

def block_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_blocked = True
    user.save()
    return redirect('admin_panel:admin_users')


def unblock_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_blocked = False
    user.save()
    return redirect('admin_panel:admin_users')
from django.contrib import messages

def delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)

        # --- SAFETY PROTECTIONS ---
        if user.is_superuser:
            messages.error(request, "Superusers cannot be deleted!")
            return redirect('admin_panel:admin_users')

        if user.role == 'admin':
            messages.error(request, "Admin accounts cannot be deleted!")
            return redirect('admin_panel:admin_users')

        # --- DELETE NORMAL USERS ---
        user.delete()
        messages.success(request, "User deleted successfully!")
        return redirect('admin_panel:admin_users')

    except User.DoesNotExist:
        messages.error(request, "User does not exist!")
        return redirect('admin_panel:admin_users')

def add_user(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return redirect('admin_panel:admin_users')

    return render(request, 'admin/add_user.html')

def user_detail(request, pk):
    # Get the user
    user = get_object_or_404(User, pk=pk)

    # Get all orders of this user - use order_date instead of created_at
    orders = Order.objects.filter(user=user).order_by('-order_date')

    # Get all reviews of this user - check if Review model has created_at or use a different field
    reviews = Review.objects.filter(user=user).order_by('-created_at')

    context = {
        'user': user,
        'orders': orders,
        'reviews': reviews,
    }

    return render(request, 'admin/user_detail.html', context)



def add_seller(request):
    if request.method == "POST":
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        shop_name = request.POST.get('shop_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()
        status = request.POST.get('status', 'Active').strip()
        profile_image = request.FILES.get('profile_image')

        # Validation checks
        errors = []

        # Check required fields
        if not username:
            errors.append("Username is required.")
        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        if not shop_name:
            errors.append("Shop name is required.")
        if not phone_number:
            errors.append("Phone number is required.")
        if not address:
            errors.append("Address is required.")

        # Check if errors exist
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('admin_panel:add_seller')

        # Check duplicate username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('admin_panel:add_seller')

        # Check duplicate email
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('admin_panel:add_seller')

        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )

            # Set seller-specific fields
            user.role = 'seller'
            user.phone_number = phone_number
            user.address = address
            user.status = status

            if profile_image:
                user.profile_image = profile_image

            user.save()

            # Create SellerDetails with REQUIRED fields
            SellerDetails.objects.create(
                user=user,
                shop_name=shop_name,
                shop_address=address,
                phone_number=phone_number
            )

            messages.success(request, f"Seller '{username}' created successfully!")
            return redirect('admin_panel:admin_sellers')

        except Exception as e:
            messages.error(request, f"Error creating seller: {str(e)}")
            return redirect('admin_panel:add_seller')

    return render(request, 'admin/add_seller.html')


def block_seller(request, seller_id):
    if request.method == 'POST':
        seller = get_object_or_404(SellerDetails, id=seller_id)
        seller.user.is_blocked = True
        seller.user.save()
    return redirect('admin_panel:admin_sellers')

def unblock_seller(request, seller_id):
    if request.method == 'POST':
        seller = get_object_or_404(SellerDetails, id=seller_id)
        seller.user.is_blocked = False
        seller.user.save()
    return redirect('admin_panel:admin_sellers')

def delete_seller(request, seller_id):
    if request.method == 'POST':
        seller = get_object_or_404(SellerDetails, id=seller_id)
        seller.user.delete()  # Deletes user and cascades to seller if set
    return redirect('admin_panel:admin_sellers')


def sellers_list(request):
    """Display list of sellers with filtering and search"""
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')

    sellers_qs = SellerDetails.objects.select_related('user').order_by('-user__date_joined')

    # Search by seller name, shop name, or user email
    if q:
        sellers_qs = sellers_qs.filter(
            Q(user__username__icontains=q) |
            Q(shop_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    # Filter by status
    if status == 'pending':
        sellers_qs = sellers_qs.filter(is_approved=False, user__is_blocked=False)
    elif status == 'approved':
        sellers_qs = sellers_qs.filter(is_approved=True, user__is_blocked=False)
    elif status == 'blocked':
        sellers_qs = sellers_qs.filter(user__is_blocked=True)

    context = {'sellers': sellers_qs}
    return render(request, 'admin/sellers.html', context)


def seller_detail(request, pk):
    """Display detailed information about a seller"""
    seller = get_object_or_404(SellerDetails, id=pk)
    context = {'seller': seller}
    return render(request, 'admin/seller_detail.html', context)


def block_seller_user(request, pk):
    """Block a seller's user account"""
    user = get_object_or_404(User, id=pk)

    if request.method == 'POST':
        user.is_blocked = True
        user.save()
        messages.success(request, f"Seller account '{user.username}' has been blocked successfully.")
        return redirect('admin_panel:admin_sellers')

    return redirect('admin_panel:admin_sellers')


def unblock_seller_user(request, pk):
    """Unblock a seller's user account"""
    user = get_object_or_404(User, id=pk)

    if request.method == 'POST':
        user.is_blocked = False
        user.save()
        messages.success(request, f"Seller account '{user.username}' has been unblocked successfully.")
        return redirect('admin_panel:admin_sellers')

    return redirect('admin_panel:admin_sellers')


def approve_seller(request, pk):
    """Approve a pending seller"""
    seller = get_object_or_404(SellerDetails, id=pk)

    seller.is_verified = True
    seller.save()
    messages.success(request, f"Seller '{seller.shop_name}' has been approved successfully.")
    # Redirect without filter to show the updated status
    return redirect('admin_panel:admin_sellers')


def delete_seller(request, pk):
    """Delete a seller and their account"""
    seller = get_object_or_404(SellerDetails, id=pk)
    seller_name = seller.shop_name
    user = seller.user

    if request.method == 'POST':
        seller.delete()
        user.delete()
        messages.success(request, f"Seller '{seller_name}' and associated account have been deleted successfully.")
        return redirect('admin_panel:admin_sellers')

    return redirect('admin_panel:admin_sellers')

def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    context = {'order': order}
    return render(request, 'admin/order_detail.html', context)
