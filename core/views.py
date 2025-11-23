# admin_panel/views.py
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth import get_user_model
User = get_user_model()

from django.db.models import Sum

from seller.models import SellerDetails, Product
from user.models import Order, Review

def dashboard(request):
    total_users = User.objects.count()
    total_sellers = SellerDetails.objects.count()
    total_orders = Order.objects.count()

    total_revenue = (
        Order.objects.filter(status='Delivered')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    pending_orders = Order.objects.filter(status='Pending').count()

    latest_orders = (
        Order.objects.select_related('user')
        .order_by('-order_date')[:10]
    )

    low_stock_products = (
        Product.objects.filter(stock__lte=5)
        .select_related('subcategory__category', 'subcategory', 'seller__user')
        .order_by('stock')[:10]
    )

    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'latest_orders': latest_orders,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'admin/dashboard.html', context)


def users_list(request):
    users = User.objects.select_related().order_by('-date_joined')
    context = {'users': users}
    return render(request, 'admin/users.html', context)


def sellers_list(request):
    sellers = SellerDetails.objects.select_related('user').order_by('-user__date_joined')
    context = {'sellers': sellers}
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