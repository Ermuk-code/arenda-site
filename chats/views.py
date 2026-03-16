from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ConversationViewSet(ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            booking__item__owner=user
        ) | Conversation.objects.filter(
            booking__renter=user
        )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):

        conversation = self.get_object()

        Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)

        return Response({"status": "messages marked as read"})