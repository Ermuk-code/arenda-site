from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from users.permissions import IsProfileCompleted
from .models import Item
from .permissions import IsOwner
from .serializers import ItemSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics
from .models import ItemImage
from .serializers import ItemImageSerializer
from .permissions import IsOwner

from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category
from .serializers import CategorySerializer

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
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

        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)

        return queryset
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['status']
    search_fields = ['title', 'description']
    ordering_fields = ['price_per_day', 'created_at', 'average_rating']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticatedOrReadOnly(), IsProfileCompleted()]
        return []

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
        bookings = item.bookings.filter(status__in=['pending', 'confirmed']).values('start_date', 'end_date')
        return Response([
            {
                'from': booking['start_date'].isoformat(),
                'to': booking['end_date'].isoformat(),
            }
            for booking in bookings
        ])

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
