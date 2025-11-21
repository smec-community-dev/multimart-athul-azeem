from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from faker import Faker
from decimal import Decimal
import random

from user.models import Cart, Wishlist, Order, OrderItem, Review
from core.models import Category, SubCategory
from seller.models import SellerDetails, Product, ProductImage

User = get_user_model()
fake = Faker("en_IN")


class Command(BaseCommand):
    help = "Populate dummy data ONLY for seller 'Ashin123'"

    def handle(self, *args, **kwargs):
        self.stdout.write("\n🔄 Starting dummy data for seller Ashin123...\n")

        seller_user = self.get_seller_user()
        seller = self.get_or_create_seller_details(seller_user)

        categories = self.create_categories()
        subcategories = self.create_subcategories(categories)
        products = self.create_products(seller, subcategories)
        self.create_product_images(products)

        users = self.get_customer_users()

        self.create_cart(users, products)
        self.create_wishlist(users, products)
        self.create_orders(users, seller, products)
        self.create_reviews(users, products)

        self.stdout.write(self.style.SUCCESS("\n🎉 Dummy data added successfully ONLY for Ashin123!"))

    # --------------------------------------------------------------
    # GET EXISTING SELLER USER
    # --------------------------------------------------------------
    def get_seller_user(self):
        try:
            return User.objects.get(username="Ashin123")
        except User.DoesNotExist:
            raise Exception("❌ User 'Ashin123' does NOT exist. Create him first!")

    # --------------------------------------------------------------
    # CREATE SELLER DETAILS ONLY IF NOT EXISTS
    # --------------------------------------------------------------
    def get_or_create_seller_details(self, user):
        seller, created = SellerDetails.objects.get_or_create(
            user=user,
            defaults={
                "shop_name": "Ashin Fashion Shop",
                "shop_address": fake.address(),
                "business_type": "Retail",
                "phone_number": user.phone_number or "9876543210",
                "gst_number": f"GST{random.randint(10000000000, 99999999999)}",
                "bank_account": str(random.randint(10000000, 99999999)),
                "is_verified": True,
            }
        )

        if created:
            self.stdout.write("✓ Created SellerDetails for Ashin123")
        else:
            self.stdout.write("✓ SellerDetails already existed for Ashin123")

        return seller

    # --------------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------------
    def create_categories(self):
        names = ["Electronics", "Fashion", "Sports", "Books", "Home"]
        categories = []

        for name in names:
            obj, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": f"{name} products"}
            )
            categories.append(obj)

        return categories

    # --------------------------------------------------------------
    # SUBCATEGORIES
    # --------------------------------------------------------------
    def create_subcategories(self, categories):
        mapping = {
            "Electronics": ["Mobiles", "Laptops", "Audio"],
            "Fashion": ["Men", "Women", "Kids"],
            "Sports": ["Gym", "Cricket", "Football"],
            "Books": ["Fiction", "Education"],
            "Home": ["Kitchen", "Furniture"]
        }

        subs = []
        for cat in categories:
            for name in mapping[cat.name]:
                obj, _ = SubCategory.objects.get_or_create(
                    name=name,
                    category=cat,
                    defaults={"description": f"{name} under {cat.name}"}
                )
                subs.append(obj)
        return subs

    # --------------------------------------------------------------
    # PRODUCTS ONLY FOR ASHIN'S SHOP
    # --------------------------------------------------------------
    def create_products(self, seller, subcategories):
        products = []
        for _ in range(50):
            subcat = random.choice(subcategories)

            product, _ = Product.objects.get_or_create(
                name=fake.word() + "-" + str(random.randint(100, 999)),
                seller=seller,
                subcategory=subcat,
                defaults={
                    "description": fake.text(max_nb_chars=200),
                    "price": Decimal(random.uniform(200, 3000)).quantize(Decimal("0.01")),
                    "stock": random.randint(5, 80),
                    "color": random.choice(["Red", "Blue", "Black", "White"]),
                    "size": random.choice(["S", "M", "L", "XL"]),
                }
            )
            products.append(product)

        return products

    # --------------------------------------------------------------
    # PRODUCT IMAGES
    # --------------------------------------------------------------
    def create_product_images(self, products):
        for p in products:
            ProductImage.objects.get_or_create(
                product=p,
                image_type="Main",
                defaults={"image": "products/dummy.jpg"}
            )

    # --------------------------------------------------------------
    # FIVE DUMMY CUSTOMERS FOR ORDERS
    # --------------------------------------------------------------
    def get_customer_users(self):
        return User.objects.filter(role="user")[:5]

    # --------------------------------------------------------------
    # CART
    # --------------------------------------------------------------
    def create_cart(self, users, products):
        for u in users:
            for _ in range(2):
                Cart.objects.get_or_create(
                    user=u,
                    product=random.choice(products),
                    defaults={"quantity": random.randint(1, 4)}
                )

    # --------------------------------------------------------------
    # WISHLIST
    # --------------------------------------------------------------
    def create_wishlist(self, users, products):
        for u in users:
            for _ in range(2):
                Wishlist.objects.get_or_create(
                    user=u,
                    product=random.choice(products)
                )

    # --------------------------------------------------------------
    # ORDERS FOR ASHIN
    # --------------------------------------------------------------
    def create_orders(self, users, seller, products):
        for u in users:
            for _ in range(2):

                status = random.choice(["Pending", "Processing", "Shipped", "Delivered"])

                order = Order.objects.create(
                    user=u,
                    seller=seller,
                    total_amount=Decimal(random.uniform(500, 3000)).quantize(Decimal("0.01")),
                    shipping_address=fake.address(),
                    payment_method=random.choice(["UPI", "COD", "Card"]),
                    status=status,
                    pending_date=timezone.now(),
                    processing_date=timezone.now() if status in ["Processing", "Shipped", "Delivered"] else None,
                    shipped_date=timezone.now() if status in ["Shipped", "Delivered"] else None,
                    delivered_date=timezone.now() if status == "Delivered" else None
                )

                for _ in range(2):
                    product = random.choice(products)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 3),
                        unit_price=product.price
                    )

    # --------------------------------------------------------------
    # REVIEWS
    # --------------------------------------------------------------
    def create_reviews(self, users, products):
        for u in users:
            for _ in range(2):
                Review.objects.create(
                    user=u,
                    product=random.choice(products),
                    rating=random.randint(1, 5),
                    comment=fake.text(max_nb_chars=120)
                )
