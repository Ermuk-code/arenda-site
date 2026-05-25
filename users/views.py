from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from django.contrib.auth import get_user_model
from django.core.cache import cache
from random import randint
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .serializers import RegisterSerializer, ProfileSerializer
from .dadata_inn_service import get_party_info
from notifications.email import send_password_reset_code

User = get_user_model()


class SendEmailVerificationCodeView(APIView):
    """
    Шаг 1 регистрации: отправить код подтверждения на email.
    POST { "email": "user@example.com" }
    """
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response({'error': 'Email обязателен'}, status=400)

        if User.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Пользователь с таким email уже существует'}, status=400)

        code = f"{randint(0, 999999):06d}"
        cache.set(f'email_verify_code:{email}', code, timeout=15 * 60)

        from notifications.email import _send
        _send(
            to_email=email,
            subject='Код подтверждения email — Mokitoki',
            message=(
                f'Здравствуйте!\n\n'
                f'Ваш код подтверждения для регистрации на Mokitoki: {code}\n'
                'Код действует 15 минут.\n\n'
                'Если это были не вы, просто проигнорируйте это письмо.'
            )
        )
        return Response({'status': 'Код подтверждения отправлен на указанный email'})


@extend_schema(
    description="""
Регистрация нового пользователя.

Перед регистрацией необходимо подтвердить email:
1. POST /api/users/send-email-code/ с { "email": "..." } — на почту придёт 6-значный код
2. Передать этот код в поле `email_code` при регистрации

Типы пользователей:

- individual: паспорт (серия + номер) + ИНН (12 цифр)
- entrepreneur: наименование ИП + ИНН (12 цифр) + ОГРНИП (15 цифр, с проверкой КЦ)
- legal: наименование организации + ИНН (10 цифр, с проверкой КЦ) + КПП (9 символов)

Для ИП и юрлиц можно использовать кнопку «Заполнить по ИНН» — 
см. endpoint GET /api/users/fill-by-inn/?inn=<ИНН>
"""
)
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        email = (request.data.get('email') or '').strip().lower()
        email_code = (request.data.get('email_code') or '').strip()

        if not email_code:
            return Response(
                {'error': 'Необходимо указать код подтверждения email (email_code)'},
                status=400
            )

        saved_code = cache.get(f'email_verify_code:{email}')
        if not saved_code or saved_code != email_code:
            return Response(
                {'error': 'Неверный или истёкший код подтверждения email'},
                status=400
            )

        response = super().create(request, *args, **kwargs)
        cache.delete(f'email_verify_code:{email}')
        return response


@extend_schema(
    description="""
Заполнить реквизиты по ИНН через DaData.

Передайте ИНН в параметре `inn`. 
Сервис автоматически определит тип (юрлицо или ИП) и вернёт данные для автозаполнения форм.

**Для юридического лица (ИНН 10 цифр)** вернёт:
```json
{
  "type": "legal",
  "data": { "company_name": "...", "inn": "...", "kpp": "..." }
}
```

**Для ИП (ИНН 12 цифр)** вернёт:
```json
{
  "type": "entrepreneur",
  "data": { "entrepreneur_name": "...", "inn": "...", "ogrnip": "..." }
}
```
""",
    parameters=[
        OpenApiParameter(
            name='inn',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='ИНН организации (10 цифр) или ИП (12 цифр)',
        )
    ],
    examples=[
        OpenApiExample(
            'Юридическое лицо',
            value={'type': 'legal', 'data': {'company_name': 'ООО «Ромашка»', 'inn': '7707083893', 'kpp': '770701001'}},
            response_only=True,
        ),
        OpenApiExample(
            'ИП',
            value={'type': 'entrepreneur', 'data': {'entrepreneur_name': 'ИП Иванов Иван Иванович', 'inn': '500100732259', 'ogrnip': '304500116000157'}},
            response_only=True,
        ),
    ],
)
class FillByInnView(APIView):
    """
    GET /api/users/fill-by-inn/?inn=<ИНН>

    Запрашивает DaData и возвращает реквизиты организации/ИП для автозаполнения.
    Доступен без авторизации (нужен при регистрации).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        inn = (request.query_params.get('inn') or '').strip()
        if not inn:
            return Response({'error': 'Параметр inn обязателен'}, status=400)

        result = get_party_info(inn)

        if result['error']:
            return Response({'error': result['error']}, status=404 if 'не найден' in result['error'] else 400)

        return Response({
            'type': result['type'],
            'data': result['data'],
        })


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'error': 'Неверный текущий пароль'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'status': 'Пароль изменён'})


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
            return Response({'error': 'Email обязателен'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'error': 'Пользователь с таким email не найден'}, status=404)

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
        return Response({'status': 'Код подтверждения отправлен'})


class PasswordResetConfirmView(APIView):
    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        code = (request.data.get('code') or '').strip()
        new_password = request.data.get('new_password') or ''

        if not email or not code or not new_password:
            return Response({'error': 'Необходимы: email, code, new_password'}, status=400)

        if len(new_password) < 6:
            return Response({'error': 'Пароль слишком короткий (минимум 6 символов)'}, status=400)

        saved_code = cache.get(f'password_reset_code:{email}')
        if not saved_code or saved_code != code:
            return Response({'error': 'Неверный или истёкший код'}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'error': 'Пользователь с таким email не найден'}, status=404)

        user.set_password(new_password)
        user.save()
        cache.delete(f'password_reset_code:{email}')
        return Response({'status': 'Пароль обновлён'})
