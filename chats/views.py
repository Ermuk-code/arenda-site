from rest_framework import generics
from .models import Message
from .serializers import MessageSerializer


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        return Message.objects.filter(chat_id=chat_id).order_by('created_at')
