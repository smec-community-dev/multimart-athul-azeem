import calendar
import csv
from django.core.paginator import Paginator
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q, CharField
from django.contrib.auth import get_user_model
from django.contrib import messages
from datetime import timedelta, timezone as dt_timezone, datetime

from core.models import SubCategory
from seller.models import SellerDetails, Product
from user.models import Order, Review

User = get_user_model()


# ============================================================================
# DASHBOARD
# ============================================================================

def dashboard(request):
    today = timezone.now()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_month_end.replace(day=1)

    def percent_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    # This month metrics
    users_this_month = User.objects.filter(date_joined__gte=first_day_this_month).count()
    orders_this_month = Order.objects.filter(order_date__gte=first_day_this_month).count()
    revenue_this_month = (
        Order.objects.filter(order_date__gte=first_day_this_month, status='Delivered')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    # Last month metrics
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

    # Overall totals
    total_users = User.objects.count()
    total_sellers = SellerDetails.objects.count()
    total_orders = Order.objects.count()
    total_revenue = (
        Order.objects.filter(status='Delivered')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )
    pending_orders = Order.objects.filter(status='Pending').count()

    # Latest orders
    latest_orders = (
        Order.objects.select_related('user', 'seller__user')
        .prefetch_related('items__product')
        .order_by('-order_date')[:10]
    )

    # Low stock products
    low_stock_products = (
        Product.objects.filter(stock__lte=5)
        .select_related('subcategory__category', 'subcategory', 'seller__user')
        .order_by('stock')[:10]
    )

    # Monthly revenue chart data
    monthly_revenue = []
    current_year = today.year
    for month in range(1, 13):
        start_date = timezone.datetime(current_year, month, 1, tzinfo=dt_timezone.utc)
        end_date = timezone.datetime(
            current_year + 1 if month == 12 else current_year,
            1 if month == 12 else month + 1,
            1,
            tzinfo=dt_timezone.utc
        )
        revenue = (
            Order.objects.filter(
                status='Delivered',
                order_date__gte=start_date,
                order_date__lt=end_date
            ).aggregate(total=Sum('total_amount'))['total'] or 0
        )
        monthly_revenue.append(float(revenue))

    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'users_growth': percent_change(users_this_month, users_last_month),
        'orders_growth': percent_change(orders_this_month, orders_last_month),
        'revenue_growth': percent_change(revenue_this_month, revenue_last_month),
        'latest_orders': latest_orders,
        'low_stock_products': low_stock_products,
        'month_labels': month_labels,
        'monthly_revenue': monthly_revenue,
    }

    return render(request, 'admin/dashboard.html', context)


# ============================================================================
# USERS MANAGEMENT
# ============================================================================

def users_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    users_qs = User.objects.all()

    if q:
        users_qs = users_qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if status == 'active':
        users_qs = users_qs.filter(is_blocked=False)
    elif status == 'blocked':
        users_qs = users_qs.filter(is_blocked=True)

    users = users_qs.order_by('-date_joined')

    context = {'users': users}
    return render(request, 'admin/users.html', context)


def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    orders = Order.objects.filter(user=user).order_by('-order_date')
    reviews = Review.objects.filter(user=user).order_by('-created_at')

    context = {
        'user': user,
        'orders': orders,
        'reviews': reviews,
    }
    return render(request, 'admin/user_detail.html', context)


def add_user(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'admin/add_user.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'admin/add_user.html')

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "User created successfully!")
        return redirect('admin_panel:admin_users')

    return render(request, 'admin/add_user.html')


def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "Superusers cannot be blocked!")
    elif user.role == 'admin':
        messages.error(request, "Admin accounts cannot be blocked!")
    else:
        user.is_blocked = True
        user.save()
        messages.success(request, f"User '{user.username}' has been blocked.")
    return redirect('admin_panel:admin_users')


def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_blocked = False
    user.save()
    messages.success(request, f"User '{user.username}' has been unblocked.")
    return redirect('admin_panel:admin_users')


def delete_user(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)

        if user.is_superuser:
            messages.error(request, "Superusers cannot be deleted!")
            return redirect('admin_panel:admin_users')

        if user.role == 'admin':
            messages.error(request, "Admin accounts cannot be deleted!")
            return redirect('admin_panel:admin_users')

        user.delete()
        messages.success(request, "User deleted successfully!")
        return redirect('admin_panel:admin_users')

    except User.DoesNotExist:
        messages.error(request, "User does not exist!")
        return redirect('admin_panel:admin_users')


# ============================================================================
# SELLERS MANAGEMENT
# ============================================================================

def sellers_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    sellers_qs = SellerDetails.objects.select_related('user').order_by('-user__date_joined')

    if q:
        sellers_qs = sellers_qs.filter(
            Q(user__username__icontains=q) |
            Q(shop_name__icontains=q) |
            Q(user__email__icontains=q)
        )

    if status == 'pending':
        sellers_qs = sellers_qs.filter(is_verified=False, user__is_blocked=False)
    elif status == 'approved':
        sellers_qs = sellers_qs.filter(is_verified=True, user__is_blocked=False)
    elif status == 'blocked':
        sellers_qs = sellers_qs.filter(user__is_blocked=True)

    context = {
        'sellers': sellers_qs,
        'search_query': q,
        'selected_status': status,
    }
    return render(request, 'admin/sellers.html', context)


def seller_detail(request, pk):
    seller = get_object_or_404(SellerDetails, id=pk)
    context = {'seller': seller}
    return render(request, 'admin/seller_detail.html', context)


def add_seller(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        shop_name = request.POST.get('shop_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()
        status = request.POST.get('status', 'Active').strip()
        profile_image = request.FILES.get('profile_image')

        errors = []
        if not all([username, email, password, shop_name, phone_number, address]):
            errors.append("All fields are required.")

        if User.objects.filter(username=username).exists():
            errors.append("Username already exists.")
        if User.objects.filter(email=email).exists():
            errors.append("Email already exists.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'admin/add_seller.html')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='seller',
                phone_number=phone_number,
                address=address,
                status=status,
                profile_image=profile_image if profile_image else None
            )

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
            return render(request, 'admin/add_seller.html')

    return render(request, 'admin/add_seller.html')


def block_seller_user(request, seller_id):
    seller = get_object_or_404(SellerDetails, id=seller_id)
    if request.method == 'POST':
        seller.user.is_blocked = True
        seller.user.save()
        messages.success(request, f"Seller '{seller.shop_name}' has been blocked.")
    return redirect('admin_panel:admin_sellers')


def unblock_seller_user(request, seller_id):
    seller = get_object_or_404(SellerDetails, id=seller_id)
    if request.method == 'POST':
        seller.user.is_blocked = False
        seller.user.save()
        messages.success(request, f"Seller '{seller.shop_name}' has been unblocked.")
    return redirect('admin_panel:admin_sellers')


def approve_seller(request, seller_id):
    seller = get_object_or_404(SellerDetails, id=seller_id)
    if request.method == 'POST':
        seller.is_verified = True
        seller.save()
        messages.success(request, f"Seller '{seller.shop_name}' has been approved.")
    return redirect('admin_panel:admin_sellers')


def delete_seller(request, seller_id):
    seller = get_object_or_404(SellerDetails, id=seller_id)
    if request.method == 'POST':
        seller_name = seller.shop_name
        user = seller.user
        seller.delete()
        user.delete()
        messages.success(request, f"Seller '{seller_name}' and account deleted successfully.")
        return redirect('admin_panel:admin_sellers')
    return redirect('admin_panel:admin_sellers')


# ============================================================================
# PRODUCTS MANAGEMENT
# ============================================================================

def products_list(request):
    all_products = Product.objects.all()
    paginator = Paginator(all_products, 10)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'products': products,
        'page_obj': products,
        'is_paginated': products.has_other_pages(),
    }
    return render(request, 'admin/products.html', context)


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = SubCategory.objects.all()

    if request.method == 'POST':
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price = request.POST.get('price', product.price)
        product.stock = request.POST.get('stock', product.stock)

        subcategory_id = request.POST.get('category')
        if subcategory_id:
            product.subcategory_id = subcategory_id

        try:
            product.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('admin_panel:admin_products')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')

    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories
    })


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_name = product.name
        try:
            product.delete()
            messages.success(request, f'Product "{product_name}" deleted successfully!')
            return redirect('admin_panel:admin_products')
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')

    return render(request, 'admin/delete_product.html', {'product': product})


# ============================================================================
# ORDERS MANAGEMENT
# ============================================================================
def orders_list(request):
    orders = Order.objects.select_related(
        "user",
        "seller__user"
    ).prefetch_related(
        "items__product"
    ).order_by("-order_date")

    # --------------------
    # SEARCH FIXED HERE
    # --------------------
    search_query = request.GET.get('search', '').strip()
    if search_query:
        orders = orders.annotate(
            id_str=Cast('id', CharField())
        ).filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(seller__user__username__icontains=search_query)
        )

    # --------------------
    # STATUS FILTER
    # --------------------
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(status=status_filter)

    # --------------------
    # PAGINATION
    # --------------------
    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    # Status dropdown values
    status_choices = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    context = {
        'orders': orders_page,
        'status_choices': status_choices,
        'current_status': status_filter,
        'search_query': search_query,
    }

    return render(request, "admin/orders.html", context)


def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all().select_related('product')

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        if new_status:
            order.status = new_status
            try:
                order.save()
                messages.success(request, f'Order status updated to {new_status}!')
                return redirect('admin_panel:admin_order_detail', order_id=order_id)
            except Exception as e:
                messages.error(request, f'Error updating order: {str(e)}')

    status_choices = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    context = {
        'order': order,
        'order_items': order_items,
        'status_choices': status_choices,
    }

    return render(request, 'admin/user_order_detail.html', context)


def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        order_id_display = order.id
        try:
            order.delete()
            messages.success(request, f'Order #{order_id_display} deleted successfully!')
            return redirect('admin_panel:admin_orders')
        except Exception as e:
            messages.error(request, f'Error deleting order: {str(e)}')

    return render(request, 'admin/delete_order_confirm.html', {'order': order})


def export_orders(request):
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order ID',
            'User',
            'Email',
            'Total Amount',
            'Status',
            'Order Date',
            'Number of Items'
        ])

        orders = Order.objects.all().select_related('user').prefetch_related('items')
        for order in orders:
            writer.writerow([
                f'ORD-{order.id}',
                order.user.username,
                order.user.email,
                f'${order.total_amount}',
                order.status.capitalize(),
                order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                order.items.count()
            ])

        return response

    except Exception as e:
        messages.error(request, f'Error exporting orders: {str(e)}')
        return redirect('admin_panel:admin_orders')


# ============================================================================
# REVIEWS MANAGEMENT
# ============================================================================

def reviews_list(request):
    reviews = Review.objects.select_related(
        'product__seller__user',
        'user',
        'product__subcategory__category'
    ).order_by('-created_at')
    context = {'reviews': reviews}
    return render(request, 'admin/reviews.html', context)