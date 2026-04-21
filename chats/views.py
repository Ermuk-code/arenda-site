from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notifications.services import notify_new_message
from .models import Message, Chat
from .serializers import MessageCreateSerializer, MessageSerializer, ChatSerializer

User = get_user_model()


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chats = Chat.objects.filter(users=request.user).order_by('-created_at')
        serializer = ChatSerializer(chats, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        participant_id = request.data.get('participant_id')
        if not participant_id:
            return Response({'error': 'participant_id required'}, status=400)
        try:
            other_user = User.objects.get(id=participant_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        if other_user == request.user:
            return Response({'error': 'Cannot chat with yourself'}, status=400)

        existing = Chat.objects.filter(users=request.user).filter(users=other_user)
        if existing.exists():
            chat = existing.first()
        else:
            chat = Chat.objects.create()
            chat.users.add(request.user, other_user)

        serializer = ChatSerializer(chat, context={'request': request})
        return Response(serializer.data, status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        chat = Chat.objects.filter(id=conversation_id, users=request.user).first()
        if not chat:
            return Response({'error': 'Not found'}, status=404)

        Message.objects.filter(chat=chat, is_read=False).exclude(
            sender=request.user
        ).update(is_read=True)

        messages = Message.objects.filter(chat=chat).order_by('created_at')
        other = chat.users.exclude(id=request.user.id).first()

        return Response({
            'id': chat.id,
            'other_user': {'id': other.id, 'username': other.username} if other else None,
            'messages': MessageSerializer(messages, many=True, context={'request': request}).data,
        })


class ConversationMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, conversation_id):
        chat = Chat.objects.filter(id=conversation_id, users=request.user).first()
        if not chat:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(chat=chat, sender=request.user)
        notify_new_message(message)

        response_serializer = MessageSerializer(message, context={'request': request})
        self._broadcast_message(chat.id, response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _broadcast_message(self, chat_id, message_data):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        async_to_sync(channel_layer.group_send)(
            f'chat_{chat_id}',
            {
                'type': 'chat_message',
                'message': message_data,
            }
        )


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        chat = Chat.objects.filter(id=conversation_id, users=request.user).first()
        if chat:
            Message.objects.filter(chat=chat, is_read=False).exclude(
                sender=request.user
            ).update(is_read=True)
        return Response({'status': 'ok'})
