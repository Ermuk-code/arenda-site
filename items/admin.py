from django.contrib import admin

from .models import Category, Item, ItemImage, ItemModerationRequest, ItemReview, ItemVideo
from .services import approve_item_moderation_request, reject_item_moderation_request


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


@admin.register(ItemModerationRequest)
class ItemModerationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'submitted_by', 'action', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'action', 'created_at', 'reviewed_at')
    search_fields = ('item__title', 'submitted_by__username', 'submitted_by__email', 'rejection_reason')
    readonly_fields = (
        'item',
        'submitted_by',
        'action',
        'status',
        'item_snapshot',
        'user_snapshot',
        'reviewed_by',
        'reviewed_at',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)
    actions = ('approve_requests', 'reject_requests')

    @admin.action(description='Approve selected item requests')
    def approve_requests(self, request, queryset):
        for moderation_request in queryset.filter(status=ItemModerationRequest.STATUS_PENDING):
            approve_item_moderation_request(moderation_request, request.user)

    @admin.action(description='Reject selected item requests')
    def reject_requests(self, request, queryset):
        for moderation_request in queryset.filter(status=ItemModerationRequest.STATUS_PENDING):
            reject_item_moderation_request(
                moderation_request,
                request.user,
                'Rejected by administrator from Django admin.',
            )


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
