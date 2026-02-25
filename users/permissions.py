from rest_framework.permissions import BasePermission

class IsProfileCompleted(BasePermission):
    message = "Заполните профиль перед выполнением этой операции."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile_completed