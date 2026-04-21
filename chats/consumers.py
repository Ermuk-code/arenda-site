import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from notifications.services import notify_new_message

from .models import Chat, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'

        if not await self.chat_exists():
            await self.close()
            return
        if not await self.is_chat_member():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message', '').strip()
        if not message_text:
            return

        user = self.scope['user']
        message = await self.save_message(user, message_text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': await self.serialize_message(message),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @sync_to_async
    def save_message(self, user, text):
        chat = Chat.objects.get(id=self.chat_id)
        message = Message.objects.create(chat=chat, sender=user, text=text)
        notify_new_message(message)
        return message

    @sync_to_async
    def serialize_message(self, message):
        return {
            'id': message.id,
            'chat': message.chat_id,
            'sender_id': message.sender_id,
            'sender_username': message.sender.username,
            'text': message.text,
            'image': message.image.url if message.image else None,
            'created_at': message.created_at.isoformat(),
            'is_read': message.is_read,
        }

    @sync_to_async
    def chat_exists(self):
        return Chat.objects.filter(id=self.chat_id).exists()

    @sync_to_async
    def is_chat_member(self):
        try:
            chat = Chat.objects.get(id=self.chat_id)
            return chat.users.filter(id=self.scope['user'].id).exists()
        except Chat.DoesNotExist:
            return False
