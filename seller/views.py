import os
import time
import json
import csv
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils.text import slugify
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods
from django.db.models import (
    Count, Sum, F, ExpressionWrapper, DecimalField, Q, Avg, Value, IntegerField
)
from django.db.models.functions import Coalesce

# Project Models & Utils
from core.models import User, SubCategory, Category
from core.views import redirect_role_dashboard
from seller.decorators import seller_required
from seller.models import Product, SellerDetails, ProductImage
from user.models import Order, Review, OrderItem


@login_required
@seller_required
def view_product(request):
    seller = request.user.seller_details

    total_revenue = (
        OrderItem.objects.filter(order__seller=seller)
        .aggregate(total=Sum(F("unit_price") * F("quantity")))["total"]
        or 0
    )

    total_orders = Order.objects.filter(seller=seller).count()

    products_count = Product.objects.filter(seller=seller).count()

    pending_products = 0  # TODO: Implement if needed

    rating_data = Review.objects.filter(product__seller=seller).aggregate(
        avg=Avg("rating"),
        count=Count("id")
    )

    avg_rating = rating_data["avg"] or 0
    rating_count = rating_data["count"]

    # Low stock threshold (customize based on your business logic)
    low_stock_threshold = 10

    # First, try to get top products with low stock
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

    # Unsliced queryset for overall top to allow further filtering
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
    top_products = list(top_low_stock_products)  # Convert to list early to avoid issues
    if len(top_products) < 3:
        # Exclude already included low-stock ones to avoid duplicates
        excluded_ids = [p.id for p in top_products]
        fillers = overall_top_qs.exclude(id__in=excluded_ids)[:3 - len(top_products)]
        top_products += list(fillers)

    recent_orders = (
        Order.objects.filter(seller=seller)
        .select_related("user")
        .prefetch_related("items")
        .prefetch_related("items__product")
        .order_by("-order_date")[:4]
    )
    today = now().date()
    last_week = today - timedelta(days=6)

    orders = Order.objects.filter(
        seller=seller,
        order_date__date__range=[last_week, today]
    ).prefetch_related("items")

    # Mon-Sun format
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


def sanitize_filename(filename):
    """Sanitize filename: remove invalid chars, limit length, add timestamp."""
    base, ext = os.path.splitext(filename)
    # Remove invalid chars (Windows/Linux safe: alnum, space, -, _ only)
    base = ''.join(c for c in base if c.isalnum() or c in (' ', '-', '_')).rstrip()
    # Limit length
    if len(base) > 100:
        base = base[:100]
    # Add timestamp to avoid collisions
    timestamp = int(time.time())
    return f"{base}_{timestamp}{ext}"

@login_required()
@seller_required
def add_product(request):
    seller = SellerDetails.objects.get(user=request.user)

    if request.method == "POST":
        seller = SellerDetails.objects.get(user=request.user)

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
        print(subcategory)

        product = Product.objects.create(
            seller=seller,
            subcategory=subcategory,
            name=name,
            description=description,
            price=price,
            stock=stock,
            color=color,
            size=size,
            slug=slugify(name)  # Ensure slug is set
        )

        # Sanitize and save main image
        if main_image:
            sanitized_filename = sanitize_filename(main_image.name)
            main_image.name = sanitized_filename
            ProductImage.objects.create(
                product=product,
                image=main_image,
                image_type="Main"
            )

        # Sanitize and save gallery images
        for img in gallery_images:
            sanitized_filename = sanitize_filename(img.name)
            img.name = sanitized_filename
            ProductImage.objects.create(
                product=product,
                image=img,
                image_type="Gallery"
            )

        return redirect("seller:seller_dashboard")



    # GET request - handle filtering and pagination
    products_qs = Product.objects.filter(seller=seller).order_by('-id')

    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        products_qs = products_qs.filter(name__icontains=search)

    # Category filter (assuming Category exists and SubCategory has category field)
    category_id = request.GET.get('category')
    if category_id:
        products_qs = products_qs.filter(subcategory__category_id=category_id)

    # Status filter based on stock
    status = request.GET.get('status')
    if status == 'active':
        products_qs = products_qs.filter(stock__gt=10)
    elif status == 'low_stock':
        products_qs = products_qs.filter(stock__gt=0, stock__lte=10)
    elif status == 'out_of_stock':
        products_qs = products_qs.filter(stock__lte=0)

    # Pagination
    paginator = Paginator(products_qs, 10)  # Show 10 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    # For filter display
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

    subcategories = SubCategory.objects.all()
    return render(request, "seller/update_product.html", {"product": product, "subcategories": subcategories})



@login_required()
@seller_required
def delete_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    product.delete()
    return redirect("add")



def seller_registration(request):
    if request.method == "POST":

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        role = request.POST.get("role")

        shop_name = request.POST.get("shop_name")
        shop_address = request.POST.get("shop_address")
        business_type = request.POST.get("business_type")
        gst_number = request.POST.get("gst")
        bank_account = request.POST.get("bank_account")

        # Username already exists?
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists")
            return render(request, "seller/registration.html", {"filled": request.POST})

        # Email already exists?
        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered. Please login.")
            return render(request, "seller/registration.html", {"filled": request.POST})

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
        SellerDetails.objects.create(
            user=user,
            shop_name=shop_name,
            shop_address=shop_address,
            business_type=business_type,
            gst_number=gst_number,
            bank_account=bank_account
        )

        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')

    return render(request, "seller/registration.html")








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
            total_price=Sum(F("items__unit_price") * F("items__quantity")),
            total_qty=Sum("items__quantity")  # ADD THIS LINE
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

    # DEBUG: Print order count
    print(f"DEBUG: Total orders for this seller: {orders.count()}")
    print(f"DEBUG: Seller: {seller}")

    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # DEBUG: Print pagination info
    print(f"DEBUG: Total pages: {page_obj.paginator.num_pages}")
    print(f"DEBUG: Current page: {page_obj.number}")
    print(f"DEBUG: Orders on this page: {len(page_obj.object_list)}")

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
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
# Assume @seller_required is custom decorator

# ... (other imports/models)

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

        # Fallbacks: Set null dates for past/completed steps to order_date (historical accuracy)
        # Pending: Always fallback to order_date if null
        if not order.pending_date:
            order.pending_date = order.order_date
            order.save(update_fields=['pending_date'])

        # Processing: Set if status implies it happened (and null)
        if not order.processing_date and order.status in ['Processing', 'Shipped', 'Delivered']:
            order.processing_date = order.order_date  # Fallback to order_date for past step
            order.save(update_fields=['processing_date'])

        # Shipped: Set if status implies it happened (and null)
        if not order.shipped_date and order.status in ['Shipped', 'Delivered']:
            order.shipped_date = order.order_date  # Fallback to order_date for past step
            order.save(update_fields=['shipped_date'])

        # Delivered: Already handled in update, but ensure if viewing Delivered
        if not order.delivered_date and order.status == 'Delivered':
            order.delivered_date = order.order_date  # Rare, but fallback
            order.save(update_fields=['delivered_date'])

        # Get order items
        items = order.items.all()

        # Recalculate total amount
        order.total_amount = sum(item.unit_price * item.quantity for item in items)
        order.save(update_fields=['total_amount'])

        # Total quantity
        total_quantity = items.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0

        # Items total price
        calculated_items_total = sum(item.unit_price * item.quantity for item in items)

        # Difference check
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


@seller_required
@login_required
def update_order_status(request, id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=id, seller=request.user.seller_details)
        new_status = request.POST.get("status")

        # Update status
        order.status = new_status

        # Update timeline dates once (with current time for new steps)
        if new_status == "Processing" and not order.processing_date:
            order.processing_date = timezone.now()

        if new_status == "Shipped" and not order.shipped_date:
            order.shipped_date = timezone.now()

        if new_status == "Delivered" and not order.delivered_date:
            order.delivered_date = timezone.now()

        order.save()

        # Redirect back to the order detail page (re-triggers fallbacks for past)
        return redirect("seller_order_view", id=id)

    # If GET request, redirect to order detail page
    return redirect("seller_order_view", id=id)




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

            return redirect('seller:profile')

        elif form_type == 'change_password':
            # Handle password change form
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            # Validate old password
            if not request.user.check_password(old_password):
                messages.error(request, 'Your current password was entered incorrectly.')
                return redirect('seller:profile')

            # Check if new passwords match
            if new_password1 != new_password2:
                messages.error(request, 'The two new password fields didn\'t match.')
                return redirect('seller:profile')

            # Validate new password
            try:
                validate_password(new_password1, request.user)
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
                return redirect('seller:profile')

            # Set new password
            request.user.set_password(new_password1)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Important to keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('seller:profile')
    context = {
        'seller': seller,
    }

    return render(request, 'seller/profile.html', context)


def not_seller(request):
    return HttpResponse("⛔ You are not allowed to access seller pages.")

@login_required()
@seller_required
def product_details(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        seller=request.user.seller_details
    )

    # Get all subcategories for the dropdown
    subcategories = SubCategory.objects.all()

    # Fetch reviews
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


# views.py


# views.py - Review Dashboard (Compatible with your Review model)









@login_required
@seller_required
def review_dashboard(request):
    # -------------------- YOUR FULL DASHBOARD LOGIC (UNCHANGED) --------------------
    try:
        seller = SellerDetails.objects.get(user=request.user)
    except SellerDetails.DoesNotExist:
        return redirect('seller_login')

    seller_products = Product.objects.filter(seller=seller)

    all_reviews = Review.objects.filter(
        product__in=seller_products
    ).select_related('product', 'user').order_by('-created_at')
    # ==================== FILTERING & SEARCHING ====================
    search_query = request.GET.get('search', '').strip()
    rating_filter = request.GET.get('rating', '')  # Keep as string
    product_filter = request.GET.get('product', '')  # Keep as string
    sort_by = request.GET.get('sort', 'newest')

    filtered_reviews = all_reviews

    # Search filter - search in comment and user info
    if search_query:
        filtered_reviews = filtered_reviews.filter(
            Q(comment__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    # Rating filter - convert to int ONLY for the query
    if rating_filter:
        try:
            rating_int = int(rating_filter)
            if 1 <= rating_int <= 5:
                filtered_reviews = filtered_reviews.filter(rating=rating_int)
            else:
                rating_filter = ''
        except (ValueError, TypeError):
            rating_filter = ''

    # Product filter - convert to int ONLY for the query
    if product_filter:
        try:
            product_int = int(product_filter)
            filtered_reviews = filtered_reviews.filter(product_id=product_int)
        except (ValueError, TypeError):
            product_filter = ''

    # Sorting
    if sort_by == 'oldest':
        filtered_reviews = filtered_reviews.order_by('created_at')
    elif sort_by == 'highest':
        filtered_reviews = filtered_reviews.order_by('-rating')
    elif sort_by == 'lowest':
        filtered_reviews = filtered_reviews.order_by('rating')
    else:  # newest (default)
        filtered_reviews = filtered_reviews.order_by('-created_at')
        sort_by = 'newest'

    paginator = Paginator(filtered_reviews, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    query_params = []
    if search_query:
        query_params.append(f'search={search_query}')
    if rating_filter:
        query_params.append(f'rating={rating_filter}')
    if product_filter:
        query_params.append(f'product={product_filter}')
    if sort_by != 'newest':
        query_params.append(f'sort={sort_by}')

    query_string = '&'.join(query_params)

    total_reviews = all_reviews.count()
    average_rating = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    unique_reviewers = all_reviews.values('user').distinct().count()
    products_reviewed = all_reviews.values('product').distinct().count()

    star_distribution = {}
    for star in range(1, 6):
        count = all_reviews.filter(rating=star).count()
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        star_distribution[star] = {
            'count': count,
            'percentage': round(percentage, 1)
        }

    top_highest_rated = seller_products.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).filter(review_count__gt=0).order_by('-avg_rating')[:5]

    top_highest_rated = [
        {
            'name': product.name,
            'rating': round(product.avg_rating, 1) if product.avg_rating else 0
        }
        for product in top_highest_rated
    ]

    top_most_reviewed = seller_products.annotate(
        review_count=Count('review')
    ).filter(review_count__gt=0).order_by('-review_count')[:5]

    top_most_reviewed = [
        {'name': product.name, 'count': product.review_count}
        for product in top_most_reviewed
    ]

    lowest_rated = seller_products.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    ).filter(review_count__gt=0).order_by('avg_rating')[:5]

    lowest_rated = [
        {
            'name': product.name,
            'rating': round(product.avg_rating, 1) if product.avg_rating else 0
        }
        for product in lowest_rated
    ]

    positive_reviews = all_reviews.filter(rating__gte=4).count()
    negative_reviews = all_reviews.filter(rating__lte=2).count()

    positive_sentiment = int((positive_reviews / total_reviews * 100)) if total_reviews > 0 else 0
    negative_sentiment = int((negative_reviews / total_reviews * 100)) if total_reviews > 0 else 0
    positive_impact = round((positive_reviews / total_reviews * 100)) if total_reviews > 0 else 0

    repeat_customers = all_reviews.values('user').annotate(
        review_count=Count('id')
    ).filter(review_count__gt=1).count()

    also_ordered_count = repeat_customers
    response_time = "2-3 hours"
    influenced_sales = positive_sentiment

    reviews_for_template = []
    for review in page_obj:
        customer_review_count = all_reviews.filter(user=review.user).count()
        is_repeat = customer_review_count > 1

        reviews_for_template.append({
            'id': review.id,
            'customer_name': review.user.get_full_name() or review.user.username,
            'customer_username': review.user.username,
            'rating': review.rating,
            'comment': review.comment[:100] + '...' if len(review.comment) > 100 else review.comment,
            'comment_full': review.comment,
            'product_name': review.product.name,
            'product_id': review.product.id,
            'date': review.created_at,
            'is_repeat_customer': is_repeat,
            'times_range': range(review.rating),
            'empty_stars_range': range(5 - review.rating),
        })

    most_reviewed_products = seller_products.annotate(
        review_count=Count('review')
    ).filter(review_count__gt=0).order_by('-review_count')[:5]

    most_reviewed_chart_labels = [p.name[:15] for p in most_reviewed_products]
    most_reviewed_chart_data = [p.review_count for p in most_reviewed_products]

    monthly_data = {}
    today = timezone.now()

    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_key = month_date.strftime('%Y-%m')
        monthly_data[month_key] = 0

    for review in all_reviews:
        month_key = review.created_at.strftime('%Y-%m')
        if month_key in monthly_data:
            monthly_data[month_key] += 1

    monthly_labels = list(monthly_data.keys())
    monthly_values = list(monthly_data.values())

    rating_dist_labels = ['5 Stars', '4 Stars', '3 Stars', '2 Stars', '1 Star']
    rating_dist_data = [
        all_reviews.filter(rating=5).count(),
        all_reviews.filter(rating=4).count(),
        all_reviews.filter(rating=3).count(),
        all_reviews.filter(rating=2).count(),
        all_reviews.filter(rating=1).count(),
    ]

    repeat_reviewer_names = list(
        Review.objects
        .filter(product__in=seller_products)
        .values(username=F("user__username"))
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .values_list("username", flat=True)[:5]
    )

    positive_customers = list(
        Review.objects
        .filter(product__in=seller_products, rating__gte=4)
        .values_list("user__username", flat=True)
        .distinct()[:5]
    )

    negative_customers = list(
        Review.objects
        .filter(product__in=seller_products, rating__lte=2)
        .values_list("user__username", flat=True)
        .distinct()[:5]
    )

    context = {
        'seller': seller,
        'reviews': reviews_for_template,
        'page_obj': page_obj,
        'paginator': paginator,

        'rating_avg': round(average_rating, 1),
        'total_reviews': total_reviews,
        'unique_reviewers': unique_reviewers,
        'products_reviewed': products_reviewed,

        'star_distribution': star_distribution,

        'top_highest_rated': top_highest_rated,
        'top_most_reviewed': top_most_reviewed,
        'lowest_rated': lowest_rated,

        'positive_sentiment': positive_sentiment,
        'negative_sentiment': negative_sentiment,
        'positive_impact': positive_impact,
        'influenced_sales': influenced_sales,
        'response_time': response_time,
        'also_ordered_count': also_ordered_count,

        'products': seller_products.values('id', 'name')[:20],

        'most_reviewed_chart_labels': json.dumps(most_reviewed_chart_labels),
        'most_reviewed_chart_data': json.dumps(most_reviewed_chart_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_values': json.dumps(monthly_values),
        'rating_dist_labels': json.dumps(rating_dist_labels),
        'rating_dist_data': json.dumps(rating_dist_data),

        'search_query': search_query,
        'rating_filter': rating_filter,
        'product_filter': product_filter,
        'sort_by': sort_by,
        'query_string': query_string,

        'repeat_reviewer_names': repeat_reviewer_names,
        'positive_customers': positive_customers,
        'negative_customers': negative_customers,
    }

    return render(request, 'seller/seller_review.html', context)


@login_required
@seller_required
@require_http_methods(["POST"])
def delete_review(request, review_id):
    try:
        seller = SellerDetails.objects.get(user=request.user)
    except SellerDetails.DoesNotExist:
        return JsonResponse({'error': 'Seller not found'}, status=403)

    try:
        review = Review.objects.get(id=review_id, product__seller=seller)
    except Review.DoesNotExist:
        return JsonResponse({'error': 'Review not found or unauthorized'}, status=404)

    review.delete()
    return JsonResponse({'success': True, 'message': 'Review deleted successfully'})


@login_required
@seller_required
def download_reviews_csv(request):
    try:
        seller = SellerDetails.objects.get(user=request.user)
    except SellerDetails.DoesNotExist:
        return redirect('admin_panel:login')

    seller_products = Product.objects.filter(seller=seller)
    all_reviews = Review.objects.filter(
        product__in=seller_products
    ).select_related('product', 'user').order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reviews_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Customer', 'Rating', 'Review', 'Product', 'Date'])

    for review in all_reviews:
        writer.writerow([
            review.user.get_full_name() or review.user.username,
            review.rating,
            review.comment,
            review.product.name,
            review.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response
@login_required
@seller_required
def review_analytics(request):
    """
    Review analytics page (non-API version)
    """
    try:
        seller = SellerDetails.objects.get(user=request.user)
    except SellerDetails.DoesNotExist:
        return redirect('admin_panel:ogin')

    seller_products = Product.objects.filter(seller=seller)
    all_reviews = Review.objects.filter(product__in=seller_products)

    total_reviews = all_reviews.count()
    average_rating = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    # Star count distribution
    star_data = {}
    for star in range(1, 6):
        star_data[star] = all_reviews.filter(rating=star).count()

    context = {
        "total_reviews": total_reviews,
        "average_rating": round(average_rating, 1),
        "star_distribution": star_data,
        "seller": seller
    }

    return render(request, "seller/review_analytics.html", context)


# ============================================================================
# SOCIAL AUTH & ROLE SELECTION VIEWS
# ============================================================================
@login_required
def choose_role(request):
    # If user already has a role, skip selection
    if request.user.role and request.user.role != "user":
        return redirect_role_dashboard(request.user.role)

    if request.method == "POST":
        selected_role = request.POST.get("role")

        if selected_role not in ["user", "seller", "admin"]:
            messages.error(request, "Invalid role selected.")
            return redirect("seller:choose_role")

        request.user.role = selected_role
        request.user.save()

        return redirect("complete_registration")

    return render(request, "auth/choose_role.html")

@login_required
def complete_registration(request):
    role = request.user.role

    if request.method == "POST":
        if role == "seller":
            SellerDetails.objects.create(
                user=request.user,
                shop_name=request.POST.get("shop_name"),
                shop_address=request.POST.get("shop_address"),
                business_type=request.POST.get("business_type"),
                gst_number=request.POST.get("gst"),
                bank_account=request.POST.get("bank_account"),
            )

        elif role == "user":
            request.user.phone_number = request.POST.get("phone")
            request.user.address = request.POST.get("address")
            request.user.save()

        elif role == "admin":
            # admin-specific fields
            request.user.employee_id = request.POST.get("employee_id")
            request.user.save()

        return redirect_role_dashboard(role)

    return render(request, "auth/complete_registration.html", {"role": role})



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
    return redirect("user:user_home")


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
        return redirect("seller:seller_dashboard")

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

        return redirect("seller:seller_dashboard")

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
    return redirect("admin_panel:login")


@login_required
def help_support(request):
    """
    Help & Support page view
    """
    context = {
        'user': request.user,
    }
    return render(request, 'seller/help.html', context)

@login_required
def seller_guide(request):
    """
    seller guide page view
    """
    context = {
        'user': request.user,
    }
    return render(request, 'seller/seller_guide.html', context)

@login_required
def privacypolicy(request):
    return render(request,"seller/privacypolicy.html")
@login_required
def contact(request):
    return render(request,"seller/contact.html")
@login_required
def service(request):
    return render(request,"seller/service.html")
@login_required
def feedback(request):
    return render(request,"seller/feedback.html")




