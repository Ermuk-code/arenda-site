from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer, ReviewSerializer

class BookingViewSet(viewsets.ModelViewSet):

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = Booking.objects.filter(
            Q(renter=self.request.user) | Q(item__owner=self.request.user)
        ).select_related('item', 'renter', 'item__owner').distinct().order_by('-created_at')

        role = self.request.query_params.get('role')
        if role == 'incoming':
            return queryset.filter(item__owner=self.request.user)
        if role == 'outgoing':
            return queryset.filter(renter=self.request.user)

        return queryset

    def _validation_error_payload(self, error):
        if hasattr(error, 'message_dict'):
            return error.message_dict
        if hasattr(error, 'messages'):
            return error.messages
        return str(error)

    def _change_status(self, booking, new_status):
        try:
            booking._status_changed_by = self.request.user
            booking.change_status(new_status)
        except DjangoValidationError as error:
            raise ValidationError(self._validation_error_payload(error)) from error

        serializer = self.get_serializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()

        if booking.item.owner != request.user:
            return Response(
                {"error": "Only owner can confirm"},
                status=status.HTTP_403_FORBIDDEN
            )

        return self._change_status(booking, 'confirmed')

    def perform_create(self, serializer):
        item = serializer.validated_data['item']

        if item.owner == self.request.user:
            raise ValidationError("You cannot book your own item")

        if not self.request.user.profile_completed:
            raise ValidationError("Complete your profile before booking")

        try:
            serializer.save(renter=self.request.user)
        except DjangoValidationError as error:
            raise ValidationError(self._validation_error_payload(error)) from error

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if request.user not in [booking.renter, booking.item.owner]:
            return Response(
                {"error": "Only booking participants can cancel"},
                status=status.HTTP_403_FORBIDDEN
            )

        return self._change_status(booking, 'cancelled')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()

        if booking.item.owner != request.user:
            return Response(
                {"error": "Only owner can complete booking"},
                status=status.HTTP_403_FORBIDDEN
            )

        return self._change_status(booking, 'completed')

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):

        booking = self.get_object()

        if booking.renter != request.user:
            return Response(
                {"error": "Only renter can leave review"},
                status=status.HTTP_403_FORBIDDEN
            )

        if hasattr(booking, 'review'):
            return Response(
                {"error": "Review already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save(booking=booking)
        except DjangoValidationError as error:
            raise ValidationError(self._validation_error_payload(error)) from error

        return Response(serializer.data, status=status.HTTP_201_CREATED)
