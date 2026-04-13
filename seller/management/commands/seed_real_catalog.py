import random
from decimal import Decimal

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models import Category, SubCategory, User
from seller.models import Product, ProductImage, SellerDetails


CATALOG = {
    "Cosmetics": {
        "Skincare": [
            ("Vitamin C Face Serum", "Brightening serum with hyaluronic acid for daily glow.", "Amber", "30ml", "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=1200&h=1200&fit=crop"),
            ("Hydrating Gel Moisturizer", "Lightweight moisturizer suitable for all skin types.", "Blue", "50ml", "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=1200&h=1200&fit=crop"),
            ("SPF 50 Sunscreen", "Broad spectrum sun protection with matte finish.", "White", "60ml", "https://images.unsplash.com/photo-1599305090598-fe179d501227?w=1200&h=1200&fit=crop"),
            ("Night Repair Cream", "Overnight cream to improve texture and hydration.", "Ivory", "40g", "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=1200&h=1200&fit=crop"),
        ],
    },
    "Gaming": {
        "Consoles": [
            ("PlayStation 5 Slim", "Next-gen console with ultra-fast SSD and 4K support.", "White", "Standard", "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=1200&h=1200&fit=crop"),
            ("Xbox Series X", "Powerful gaming console for high frame-rate gameplay.", "Black", "1TB", "https://images.unsplash.com/photo-1621259182978-fbf93132d53d?w=1200&h=1200&fit=crop"),
            ("Wireless Gaming Controller", "Ergonomic controller with low-latency response.", "Black", "Standard", "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=1200&h=1200&fit=crop"),
            ("Gaming Headset Pro", "Surround sound headset with detachable mic.", "Black", "Standard", "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=1200&h=1200&fit=crop"),
        ],
    },
    "Books": {
        "Reading": [
            ("Atomic Habits", "Practical strategies to build good habits and break bad ones.", "Blue", "Paperback", "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=1200&h=1200&fit=crop"),
            ("Deep Work", "Guide to focused success in a distracted world.", "Navy", "Paperback", "https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=1200&h=1200&fit=crop"),
            ("Clean Code", "A handbook of agile software craftsmanship principles.", "White", "Paperback", "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=1200&h=1200&fit=crop"),
            ("The Psychology of Money", "Timeless lessons on wealth, greed, and happiness.", "Green", "Paperback", "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=1200&h=1200&fit=crop"),
        ],
    },
    "Wearables": {
        "Smart Devices": [
            ("Smart Watch Active", "Fitness smartwatch with heart-rate and sleep tracking.", "Black", "44mm", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=1200&h=1200&fit=crop"),
            ("Fitness Band 7", "Slim fitness tracker with AMOLED display.", "Graphite", "Standard", "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=1200&h=1200&fit=crop"),
            ("Wireless Sports Earbuds", "Sweat-resistant earbuds for workouts and runs.", "White", "Standard", "https://images.unsplash.com/photo-1588423771073-b8903fbb85b5?w=1200&h=1200&fit=crop"),
            ("Smart Ring Health", "Minimal ring for sleep and activity monitoring.", "Silver", "Size 9", "https://images.unsplash.com/photo-1617040619263-41c5a9ca7521?w=1200&h=1200&fit=crop"),
        ],
    },
}


def fetch_image(url: str, filename: str):
    response = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type:
        raise ValueError(f"Unexpected content type: {content_type}")
    return ContentFile(response.content, name=filename)


class Command(BaseCommand):
    help = "Seed realistic categories/products with working images for homepage slider."

    def handle(self, *args, **options):
        seller = SellerDetails.objects.select_related("user").first()
        if not seller:
            user, _ = User.objects.get_or_create(
                username="demo_seller",
                defaults={"email": "demo_seller@example.com", "role": "seller"},
            )
            user.role = "seller"
            user.set_password("DemoSeller@123")
            user.save()
            seller, _ = SellerDetails.objects.get_or_create(
                user=user,
                defaults={
                    "shop_name": "Demo Store",
                    "shop_address": "MG Road, Bengaluru",
                    "phone_number": "9876543210",
                    "business_type": "General",
                    "is_verified": True,
                },
            )

        created_products = 0
        for category_name, subcats in CATALOG.items():
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"{category_name} essentials and best picks.", "status": True},
            )
            for sub_name, products in subcats.items():
                subcategory, _ = SubCategory.objects.get_or_create(
                    category=category,
                    name=sub_name,
                    defaults={"description": f"Top-rated {sub_name.lower()} products.", "status": True},
                )
                for idx, (name, description, color, size, image_url) in enumerate(products):
                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            "seller": seller,
                            "subcategory": subcategory,
                            "description": description,
                            "price": Decimal(random.randint(499, 14999)),
                            "stock": random.randint(8, 80),
                            "color": color,
                            "size": size,
                            "is_featured": True if idx == 0 else False,
                        },
                    )
                    if not created:
                        product.seller = seller
                        product.subcategory = subcategory
                        product.description = description
                        product.color = color
                        product.size = size
                        product.stock = max(product.stock, 8)
                        product.is_featured = product.is_featured or (idx == 0)
                        product.save()
                    else:
                        created_products += 1

                    # Ensure image set is refreshed with relevant product images.
                    product.images.all().delete()
                    try:
                        ProductImage.objects.create(
                            product=product,
                            image=fetch_image(image_url, f"{product.slug}-main.jpg"),
                            image_type="Main",
                        )
                        ProductImage.objects.create(
                            product=product,
                            image=fetch_image(image_url.replace("w=1200", "w=1000"), f"{product.slug}-gallery.jpg"),
                            image_type="Gallery",
                        )
                    except Exception as exc:
                        self.stdout.write(self.style.WARNING(f"Image download skipped for {product.name}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Catalog ready. New products created: {created_products}"))
