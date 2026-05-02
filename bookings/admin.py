from django.contrib import admin

from .models import Booking, Review


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'item',
        'renter',
        'status',
        'payment_status',
        'start_date',
        'end_date',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'created_at', 'start_date', 'end_date')
    search_fields = ('item__title', 'renter__username', 'item__owner__username')
    ordering = ('-created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'item_title',
        'author_username',
        'rating',
        'is_hidden',
        'moderated_by',
        'moderated_at',
        'created_at',
    )
    list_filter = ('rating', 'is_hidden', 'created_at', 'moderated_at')
    search_fields = (
        'booking__item__title',
        'booking__renter__username',
        'comment',
        'moderation_reason',
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'moderated_at', 'moderated_by')
    actions = ('hide_reviews', 'unhide_reviews')

    @admin.display(description='Item')
    def item_title(self, obj):
        return obj.booking.item.title

    @admin.display(description='Author')
    def author_username(self, obj):
        return obj.booking.renter.username

    @admin.action(description='Hide selected reviews from public pages')
    def hide_reviews(self, request, queryset):
        for review in queryset:
            review.hide(
                moderated_by=request.user,
                reason=review.moderation_reason or 'Hidden by administrator',
            )

    @admin.action(description='Restore selected reviews to public pages')
    def unhide_reviews(self, request, queryset):
        for review in queryset:
            review.unhide()
