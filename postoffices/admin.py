from django.contrib import admin
from .models import PostOffice


@admin.register(PostOffice)
class PostOfficeAdmin(admin.ModelAdmin):
    list_display = ('postal_code', 'city', 'address_str', 'is_closed', 'type_code', 'updated_at')
    list_filter = ('is_closed', 'type_code')
    search_fields = ('postal_code', 'address_str', 'city', 'region')
    readonly_fields = ('updated_at',)
from django.contrib import admin

# Register your models here.
