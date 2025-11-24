import calendar
import csv

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q, CharField, F, Count

from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from datetime import timedelta, timezone as dt_timezone, datetime
from django.db import models

from core.models import SubCategory, Category
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
    """Display all products with search, filtering, and pagination"""
    products = Product.objects.select_related(
        'subcategory',
        'seller__user'
    ).prefetch_related(
        'images'
    ).order_by('-created_at')

    # Search by product name or category
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(subcategory__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by stock status
    stock_status_filter = request.GET.get('stock_status', '').strip()
    if stock_status_filter == 'in_stock':
        products = products.filter(stock__gt=5)
    elif stock_status_filter == 'low_stock':
        products = products.filter(stock__lte=5, stock__gt=0)
    elif stock_status_filter == 'out_of_stock':
        products = products.filter(stock=0)

    # Stock status choices for dropdown
    stock_status_choices = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    # Pagination
    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    # Calculate statistics
    total_products = Product.objects.count()
    in_stock_count = Product.objects.filter(stock__gt=5).count()
    low_stock_count = Product.objects.filter(stock__lte=5, stock__gt=0).count()

    # Calculate total inventory value (price * stock)
    inventory_data = Product.objects.aggregate(
        total=Sum(F('price') * F('stock'), output_field=models.DecimalField())
    )
    total_inventory_value = inventory_data['total'] or 0

    context = {
        'products': products_page,
        'stock_status_choices': stock_status_choices,
        'current_stock_status': stock_status_filter,
        'search_query': search_query,
        'total_products': total_products,
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'total_inventory_value': round(total_inventory_value, 2),
    }

    return render(request, 'admin/products.html', context)



def product_detail(request, product_id):
    """Display detailed product information"""
    product = get_object_or_404(
        Product.objects.select_related(
            'subcategory',
            'seller__user'
        ).prefetch_related(
            'images'
        ),
        id=product_id
    )

    # Get query parameters to preserve search/filter
    search_query = request.GET.get('search', '')
    current_stock_status = request.GET.get('stock_status', '')

    context = {
        'product': product,
        'search_query': search_query,
        'current_stock_status': current_stock_status,
    }

    return render(request, 'admin/product_detail.html', context)


def edit_product(request, product_id):
    """Edit a product"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        # Update product fields
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price = request.POST.get('price', product.price)
        product.stock = request.POST.get('stock', product.stock)

        try:
            product.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')

            # Preserve filter parameters when redirecting back
            redirect_url = 'admin_panel:admin_products'
            params = []
            if request.POST.get('search_query'):
                params.append(f'search={request.POST.get("search_query")}')
            if request.POST.get('current_stock_status'):
                params.append(f'stock_status={request.POST.get("current_stock_status")}')

            return redirect(f"{redirect_url}?{'&'.join(params)}" if params else redirect_url)
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')

    # Get query parameters to pass to template
    search_query = request.GET.get('search', '')
    current_stock_status = request.GET.get('stock_status', '')

    context = {
        'product': product,
        'search_query': search_query,
        'current_stock_status': current_stock_status,
    }

    return render(request, 'admin/edit_product.html', context)



def delete_product(request, product_id):
    """Delete a product"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_name = product.name
        try:
            product.delete()
            messages.success(request, f'Product "{product_name}" deleted successfully!')

            # Preserve filter parameters when redirecting back
            redirect_url = 'admin_panel:admin_products'
            params = []
            if request.POST.get('search_query'):
                params.append(f'search={request.POST.get("search_query")}')
            if request.POST.get('current_stock_status'):
                params.append(f'stock_status={request.POST.get("current_stock_status")}')

            return redirect(f"{redirect_url}?{'&'.join(params)}" if params else redirect_url)
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
            return redirect('admin_panel:admin_products')

    # Get query parameters to pass to confirmation page
    search_query = request.GET.get('search', '')
    current_stock_status = request.GET.get('stock_status', '')

    context = {
        'product': product,
        'search_query': search_query,
        'current_stock_status': current_stock_status,
    }

    return render(request, 'admin/delete_product_confirm.html', context)
# ============================================================================
# ORDERS MANAGEMENT
# ============================================================================

def orders_list(request):
    """Display all orders with search, filtering, and pagination"""
    orders = Order.objects.select_related(
        "user",
        "seller__user"
    ).prefetch_related(
        "items__product"
    ).order_by("-order_date")

    # Search by Order ID or Username
    search_query = request.GET.get('search', '').strip()
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Status choices for dropdown
    status_choices = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    # Pagination
    paginator = Paginator(orders, 15)  # 15 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    # Calculate statistics
    total_orders = Order.objects.count()
    delivered_count = Order.objects.filter(status='delivered').count()
    pending_count = Order.objects.filter(status='pending').count()
    total_revenue = (
        Order.objects.filter(status__iexact='Delivered')
        .aggregate(total=Sum('total_amount'))['total']
    )
    total_revenue = float(total_revenue) if total_revenue else 0

    context = {
        'orders': orders_page,
        'status_choices': status_choices,
        'current_status': status_filter,
        'search_query': search_query,
        'total_orders': total_orders,
        'delivered_count': delivered_count,
        'pending_count': pending_count,
        'total_revenue': round(total_revenue, 2),
    }

    return render(request, "admin/orders.html", context)



def order_detail(request, order_id):
    """Display detailed order information with status update"""
    order = get_object_or_404(
        Order.objects.select_related(
            "user",
            "seller__user"
        ).prefetch_related(
            "items__product"
        ),
        id=order_id
    )

    if request.method == 'POST':
        # Update order status
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

    # Get query parameters to preserve search/filter when going back
    search_query = request.GET.get('search', '')
    current_status = request.GET.get('status', '')

    context = {
        'order': order,
        'order_items': order.items.all(),
        'status_choices': status_choices,
        'search_query': search_query,
        'current_status': current_status,
    }

    return render(request, 'admin/order_details.html', context)



def delete_order(request, order_id):
    """Delete an order with confirmation"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        order_id_display = order.id
        try:
            order.delete()
            messages.success(request, f'Order #{order_id_display} deleted successfully!')

            # Preserve search/filter parameters when redirecting back
            redirect_url = 'admin_panel:admin_orders'
            search_query = request.POST.get('search_query', '')
            current_status = request.POST.get('current_status', '')

            if search_query or current_status:
                params = []
                if search_query:
                    params.append(f'search={search_query}')
                if current_status:
                    params.append(f'status={current_status}')
                return redirect(f"{redirect_url}?{'&'.join(params)}")

            return redirect(redirect_url)
        except Exception as e:
            messages.error(request, f'Error deleting order: {str(e)}')
            return redirect('admin_panel:admin_orders')

    # Get query parameters to pass to confirmation page
    search_query = request.GET.get('search', '')
    current_status = request.GET.get('status', '')

    context = {
        'order': order,
        'search_query': search_query,
        'current_status': current_status,
    }

    return render(request, 'admin/delete_order_confirm.html', context)



def export_orders(request):
    """Export orders to CSV file"""
    try:
        # Get filtered orders if filters are applied
        orders = Order.objects.select_related(
            "user",
            "seller__user"
        ).prefetch_related(
            "items__product"
        ).order_by("-order_date")

        search_query = request.GET.get('search', '').strip()
        if search_query:
            orders = orders.filter(
                Q(id__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )

        status_filter = request.GET.get('status', '').strip()
        if status_filter:
            orders = orders.filter(status=status_filter)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        filename = f'orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Write header
        writer.writerow([
            'Order ID',
            'User',
            'Email',
            'Total Amount',
            'Status',
            'Order Date',
            'Number of Items',
            'Seller'
        ])

        # Write data
        for order in orders:
            seller_name = order.seller.user.username if order.seller else 'N/A'
            writer.writerow([
                f'ORD-{order.id}',
                order.user.username,
                order.user.email,
                f'${order.total_amount}',
                order.status.capitalize(),
                order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                order.items.count(),
                seller_name
            ])

        return response

    except Exception as e:
        messages.error(request, f'Error exporting orders: {str(e)}')
        return redirect('admin_panel:admin_orders')

# ============================================================================
# REVIEWS MANAGEMENT
# ============================================================================



def reviews_list(request):
    """Display all reviews with search, filtering, and pagination"""
    reviews = Review.objects.select_related(
        'product',
        'user'
    ).order_by('-created_at')

    # Search by Product name or Username
    search_query = request.GET.get('search', '').strip()
    if search_query:
        reviews = reviews.filter(
            Q(product__name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(comment__icontains=search_query)
        )

    # Filter by rating
    rating_filter = request.GET.get('rating', '').strip()
    if rating_filter:
        try:
            rating = int(rating_filter)
            reviews = reviews.filter(rating=rating)
        except (ValueError, TypeError):
            pass

    # Filter by status (approved/pending)
    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)
    elif status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)

    # Rating choices for dropdown
    rating_choices = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    # Status choices for dropdown
    status_choices = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
    ]

    # Pagination
    paginator = Paginator(reviews, 20)  # 20 reviews per page
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    # Calculate statistics
    total_reviews = Review.objects.count()
    approved_count = Review.objects.filter(is_approved=True).count()
    pending_count = Review.objects.filter(is_approved=False).count()
    avg_rating = Review.objects.values('rating').aggregate(avg=models.Avg('rating'))['avg']

    context = {
        'reviews': reviews_page,
        'rating_choices': rating_choices,
        'status_choices': status_choices,
        'current_rating': rating_filter,
        'current_status': status_filter,
        'search_query': search_query,
        'total_reviews': total_reviews,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'avg_rating': round(avg_rating, 2) if avg_rating else 0,
    }

    return render(request, 'admin/reviews.html', context)



def review_detail(request, review_id):
    """Display detailed review information"""
    review = get_object_or_404(
        Review.objects.select_related('product', 'user'),
        id=review_id
    )

    # Get query parameters to preserve search/filter
    search_query = request.GET.get('search', '')
    current_rating = request.GET.get('rating', '')
    current_status = request.GET.get('status', '')

    context = {
        'review': review,
        'search_query': search_query,
        'current_rating': current_rating,
        'current_status': current_status,
    }

    return render(request, 'admin/review_detail.html', context)


def approve_review(request, review_id):
    """Approve a review"""
    review = get_object_or_404(Review, id=review_id)

    try:
        review.is_approved = True
        review.save()
        messages.success(request, f'Review for "{review.product.name}" has been approved!')
    except Exception as e:
        messages.error(request, f'Error approving review: {str(e)}')

    # Preserve filter parameters
    redirect_url = 'admin_panel:admin_reviews'
    params = []
    if request.GET.get('search'):
        params.append(f'search={request.GET.get("search")}')
    if request.GET.get('rating'):
        params.append(f'rating={request.GET.get("rating")}')
    if request.GET.get('status'):
        params.append(f'status={request.GET.get("status")}')
    if request.GET.get('page'):
        params.append(f'page={request.GET.get("page")}')

    return redirect(f"{redirect_url}?{'&'.join(params)}" if params else redirect_url)



def reject_review(request, review_id):
    """Reject/Unapprove a review"""
    review = get_object_or_404(Review, id=review_id)

    try:
        review.is_approved = False
        review.save()
        messages.success(request, f'Review for "{review.product.name}" has been rejected!')
    except Exception as e:
        messages.error(request, f'Error rejecting review: {str(e)}')

    # Preserve filter parameters
    redirect_url = 'admin_panel:admin_reviews'
    params = []
    if request.GET.get('search'):
        params.append(f'search={request.GET.get("search")}')
    if request.GET.get('rating'):
        params.append(f'rating={request.GET.get("rating")}')
    if request.GET.get('status'):
        params.append(f'status={request.GET.get("status")}')
    if request.GET.get('page'):
        params.append(f'page={request.GET.get("page")}')

    return redirect(f"{redirect_url}?{'&'.join(params)}" if params else redirect_url)



def delete_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(Review, id=review_id)

    if request.method == 'POST':
        product_name = review.product.name
        try:
            review.delete()
            messages.success(request, f'Review for "{product_name}" has been deleted!')

            # Preserve filter parameters
            redirect_url = 'admin_panel:admin_reviews'
            params = []
            if request.POST.get('search_query'):
                params.append(f'search={request.POST.get("search_query")}')
            if request.POST.get('current_rating'):
                params.append(f'rating={request.POST.get("current_rating")}')
            if request.POST.get('current_status'):
                params.append(f'status={request.POST.get("current_status")}')

            return redirect(f"{redirect_url}?{'&'.join(params)}" if params else redirect_url)
        except Exception as e:
            messages.error(request, f'Error deleting review: {str(e)}')
            return redirect('admin_panel:admin_reviews')

    # Get query parameters to pass to confirmation page
    search_query = request.GET.get('search', '')
    current_rating = request.GET.get('rating', '')
    current_status = request.GET.get('status', '')

    context = {
        'review': review,
        'search_query': search_query,
        'current_rating': current_rating,
        'current_status': current_status,
    }

    return render(request, 'admin/delete_review_confirm.html', context)

#Admin Profile#####################
@login_required(login_url='login')
def admin_profile(request):
    user = request.user
    return render(request, 'admin/profile.html', {'user': user})




def edit_profile(request):
    """Edit admin profile"""
    user = request.user

    if request.method == 'POST':
        # Update user information
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)

        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('admin_panel:admin_profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    context = {
        'user': user,
    }
    return render(request, 'admin/edit_profile.html', context)



def admin_settings(request):
    """Admin settings page"""
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.models import User

            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            # Validate old password
            if not user.check_password(old_password):
                messages.error(request, 'Old password is incorrect!')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match!')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters!')
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('admin_panel:admin_settings')

    context = {
        'user': user,
    }
    return render(request, 'admin/settings.html', context)



def admin_logout(request):
    """Logout admin user"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')

    return redirect('login')  # Redirect to login page



def help_center(request):
    """
    View for Help Center page.
    """
    return render(request, 'admin/help_center.html')


def contact_us(request):
    """
    View for Contact Us page.
    Handles form submission if needed.
    """
    if request.method == 'POST':
        # Process contact form (e.g., send email)
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Example: Send email (implement with Django's send_mail)
        # from django.core.mail import send_mail
        # send_mail(subject, message, email, ['admin@shophub.com'])

        messages.success(request, 'Your message has been sent! We\'ll get back to you soon.')
        return redirect('admin_panel:contact_us')

    return render(request, 'admin/contact_us.html')



def privacy_policy(request):
    """
    View for Privacy Policy page.
    """
    return render(request, 'admin/privacy_policy.html')



def terms_of_service(request):
    """
    View for Terms of Service page.
    """
    return render(request, 'admin/terms_of_service.html')


def feedback(request):
    """
    View for Feedback page.
    Handles form submission.
    """
    if request.method == 'POST':
        # Process feedback form
        rating = request.POST.get('rating', 0)
        category = request.POST.get('category')
        feedback_text = request.POST.get('feedback')

        # Example: Save to model or send email
        # Feedback.objects.create(user=request.user, rating=rating, category=category, text=feedback_text)

        messages.success(request, 'Thank you for your feedback! We appreciate it.')
        return redirect('admin_panel:feedback')

    return render(request, 'admin/feedback.html')


def admin_categories(request):
    """
    View to display all categories with search, filter, and pagination
    """
    categories = Category.objects.all().annotate(
        subcategory_count=Count('subcategories')
    )

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by status
    current_status = request.GET.get('status', '')
    if current_status == 'active':
        categories = categories.filter(status=True)
    elif current_status == 'inactive':
        categories = categories.filter(status=False)

    # Order by name
    categories = categories.order_by('name')

    # Pagination
    paginator = Paginator(categories, 10)  # 10 items per page
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    # Calculate statistics
    all_categories = Category.objects.all()
    total_categories = all_categories.count()
    active_categories = all_categories.filter(status=True).count()
    inactive_categories = all_categories.filter(status=False).count()
    total_subcategories = all_categories.annotate(
        subcategory_count=Count('subcategories')
    ).aggregate(total=Count('subcategories', distinct=True))['total'] or 0

    context = {
        'categories': categories,
        'search_query': search_query,
        'current_status': current_status,
        'total_categories': total_categories,
        'active_categories': active_categories,
        'inactive_categories': inactive_categories,
        'total_subcategories': total_subcategories,
    }

    return render(request, 'admin/category_list.html', context)

def admin_category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        status = 'status' in request.POST   # checkbox name must be "status"

        # 1️⃣ Name required
        if not name:
            messages.error(request, 'Name is required.')
            return render(request, 'admin/category_add.html')

        # 2️⃣ Duplicate category check (add this here)
        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, "Category with this name already exists.")
            return render(request, 'admin/category_add.html')

        # 3️⃣ Create category
        Category.objects.create(
            name=name,
            description=description,
            status=status
        )

        messages.success(request, 'Category added successfully.')
        return redirect('admin_panel:admin_categories')

    return render(request, 'admin/category_add.html')





def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        status = 'status' in request.POST  # use 'status' instead of is_active

        if not name:
            messages.error(request, 'Name is required.')
            return render(request, 'admin/category_edit.html', {'category': category})

        category.name = name
        category.description = description
        category.status = status  # corrected
        category.save()

        messages.success(request, 'Category updated successfully.')
        return redirect('admin_panel:admin_categories')

    return render(request, 'admin/category_edit.html', {'category': category})




def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        # Optional: Check if subcategories exist before delete
        if SubCategory.objects.filter(category=category).exists():
            messages.error(request, 'Cannot delete category with subcategories.')
            return redirect('admin_panel:admin_categories')
        category.delete()
        messages.success(request, 'Category deleted successfully.')
        return redirect('admin_panel:admin_categories')
    # For GET, render a simple confirm page (optional; create template or use inline)
    return render(request, 'admin/category_confirm_delete.html', {'category': category})



def admin_subcategories(request):
    subcategories = SubCategory.objects.select_related('category').all().order_by('name')
    paginator = Paginator(subcategories, 10)
    page_number = request.GET.get('page')
    subcategories = paginator.get_page(page_number)
    return render(request, 'admin/subcategory_list.html', {'subcategories': subcategories})



def admin_subcategory_add(request):
    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category_id')
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, 'Name is required.')
            return render(request, 'admin/subcategory_add.html', {'categories': categories})

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            messages.error(request, 'Invalid parent category.')
            return render(request, 'admin/subcategory_add.html', {'categories': categories})

        SubCategory.objects.create(
            name=name,
            category=category,
            description=description
        )

        messages.success(request, 'Subcategory added successfully.')
        return redirect('admin_panel:admin_subcategories')

    return render(request, 'admin/subcategory_add.html', {'categories': categories})



def admin_subcategory_edit(request, pk):
    subcategory = get_object_or_404(SubCategory, pk=pk)
    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category_id')
        description = request.POST.get('description', '').strip()
        status = 'status' in request.POST  # <-- ADD THIS

        if not name:
            messages.error(request, 'Name is required.')
            return render(request, 'admin/subcategory_edit.html', {
                'subcategory': subcategory,
                'categories': categories
            })

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            messages.error(request, 'Invalid parent category.')
            return render(request, 'admin/subcategory_edit.html', {
                'subcategory': subcategory,
                'categories': categories
            })

        subcategory.name = name
        subcategory.category = category
        subcategory.description = description
        subcategory.status = status  # <-- ADD THIS
        subcategory.save()

        messages.success(request, 'Subcategory updated successfully.')
        return redirect('admin_panel:admin_subcategories')

    return render(request, 'admin/subcategory_edit.html', {
        'subcategory': subcategory,
        'categories': categories
    })



def admin_subcategory_delete(request, pk):
    subcategory = get_object_or_404(SubCategory, pk=pk)
    if request.method == 'POST':
        subcategory.delete()
        messages.success(request, 'Subcategory deleted successfully.')
        return redirect('admin_panel:admin_subcategories')
    return render(request, 'admin/subcategory_confirm_delete.html', {'subcategory': subcategory})