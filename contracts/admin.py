from django.contrib import admin

from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document_number',
        'booking',
        'is_signed',
        'renter_signed_at',
        'owner_signed_at',
        'signed_at',
        'created_at',
    )
    search_fields = ('document_number', 'booking__item__title', 'booking__renter__username')
    list_filter = ('is_signed', 'created_at', 'signed_at')
