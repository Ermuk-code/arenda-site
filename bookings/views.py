from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Booking
from .serializers import BookingSerializer
from rest_framework.exceptions import ValidationError

class BookingViewSet(viewsets.ModelViewSet):

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(renter=self.request.user)

    def perform_create(self, serializer):
        item = serializer.validated_data['item']

        if item.owner == self.request.user:
            raise ValidationError("You cannot book your own item")

        if not self.request.user.profile_completed:
            raise ValidationError("Complete your profile before booking")

        serializer.save(renter=self.request.user)