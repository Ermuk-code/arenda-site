from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from .serializers import RegisterSerializer
from .serializers import ProfileSerializer
from drf_spectacular.utils import extend_schema

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