from django.contrib import admin
from core.models import SubCategory, Category
from .models import User
admin.site.register(Category)
admin.site.register(SubCategory)


