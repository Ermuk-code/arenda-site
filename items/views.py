from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from users.permissions import IsProfileCompleted

from .models import Category, Item, ItemImage
from .permissions import IsOwner
from .serializers import CategorySerializer, ItemImageSerializer, ItemSerializer

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.order_by('name')
    serializer_class = CategorySerializer

class ItemViewSet(viewsets.ModelViewSet):

    serializer_class = ItemSerializer

    def get_queryset(self):

        user = self.request.user

        if user.is_authenticated:
            queryset = Item.objects.filter(
                models.Q(status='available') | models.Q(owner=user)
            )
        else:
            queryset = Item.objects.filter(status='available')

        min_rating = self.request.query_params.get('min_rating')
        mine = self.request.query_params.get('mine')

        if mine in ['1', 'true', 'True'] and user.is_authenticated:
            queryset = queryset.filter(owner=user)

        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)

        return queryset.select_related('owner', 'category').distinct()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['status', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['price_per_day', 'created_at', 'average_rating']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwner(), IsProfileCompleted()]
        if self.action == 'create':
            return [IsAuthenticatedOrReadOnly(), IsProfileCompleted()]
        return []

    @action(detail=True, methods=['get'])
    def booked_ranges(self, request, pk=None):
        item = self.get_object()
        active_bookings = item.bookings.filter(status__in=['pending', 'confirmed']).order_by('start_date')
        return Response(
            [
                {
                    'start_date': booking.start_date.isoformat(),
                    'end_date': booking.end_date.isoformat(),
                }
                for booking in active_bookings
            ]
        )

class ItemImageUploadView(generics.CreateAPIView):
    serializer_class = ItemImageSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        item_id = self.request.data.get('item')
        if not item_id:
            raise ValidationError({'item': ['This field is required.']})

        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            raise ValidationError({'item': ['Invalid item id.']})

        if item.owner != self.request.user:
            raise PermissionDenied("You are not the owner of this item")

        serializer.save(item=item)


class ItemImageDeleteView(generics.DestroyAPIView):
    serializer_class = ItemImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ItemImage.objects.filter(item__owner=self.request.user)
