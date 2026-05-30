from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import viewsets
from .models import Contract
from .serializers import ContractSerializer


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer

    def get_queryset(self):
        user = self.request.user

        return Contract.objects.filter(
            booking__renter=user
        ) | Contract.objects.filter(
            booking__item__owner=user
        )
    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):

        contract = self.get_object()
        user = request.user

        # 👇 кто подписывает
        if user == contract.booking.renter:
            contract.signed_by_renter = True

        elif user == contract.booking.item.owner:
            contract.signed_by_owner = True

        else:
            return Response({"error": "Not allowed"}, status=403)

        # 💥 если оба подписали
        if contract.signed_by_renter and contract.signed_by_owner:
            contract.is_signed = True
            contract.signed_at = timezone.now()

            # 🔥 меняем статус бронирования
            contract.booking.status = 'confirmed'
            contract.booking.save()

        contract.save()

        return Response({
            "status": "signed",
            "fully_signed": contract.is_signed
        })