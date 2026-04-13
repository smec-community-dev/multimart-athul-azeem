
from django.db import models
from django.template.defaultfilters import slugify

from core.models import User, SubCategory


class SellerDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_details')
    shop_name = models.CharField(max_length=100)
    shop_address = models.TextField()
    business_type = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_blocked=models.BooleanField(default=False)

    def __str__(self):
        return self.shop_name

# ------------------ PRODUCT ------------------
class Product(models.Model):
    seller = models.ForeignKey(SellerDetails, on_delete=models.CASCADE, related_name='products')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    is_featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def image(self):
        """
        Compatibility accessor for templates that expect `product.image.url`.
        Returns the `ImageFieldFile` from the Main image, or falls back to
        the first available image for this product.
        """
        main_image = self.images.filter(image_type="Main").first()
        if main_image and main_image.image:
            return main_image.image

        fallback = self.images.first()
        if fallback and fallback.image:
            return fallback.image

        return None


# ------------------ PRODUCT IMAGE ------------------
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    image_type = models.CharField(
        max_length=20,
        choices=[('Main', 'Main'), ('Gallery', 'Gallery')],
        default='Main'
    )

    def __str__(self):
        return f"{self.product.name} - {self.image_type}"
