from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking

from .models import Contract
from .serializers import ContractSerializer, ContractSignSerializer


class ContractViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Contract.objects.filter(
            Q(booking__renter=user) | Q(booking__item__owner=user)
        ).select_related('booking', 'booking__renter', 'booking__item', 'booking__item__owner')

    def _get_participant_booking(self, booking_id):
        return Booking.objects.select_related('item', 'item__owner', 'renter').filter(
            booking_participants_filter(self.request.user),
            id=booking_id,
        ).first()

    @action(detail=False, methods=['get'], url_path=r'by-booking/(?P<booking_id>\d+)')
    def by_booking(self, request, booking_id=None):
        booking = self._get_participant_booking(booking_id)
        if not booking:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status not in ['confirmed', 'completed']:
            return Response(
                {'error': 'Contract is available only after booking confirmation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contract = Contract.create_for_booking(booking)
        serializer = self.get_serializer(contract)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        contract = self.get_object()
        serializer = ContractSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            contract.sign_for_user(
                request.user,
                signer_name=serializer.validated_data['signer_name'],
                certificate_pin=serializer.validated_data['certificate_pin'],
            )
        except DjangoValidationError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        output = self.get_serializer(contract)
        return Response(output.data, status=status.HTTP_200_OK)


def booking_participants_filter(user):
    from django.db.models import Q

    return Q(renter=user) | Q(item__owner=user)
