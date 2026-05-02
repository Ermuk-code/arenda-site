from django.contrib import admin

from .models import Category, Item, ItemImage, ItemReview, ItemVideo


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 0


class ItemVideoInline(admin.TabularInline):
    model = ItemVideo
    extra = 0


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'owner',
        'category',
        'price_per_day',
        'status',
        'average_rating',
        'reviews_count',
        'created_at',
    )
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'owner__username', 'owner__email')
    ordering = ('-created_at',)
    inlines = (ItemImageInline, ItemVideoInline)
    actions = ('block_items', 'unblock_items')

    @admin.action(description='Block selected items')
    def block_items(self, request, queryset):
        queryset.update(status='blocked')

    @admin.action(description='Mark selected items as available')
    def unblock_items(self, request, queryset):
        queryset.update(status='available')


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'uploaded_at')
    search_fields = ('item__title',)
    ordering = ('-uploaded_at',)


@admin.register(ItemVideo)
class ItemVideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'uploaded_at')
    search_fields = ('item__title',)
    ordering = ('-uploaded_at',)


@admin.register(ItemReview)
class ItemReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'author', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('item__title', 'author__username', 'comment')
    ordering = ('-created_at',)
