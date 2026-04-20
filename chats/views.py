from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Message, Chat
from .serializers import MessageSerializer, ChatSerializer

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        # только участник чата видит сообщения
        chat = Chat.objects.filter(id=chat_id, users=self.request.user).first()
        if not chat:
            return Message.objects.none()
        # помечаем сообщения как прочитанные
        Message.objects.filter(chat=chat, is_read=False).exclude(
            sender=self.request.user
        ).update(is_read=True)
        return Message.objects.filter(chat_id=chat_id).order_by('created_at')

class ChatListView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(users=self.request.user).order_by('-created_at')