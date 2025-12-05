
import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from core.models import User, Category, SubCategory
from seller.models import SellerDetails, Product, ProductImage
from django.core.files.base import ContentFile

# Create test seller
username = 'test_seller_agent'
password = 'password123'
email = 'test_agent@example.com'

user, created = User.objects.get_or_create(username=username, defaults={'email': email})
user.set_password(password)
user.role = 'seller'
user.save()

seller_details, _ = SellerDetails.objects.get_or_create(
    user=user,
    defaults={
        'shop_name': "Agent Shop", 
        'phone_number': "1234567890",
        'shop_address': "123 Test Lane"
    }
)

# Create Dummy Category/SubCategory
cat, _ = Category.objects.get_or_create(name="TestCat", defaults={'description': 'Test Category'})
subcat, _ = SubCategory.objects.get_or_create(name="TestSubCat", category=cat, defaults={'description': 'Test SubCategory'})

# Create Product
product_name = "Test Gallery Product"
product, prod_created = Product.objects.get_or_create(
    seller=seller_details,
    name=product_name,
    defaults={
        'subcategory': subcat,
        'description': 'A product to test gallery images.',
        'price': 999.00,
        'stock': 50,
    }
)

if prod_created:
    print("Created new product.")
    # Create simple images
    # We won't create actual files on disk for speed, just db entries if possible, 
    # but accessing .url might require it. 
    # Let's clean up existing images for this product just in case
    product.images.all().delete()
    
    ProductImage.objects.create(product=product, image='products/test_main.jpg', image_type='Main')
    ProductImage.objects.create(product=product, image='products/test_gal1.jpg', image_type='Gallery')
    ProductImage.objects.create(product=product, image='products/test_gal2.jpg', image_type='Gallery')

else:
    print("Product already exists.")
    # Ensure images exist
    if not product.images.filter(image_type='Main').exists():
         ProductImage.objects.create(product=product, image='products/test_main.jpg', image_type='Main')
    if not product.images.filter(image_type='Gallery').exists():
         ProductImage.objects.create(product=product, image='products/test_gal1.jpg', image_type='Gallery')
         ProductImage.objects.create(product=product, image='products/test_gal2.jpg', image_type='Gallery')


print(f"LOGIN_USERNAME={username}")
print(f"LOGIN_PASSWORD={password}")
print(f"PRODUCT_SLUG={product.slug}")
