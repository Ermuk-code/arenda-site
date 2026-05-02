from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'user_type',
        'profile_completed',
        'average_rating',
        'reviews_count',
        'is_active',
        'is_staff',
    )
    list_filter = (
        'user_type',
        'profile_completed',
        'is_active',
        'is_staff',
        'is_superuser',
    )
    search_fields = ('username', 'email', 'full_name', 'entrepreneur_name', 'company_name')
    ordering = ('-id',)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Marketplace profile',
            {
                'fields': (
                    'user_type',
                    'phone',
                    'full_name',
                    'entrepreneur_name',
                    'company_name',
                    'passport_series',
                    'passport_number',
                    'inn',
                    'kpp',
                    'ogrnip',
                    'profile_completed',
                    'average_rating',
                    'reviews_count',
                )
            },
        ),
    )

    readonly_fields = ('average_rating', 'reviews_count')
    actions = ('deactivate_users', 'activate_users')

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
