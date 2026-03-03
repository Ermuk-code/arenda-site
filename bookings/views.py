from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Booking
from .serializers import BookingSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

class BookingViewSet(viewsets.ModelViewSet):

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(renter=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()

        if booking.item.owner != request.user:
            return Response(
                {"error": "Only owner can confirm"},
                status=403
            )

        try:
            booking.change_status('confirmed')
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

        return Response({"status": "Booking confirmed"})
    def perform_create(self, serializer):
        item = serializer.validated_data['item']

        if item.owner == self.request.user:
            raise ValidationError("You cannot book your own item")

        if not self.request.user.profile_completed:
            raise ValidationError("Complete your profile before booking")

        serializer.save(renter=self.request.user)