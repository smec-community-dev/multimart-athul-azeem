import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
from PIL import Image
import io
from django.core.files.base import ContentFile
from core.models import Category, SubCategory
from seller.models import SellerDetails, Product, ProductImage
from user.models import User, Cart, Wishlist, Order, OrderItem, Review

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with extensive dummy data for all models'

    def handle(self, *args, **options):

        # FIXED: Correct Faker seeding method
        Faker.seed(42)
        fake = Faker()

        # Step 1: Create More Dummy Categories (10 total)
        category_names = [
            'Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports', 'Beauty',
            'Toys', 'Automotive', 'Health', 'Food & Grocery'
        ]
        categories = []
        for name in category_names:
            cat, created = Category.objects.get_or_create(
                name=name,
                defaults={'description': fake.sentence(nb_words=10)}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat.name}'))
            categories.append(cat)

        # Step 2: Create More Dummy SubCategories (30 total)
        subcat_data = []
        for cat in categories:
            subcats = [
                {'name': f'{cat.name} Sub1', 'category': cat},
                {'name': f'{cat.name} Sub2', 'category': cat},
                {'name': f'{cat.name} Sub3', 'category': cat},
            ]
            for sub_data in subcats:
                sub, created = SubCategory.objects.get_or_create(
                    name=sub_data['name'],
                    category=sub_data['category'],
                    defaults={'description': fake.sentence()}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created subcategory: {sub.name}'))
                subcat_data.append(sub)

        # Step 3: Create Dummy Users (5 sellers, 10 buyers)
        dummy_users = []
        for i in range(15):
            role = 'seller' if i < 5 else 'user'
            user_data = {
                'username': f'{role}{i + 1}',
                'email': f'{role}{i + 1}@example.com',
                'password': 'pass123',
                'role': role,
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'phone_number': fake.phone_number(),
                'address': fake.address(),
            }
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(**user_data)
                if role == 'seller':
                    SellerDetails.objects.create(
                        user=user,
                        shop_name=f"{user.first_name}'s Shop",
                        shop_address=fake.address(),
                        business_type=fake.word().capitalize(),
                        phone_number=fake.phone_number(),
                        gst_number=fake.bothify(text='GST#########'),
                        bank_account=fake.iban(),
                        is_verified=fake.boolean(chance_of_getting_true=70),
                    )
                self.stdout.write(self.style.SUCCESS(f'Created {role}: {user.username}'))
                dummy_users.append(user)

        sellers = SellerDetails.objects.all()
        buyers = User.objects.filter(role='user')

        # Step 4: Create Dummy Products (50 total)
        dummy_products = []
        for i in range(50):
            seller = fake.random_element(sellers)
            subcat = fake.random_element(subcat_data)
            prod_data = {
                'seller': seller,
                'subcategory': subcat,
                'name': fake.catch_phrase()[:50],
                'description': fake.paragraph(nb_sentences=3),
                'price': fake.random_number(digits=3) + fake.random.uniform(0, 99.99),
                'stock': fake.random_int(min=0, max=200),
                'color': fake.random_element(['Red', 'Blue', 'Green', 'Black', 'White', 'N/A']),
                'size': fake.random_element(['S', 'M', 'L', 'XL', 'One Size', 'N/A']),
            }

            if not Product.objects.filter(name=prod_data['name']).exists():
                product = Product.objects.create(**prod_data)

                # Main Image
                main_buffer = io.BytesIO()
                img = Image.new('RGB', (400, 400),
                                color=(fake.random_int(0, 255), fake.random_int(0, 255), fake.random_int(0, 255)))
                img.save(main_buffer, format='PNG')
                main_buffer.seek(0)
                main_file = ContentFile(main_buffer.read(), name=f"{product.slug}_main.png")
                ProductImage.objects.create(product=product, image=main_file, image_type='Main')

                # 2-4 Gallery Images
                for j in range(fake.random_int(min=2, max=4)):
                    gal_buffer = io.BytesIO()
                    gal_img = Image.new('RGB', (300, 300),
                                        color=(fake.random_int(0, 255), fake.random_int(0, 255), fake.random_int(0, 255)))
                    gal_img.save(gal_buffer, format='PNG')
                    gal_buffer.seek(0)
                    gal_file = ContentFile(gal_buffer.read(), name=f"{product.slug}_gal_{j}.png")
                    ProductImage.objects.create(product=product, image=gal_file, image_type='Gallery')

                dummy_products.append(product)
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
            else:
                product = Product.objects.get(name=prod_data['name'])
                dummy_products.append(product)

        # Step 5: Create Dummy Carts
        for buyer in buyers:
            for _ in range(2):
                prod = fake.random_element(dummy_products)
                Cart.objects.get_or_create(
                    user=buyer,
                    product=prod,
                    defaults={'quantity': fake.random_int(min=1, max=5)}
                )

        # Step 6: Create Dummy Wishlists
        for buyer in buyers:
            for _ in range(fake.random_int(min=1, max=3)):
                prod = fake.random_element(dummy_products)
                Wishlist.objects.get_or_create(user=buyer, product=prod)

        # Step 7: Create Dummy Orders
        for i in range(30):
            buyer = fake.random_element(buyers)
            seller = fake.random_element(sellers)

            order = Order.objects.create(
                user=buyer,
                seller=seller,
                total_amount=fake.random_number(digits=3) + fake.random.uniform(0, 99.99),
                shipping_address=fake.address(),
                payment_method=fake.random_element(['Credit Card', 'Debit Card', 'PayPal', 'COD']),
                status=fake.random_element(['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']),
            )

            # Order Items
            for _ in range(fake.random_int(min=1, max=3)):
                prod = fake.random_element([p for p in dummy_products if p.seller == seller])
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=fake.random_int(min=1, max=3),
                    unit_price=prod.price
                )

        # Step 8: Create Dummy Reviews
        for i in range(40):
            Review.objects.create(
                user=fake.random_element(dummy_users),
                product=fake.random_element(dummy_products),
                rating=fake.random_int(min=1, max=5),
                comment=fake.paragraph(nb_sentences=2)
            )

        self.stdout.write(self.style.SUCCESS("Dummy data generation complete!"))
