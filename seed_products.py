import random
import requests
from django.core.files.base import ContentFile

from core.models import Category, SubCategory
from seller.models import Product, ProductImage, SellerDetails


def download_image(url, filename):
    response = requests.get(url)
    return ContentFile(response.content, name=filename)


PRODUCT_IMAGES = [
    "https://images.unsplash.com/photo-1592286927505-ed303e3d0eef",
    "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1",
    "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c",
    "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",
    "https://images.unsplash.com/photo-1593642532973-d31b6557fa68",
]

CATEGORY_DATA = [
    ("Electronics", ["Mobiles", "Laptops", "Headphones"]),
    ("Fashion", ["Men", "Women", "Kids"]),
    ("Cosmetics", ["Makeup", "Skincare"]),
    ("Gaming", ["Consoles", "Accessories"]),
    ("Books", ["Fiction", "Educational"]),
    ("Wearables", ["Watches", "Fitness Bands"]),
]


def run():

    seller = SellerDetails.objects.first()
    if not seller:
        print("⚠ No seller exists. Please create one seller user from Django admin first.")
        return

    # Create categories and subcategories
    for cat_name, subs in CATEGORY_DATA:
        category, _ = Category.objects.get_or_create(name=cat_name)

        for sub_name in subs:
            SubCategory.objects.get_or_create(category=category, name=sub_name)

    # Create dummy products (150)
    for i in range(1, 151):
        name = f"Product {i}"
        subcategory = SubCategory.objects.order_by("?").first()

        product = Product.objects.create(
            name=name,
            description=f"This is sample description for product {i}",
            price=random.randint(300, 90000),
            stock=random.randint(5, 100),
            seller=seller,
            subcategory=subcategory,
        )

        # Add 2 images for each product
        for count, url in enumerate(PRODUCT_IMAGES[:2]):
            image_file = download_image(url + "?w=400&h=400&fit=crop", f"product-{i}-{count}.jpg")
            ProductImage.objects.create(product=product, image=image_file)

    print("🎉 Successfully created 150 dummy products with images!")
