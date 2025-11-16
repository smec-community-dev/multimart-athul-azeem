import random
import requests
from django.db import connection
from django.core.files.base import ContentFile
from django.utils.text import slugify

from core.models import Category, SubCategory
from seller.models import Product, ProductImage, SellerDetails


PRODUCT_IMAGES = [
    "https://images.unsplash.com/photo-1592286927505-ed303e3d0eef",
    "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1",
    "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c",
    "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",
]


def download_image(url, name):
    response = requests.get(url)
    return ContentFile(response.content, name=name)


def run():
    seller = SellerDetails.objects.first()
    if not seller:
        print("⚠ Add at least 1 Seller from admin first")
        return

    for i in range(1, 151):
        name = f"Product {i}"
        subcategory = SubCategory.objects.order_by("?").first()

        # Create product WITHOUT slug (to avoid override duplicate issue)
        product = Product(
            name=name,
            description=f"Dummy description for product {i}",
            price=random.randint(300, 90000),
            stock=random.randint(5, 100),
            seller=seller,
            subcategory=subcategory,
        )
        product.save(force_insert=True)

        # Generate correct unique slug manually using SQL (bypass save override)
        unique_slug = f"{slugify(name)}-{product.id}"
        with connection.cursor() as cursor:
            cursor.execute("UPDATE seller_product SET slug=%s WHERE id=%s", [unique_slug, product.id])

        # Add two images
        for index, img_url in enumerate(PRODUCT_IMAGES[:2]):
            img = download_image(img_url + "?w=400&h=400&fit=crop", f"{unique_slug}-{index}.jpg")
            ProductImage.objects.create(product=product, image=img)

    print("🎉 SUCCESS: 150 dummy products created!")


