from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone


@action(detail=True, methods=['post'])
def sign(self, request, pk=None):

    contract = self.get_object()

    contract.is_signed = True
    contract.signed_at = timezone.now()
    contract.save()

    return Response({"status": "contract signed"})