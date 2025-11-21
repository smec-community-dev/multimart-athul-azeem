from django.core.checks import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import (
    Count, Sum, F, ExpressionWrapper, DecimalField, Q, Avg
)
from django.http import HttpResponse
from django.utils.text import slugify


# Project models
from core.models import User, SubCategory
from seller.decorators import seller_required
from seller.models import Product, SellerDetails, ProductImage
from user.models import Order, Review, OrderItem

from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce

from django.utils.timezone import now
from datetime import timedelta
@login_required
@seller_required
def view_product(request):
    seller = request.user.seller_details

    # -----------------------------
    # TOTAL REVENUE (ALL TIME)
    # -----------------------------
    total_revenue = (
        OrderItem.objects.filter(order__seller=seller, order__status='Delivered')
        .aggregate(total=Sum(F("unit_price") * F("quantity")))["total"]
        or 0
    )

    # -----------------------------
    # TOTAL ORDERS (ALL TIME)
    # -----------------------------
    total_orders = Order.objects.filter(seller=seller, status="Delivered").count()

    # -----------------------------
    # PRODUCTS COUNT
    # -----------------------------
    products_count = Product.objects.filter(seller=seller).count()

    # -----------------------------
    # PENDING PRODUCTS
    # -----------------------------
    pending_products = Product.objects.filter(seller=seller, stock__lte=0).count()

    # -----------------------------
    # RATINGS
    # -----------------------------
    rating_data = Review.objects.filter(product__seller=seller).aggregate(
        avg=Avg("rating"),
        count=Count("id")
    )
    avg_rating = rating_data["avg"] or 0
    rating_count = rating_data["count"]

    # -----------------------------
    # TODAY - YESTERDAY
    # -----------------------------
    today = now().date()
    yesterday = today - timedelta(days=1)

    today_revenue = (
        OrderItem.objects.filter(
            order__seller=seller,
            order__order_date__date=today,
            order__status='Delivered'
        ).aggregate(total=Sum(F("unit_price") * F("quantity")))["total"]
        or 0
    )

    yesterday_revenue = (
        OrderItem.objects.filter(
            order__seller=seller,
            order__order_date__date=yesterday,
            order__status='Delivered'
        ).aggregate(total=Sum(F("unit_price") * F("quantity")))["total"]
        or 0
    )

    revenue_growth = (
        ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
        if yesterday_revenue > 0 else 0
    )

    # -----------------------------
    # ORDERS TODAY VS YESTERDAY
    # -----------------------------
    today_orders = Order.objects.filter(
        seller=seller, order_date__date=today, status="Delivered"
    ).count()

    yesterday_orders = Order.objects.filter(
        seller=seller, order_date__date=yesterday, status="Delivered"
    ).count()

    orders_growth = (
        ((today_orders - yesterday_orders) / yesterday_orders) * 100
        if yesterday_orders > 0 else 0
    )

    new_orders_today = today_orders  # used in dashboard

    # -----------------------------
    # TOP SELLING PRODUCTS
    # -----------------------------
    completed_order_filter = Q(orderitem__order__status='Delivered')
    low_stock_threshold = 10

    top_low_stock_products = (
        Product.objects.filter(seller=seller, stock__lt=low_stock_threshold)
        .annotate(
            total_sold=Coalesce(
                Sum("orderitem__quantity", filter=completed_order_filter),
                Value(0),
                output_field=IntegerField()
            )
        )
        .order_by("-total_sold", "-created_at")[:3]
    )

    overall_top_qs = (
        Product.objects.filter(seller=seller)
        .annotate(
            total_sold=Coalesce(
                Sum("orderitem__quantity", filter=completed_order_filter),
                Value(0),
                output_field=IntegerField()
            )
        )
        .order_by("-total_sold", "-created_at")
    )

    top_products = list(top_low_stock_products)
    if len(top_products) < 3:
        excluded_ids = [p.id for p in top_products]
        fillers = overall_top_qs.exclude(id__in=excluded_ids)[:3 - len(top_products)]
        top_products += list(fillers)

    top_product = overall_top_qs.first()

    # -----------------------------
    # RECENT ORDERS
    # -----------------------------
    recent_orders = (
        Order.objects.filter(seller=seller)
        .select_related("user")
        .prefetch_related("items")
        .prefetch_related("items__product")
        .order_by("-order_date")[:4]
    )

    # -----------------------------
    # WEEKLY SALES CHART
    # -----------------------------
    last_week = today - timedelta(days=6)

    orders = Order.objects.filter(
        seller=seller,
        order_date__date__range=[last_week, today],
        status="Delivered"
    ).prefetch_related("items")

    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_data = {day: 0 for day in week_days}

    for order in orders:
        day = order.order_date.strftime("%a")
        total = sum(item.unit_price * item.quantity for item in order.items.all())
        week_data[day] += float(total)

    # Ordered output
    sales_labels = week_days
    sales_values = [week_data[d] for d in week_days]

    # Fallback if empty
    if not any(sales_values):
        sales_values = [0] * 7

    # -----------------------------
    # CONTEXT DATA
    # -----------------------------
    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "products_count": products_count,
        "pending_products": pending_products,

        "avg_rating": round(avg_rating, 1),
        "rating_count": rating_count,

        "today_revenue": today_revenue,
        "yesterday_revenue": yesterday_revenue,
        "revenue_growth": round(revenue_growth, 1),

        "today_orders": today_orders,
        "yesterday_orders": yesterday_orders,
        "orders_growth": round(orders_growth, 1),
        "new_orders_today": new_orders_today,

        "top_products": top_products,
        "top_product": top_product,

        "recent_orders": recent_orders,

        "sales_labels": sales_labels,
        "sales_values": sales_values,

        "low_stock_threshold": low_stock_threshold,
    }

    return render(request, "seller/sellerdashboard.html", context)




@login_required()
@seller_required
def add_product(request):
    if request.method == "POST":

        seller = SellerDetails.objects.get(user=request.user)
        print(seller)

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


        product = Product.objects.create(
            seller=seller,
            subcategory=subcategory,
            name=name,
            description=description,
            price=price,
            stock=stock,
            color=color,
            size=size
        )

        if main_image:
            ProductImage.objects.create(
                product=product,
                image=main_image,
                image_type="Main"
            )


        for img in  gallery_images:
            ProductImage.objects.create(
                product=product,
                image=img,
                image_type="Gallery"
            )

        return redirect("seller_dashboard")





    products = Product.objects.all()
    subcategories = SubCategory.objects.all()
    return render(request, "seller/features.html", {"subcategories": subcategories, "products": products})

@login_required()
@seller_required
def update_product(request, slug):
    product = get_object_or_404(Product, slug=slug)

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        product.color = request.POST.get("color")
        product.size = request.POST.get("size")
        product.subcategory_id = request.POST.get("subcategory")

        # Update slug if name changed
        new_name = request.POST.get("name")
        if new_name != product.name:
            product.slug = None  # regenerate
            product.name = new_name

        if "main_image" in request.FILES:
            ProductImage.objects.create(
                product=product,
                image=request.FILES["main_image"],
                image_type="Main"
            )

        if "gallery_images" in request.FILES:
            for img in request.FILES.getlist("gallery_images"):
                ProductImage.objects.create(product=product, image=img, image_type="Gallery")

        product.save()

        return redirect("add")

    return render(request, "seller/update_product.html", {"product": product})



@login_required()
@seller_required
def delete_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    product.delete()
    return redirect("add")




def seller_registration(request):
    if request.method=="POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        role = request.POST.get("role")
        shop_name = request.POST.get("shop_name")
        shop_address = request.POST.get("shop_address")
        business_type = request.POST.get("business_type")
        gst_number = request.POST.get("gst_number")
        bank_account = request.POST.get("bank_account")


        if User.objects.filter(username=username).exists():
            messages.error(request, f" username {username} already exists")
            return render(request, "seller/seller_registration.html")

        user=User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role


        )
        SellerDetails.objects.create(
            user=user,
            shop_name=shop_name,
            shop_address=shop_address,
            business_type=business_type,
            gst_number=gst_number,
            bank_account=bank_account
        )

        messages.success(request, "Registration successful! Please log in.")
        return redirect('seller/login')






    return render(request,"seller/seller_registration.html")




@login_required()
@seller_required
def order_product(request):
    seller = getattr(request.user, "seller_details", None)
    search = request.GET.get("search", "").strip()

    if not seller:
        return HttpResponse("You are not a seller")

    orders = (
        Order.objects.filter(seller=seller)
        .prefetch_related("items", "items__product")
        .annotate(
            items_count=Count("items"),
            total_price=Sum(F("items__unit_price") * F("items__quantity"))
        )
    )
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(items__product__name__icontains=search)
        ).distinct()

    # Get status filter from URL query parameter
    status = request.GET.get('status', None)

    # Filter by status if provided
    if status and status != 'all':
        orders = orders.filter(status=status.capitalize())

    notification_count = Order.objects.filter(seller=seller, status='Pending').count()

    return render(
        request,
        "seller/seller_order.html",
        {
            "orders": orders,
            "notification_count": notification_count,
            "current_status": status if status else 'all'
        }
    )


@seller_required
@login_required
def order_detail(request, id):
    try:
        seller = request.user.seller_details

        # Get order with related data
        order = get_object_or_404(
            Order.objects.select_related('user')
            .prefetch_related('items__product'),
            id=id,
            seller=seller
        )

        # Get order items with calculated totals
        items = order.items.select_related('product').annotate(
            item_total=ExpressionWrapper(
                F('unit_price') * F('quantity'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )

        # Calculate totals
        total_quantity = items.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0

        # Calculate items total (sum of all item totals)
        calculated_items_total = sum(
            item.unit_price * item.quantity for item in items
        )

        # Calculate the difference to understand the discrepancy
        amount_difference = order.total_amount - calculated_items_total

        # Debug information (you can remove this in production)
        print(f"Order ID: {order.id}")
        print(f"Database Total: {order.total_amount}")
        print(f"Calculated Items Total: {calculated_items_total}")
        print(f"Difference: {amount_difference}")
        print(f"Total Quantity: {total_quantity}")

        context = {
            "order": order,
            "items": items,
            "total_quantity": total_quantity,
            "calculated_items_total": calculated_items_total,
            "amount_difference": amount_difference,
            "has_discrepancy": abs(amount_difference) > 0.01,  # More than 1 paisa difference
        }

        return render(request, "seller/seller_order_product_detail.html", context)

    except Exception as e:
        # Log the error for debugging
        print(f"Error in order_detail view: {str(e)}")
        return render(request, 'error.html', {'error': str(e)})

def login_seller(request):
    if request.method =="POST":
        username=request.POST.get("username")
        password=request.POST.get("password")
        print(username,password)


        user=authenticate(request,username=username,password=password)
        print(user)
        if user is not None:
            login(request, user)

            is_seller=SellerDetails.objects.filter(user=user).exists()
            if is_seller:
                print(".............")
                return redirect('seller_dashboard')

            else:
                return redirect('home')
        return render(request,"seller/login.html",{"error":"invalid username or password"})
    return render(request,"seller/login.html")

def logout_seller(request):
    logout(request)
    return redirect('home')


def home(request):
    return render(request,"seller/seller_home.html")



@login_required()
@seller_required
def seller_profile_view(request):
    # Get or create seller details for the user
    seller, created = SellerDetails.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'business_info':
            # Handle business information form
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

        elif form_type == 'change_password':
            # Handle password change form
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

            # Validate new password
            try:
                validate_password(new_password1, request.user)
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
                return redirect('profile')

            # Set new password
            request.user.set_password(new_password1)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Important to keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')

    context = {
        'seller': seller,
    }

    return render(request, 'seller/profile.html', context)


def not_seller(request):
    return HttpResponse("⛔ You are not allowed to access seller pages.")


def update_order_status(request, id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=id)
        order.status = "Delivered"
        order.save()
    return redirect("seller_dashboard")



@login_required()
@seller_required
def product_details(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        seller=request.user.seller_details
    )

    reviews = (
        Review.objects.filter(product=product)
        .select_related("user")
        .order_by("-created_at")
    )

    avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    order_items = OrderItem.objects.filter(product=product)

    total_quantity_sold = (
        order_items.aggregate(q=Sum("quantity"))["q"] or 0
    )

    order_count = order_items.values("order").distinct().count()

    return render(
        request,
        "seller/seller_product_details.html",
        {
            "product": product,
            "reviews": reviews,
            "avg_rating": round(avg_rating, 1),
            "total_quantity_sold": total_quantity_sold,
            "order_count": order_count,
        }
    )







