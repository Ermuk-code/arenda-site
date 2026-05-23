from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import PostOffice
from .serializers import PostOfficeSerializer
from .services import fetch_offices_from_dadata, parse_office


class PostOfficeSearchView(APIView):
    """
    GET /api/post-offices/search/?query=Москва&kladr_id=7700000000000

    Ищет отделения Почты России:
    1. Сначала в локальной БД (PostgreSQL).
    2. Если в БД меньше 5 результатов — запрашивает DaData,
       сохраняет новые записи в БД и возвращает объединённый список.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('query', '').strip()
        kladr_id = request.query_params.get('kladr_id', '').strip()

        if not query:
            return Response(
                {'error': 'Параметр query обязателен.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Ищем в БД
        qs = PostOffice.objects.filter(is_closed=False)
        qs = qs.filter(address_str__icontains=query) | PostOffice.objects.filter(
            is_closed=False, postal_code__icontains=query
        )
        qs = qs.distinct()

        if kladr_id:
            # При наличии kladr_id дополнительно фильтруем по городу,
            # если он уже сохранён в БД.
            # Полноценно kladr_id работает только через DaData,
            # поэтому форсируем обновление.
            db_count = 0
        else:
            db_count = qs.count()

        # 2. Если в БД мало данных — идём в DaData
        if db_count < 5:
            try:
                suggestions = fetch_offices_from_dadata(
                    query=query,
                    city_kladr_id=kladr_id or None,
                    count=20,
                )
                for suggestion in suggestions:
                    parsed = parse_office(suggestion)
                    if not parsed['postal_code']:
                        continue
                    PostOffice.objects.update_or_create(
                        postal_code=parsed['postal_code'],
                        defaults=parsed,
                    )
            except Exception as e:
                # Не падаем — отдаём то, что есть в БД
                pass

            # Перечитываем из БД после обновления
            qs = PostOffice.objects.filter(is_closed=False)
            qs = (
                qs.filter(address_str__icontains=query)
                | PostOffice.objects.filter(is_closed=False, postal_code__icontains=query)
            ).distinct()

        serializer = PostOfficeSerializer(qs[:20], many=True)
        return Response(serializer.data)


class PostOfficeDetailView(APIView):
    """GET /api/post-offices/<postal_code>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, postal_code):
        try:
            office = PostOffice.objects.get(postal_code=postal_code)
        except PostOffice.DoesNotExist:
            return Response({'error': 'Отделение не найдено.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PostOfficeSerializer(office).data)
