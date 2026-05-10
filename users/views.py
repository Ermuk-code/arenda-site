from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from django.contrib.auth import get_user_model
from django.core.cache import cache
from random import randint
from .serializers import RegisterSerializer
from .serializers import ProfileSerializer
from drf_spectacular.utils import extend_schema

User = get_user_model()

@extend_schema(
    description="""
Обновление профиля пользователя.

Типы пользователей:

- individual: паспорт (серия + номер) + ИНН
- entrepreneur: ИНН + ОГРНИП
- legal: ИНН + КПП
"""
)
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'error': 'Wrong password'}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({'status': 'password changed'})


class ProfileView(APIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordResetRequestView(APIView):
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'error': 'Email is required'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'error': 'User with this email was not found'}, status=404)

        code = f"{randint(0, 999999):06d}"
        cache.set(f'password_reset_code:{email}', code, timeout=15 * 60)

        from notifications.email import _send
        _send(
            to_email=user.email,
            subject='Код для восстановления пароля',
            message=(
                f'Здравствуйте, {user.username}!\n\n'
                f'Ваш код для восстановления пароля: {code}\n'
                'Код действует 15 минут.\n\n'
                'Если это были не вы, просто проигнорируйте это письмо.'
            )
        )

        return Response({'status': 'verification code sent'})


class PasswordResetConfirmView(APIView):
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        code = (request.data.get('code') or '').strip()
        new_password = request.data.get('new_password') or ''

        if not email or not code or not new_password:
            return Response({'error': 'Email, code and new_password are required'}, status=400)

        if len(new_password) < 6:
            return Response({'error': 'Password too short'}, status=400)

        saved_code = cache.get(f'password_reset_code:{email}')
        if not saved_code or saved_code != code:
            return Response({'error': 'Invalid or expired code'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'error': 'User with this email was not found'}, status=404)

        user.set_password(new_password)
        user.save()
        cache.delete(f'password_reset_code:{email}')

        return Response({'status': 'password updated'})
