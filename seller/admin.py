from django.contrib import admin
from seller.models import Product, SellerDetails, User, ProductImage

admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(SellerDetails)
admin.site.register(User)


