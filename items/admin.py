from django.contrib import admin
from .models import Category, Item, ItemImage, ItemVideo, ItemReview

admin.site.register(Category)
admin.site.register(Item)
admin.site.register(ItemImage)
admin.site.register(ItemVideo)
admin.site.register(ItemReview)
