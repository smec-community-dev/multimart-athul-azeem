import os
import time

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
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

# Project models
from core.models import User, SubCategory, Category  # Assuming Category is in core.models
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

        return redirect("seller_dashboard")

   

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
        return redirect('login')






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


from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password, ValidationError
from django.shortcuts import render, redirect
from .models import SellerDetails  # Assuming the model import


@login_required
@seller_required
def seller_profile_view(request):
    # Get or create seller details for the user
    seller, created = SellerDetails.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'profile_info':
            # Handle profile information form
            email = request.POST.get('email', '')
            phone_number = request.POST.get('phone_number', '')
            profile_image = request.FILES.get('profile_image')

            updated = False
            if email and email != request.user.email:
                try:
                    # Basic email validation can be added here if needed
                    request.user.email = email
                    request.user.save()
                    updated = True
                except Exception as e:
                    messages.error(request, f'Error updating email: {str(e)}')
                    return redirect('profile')

            if phone_number and phone_number != seller.phone_number:
                seller.phone_number = phone_number
                seller.save()
                updated = True

            if profile_image:
                seller.profile_image = profile_image
                seller.save()
                updated = True

            if updated:
                messages.success(request, 'Profile information updated successfully!')
            else:
                messages.info(request, 'No changes were made.')
            return redirect('profile')

        elif form_type == 'business_info':
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



from django.db.models.functions import TruncDay, TruncWeek
from django.db.models import Sum, Avg
import json

@login_required()
@seller_required
def product_details(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        seller=request.user.seller_details
    )

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
    weekly_qs = (
        OrderItem.objects
        .filter(product=product)
        .annotate(week=TruncWeek("order__order_date"))
        .values("week")
        .annotate(total=Sum("quantity"))
        .order_by("week")
    )

    weekly_labels = [w["week"].strftime("%a") for w in weekly_qs]
    weekly_sales = [w["total"] for w in weekly_qs]

    # MONTHLY SALES
    monthly_qs = (
        OrderItem.objects
        .filter(product=product)
        .annotate(day=TruncDay("order__order_date"))
        .values("day")
        .annotate(total=Sum("quantity"))
        .order_by("day")
    )

    monthly_labels = [m["day"].strftime("Day %d") for m in monthly_qs]
    monthly_sales = [m["total"] for m in monthly_qs]

    if not monthly_labels:
        monthly_labels = [f"Day {i}" for i in range(1, 31)]
        monthly_sales = [0] * 30

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------
    return render(
        request,
        "seller/seller_product_details.html",
        {
            "product": product,
            "reviews": reviews,
            "avg_rating": round(avg_rating, 1),
            "total_quantity_sold": total_quantity_sold,
            "order_count": order_count,
            "images": images,
            "main_image": main_image,

            # Chart Data
            "weekly_labels": json.dumps(weekly_labels),
            "weekly_sales": json.dumps(weekly_sales),
            "monthly_labels": json.dumps(monthly_labels),
            "monthly_sales": json.dumps(monthly_sales),
        }
    )
