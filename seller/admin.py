from django.contrib import admin
from seller.models import Product,SellerDetails,ProductImage

admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(SellerDetails)



