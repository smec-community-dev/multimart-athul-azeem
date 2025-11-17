from django.contrib.auth import authenticate
from django.core.checks import messages
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField, Q
from django.http import HttpResponse
from django.utils.text import slugify
from django.shortcuts import render, redirect
from core.models import User
from user.models import Order
from .models import Product, SellerDetails, ProductImage
from django.contrib.auth import authenticate, login
from core.models import SubCategory
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import F, ExpressionWrapper, DecimalField



def view_product(request):
    products=Product.objects.all()
    return render(request,"seller/sellerdashboard.html",{"product":products})



def add_product(request):
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


        for img in gallery_images:
            ProductImage.objects.create(
                product=product,
                image=img,
                image_type="Gallery"
            )

        return redirect("seller_dashboard")





    products = Product.objects.all()
    subcategories = SubCategory.objects.all()
    return render(request, "seller/features.html", {"subcategories": subcategories, "products": products})

def update_product(request,id):
    product = Product.objects.get(id=id)


    if request.method == "POST":
        name = request.POST.get("name")

        # Prevent duplicate name (ignore self)
        if Product.objects.exclude(id=id).filter(name=name).exists():
            messages.error(request, "Product name already exists.")
            return redirect(request.META.get("HTTP_REFERER"))

        product.name = name
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        product.color = request.POST.get("color")
        product.size = request.POST.get("size")
        product.subcategory_id = request.POST.get("subcategory")

        # Handle images
        if 'main_image' in request.FILES:
            product.main_image = request.FILES['main_image']

        if 'gallery_images' in request.FILES:
            for img in request.FILES.getlist('gallery_images'):
                ProductImage.objects.create(product=product, image=img)

        product.save()
        messages.success(request, "Product updated successfully!")
        return redirect('add')



    return render(request,"feature.html",{"products":product})

def delete_product(request,id):

        product=Product.objects.get(id=id)
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



@login_required
def order_detail(request, id):
    seller = request.user.seller_details

    order = get_object_or_404(
        Order,
        id=id,
        seller=seller
    )

    items = (
        order.items.select_related("product")
        .annotate(
            total=ExpressionWrapper(
                F("unit_price") * F("quantity"),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    )
    order_total = sum(item.total for item in items)

    return render(request,"seller/seller_order_product_detail.html",   {"order": order, "items": items,"order_total": order_total  })


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
                return redirect('/home')
        return render(request,"seller/login.html",{"error":"invalid username or password"})
    return render(request,"seller/login.html")





