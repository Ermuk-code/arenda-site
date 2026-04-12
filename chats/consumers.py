import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import Chat, Message
from asgiref.sync import sync_to_async

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print(f"🔍 WebSocket connect attempt")
        print(f"🔍 User: {self.scope['user']}")
        print(f"🔍 User is anonymous: {self.scope['user'].is_anonymous}")

        if self.scope["user"].is_anonymous:
            print("❌ Rejecting anonymous user")
            await self.close()
            return

        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'

        chat_exists = await self.chat_exists()
        if not chat_exists:
            print(f"❌ Chat {self.chat_id} does not exist")
            await self.close()
            return

        is_member = await self.is_chat_member()
        if not is_member:
            print(f"❌ User is not a member of chat {self.chat_id}")
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f"✅ WebSocket connected to chat {self.chat_id}")

    async def disconnect(self, close_code):
        print(f"🔌 WebSocket disconnected: {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print(f"📨 Received: {text_data}")
        data = json.loads(text_data)
        message_text = data.get('message', '')
        user = self.scope["user"]

        message = await self.save_message(user, message_text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message.text,
                'user': user.username,
                'user_id': user.id,
                'timestamp': str(message.created_at),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def save_message(self, user, text):
        chat = Chat.objects.get(id=self.chat_id)
        return Message.objects.create(
            chat=chat,
            sender=user,
            text=text
        )

    @sync_to_async
    def chat_exists(self):
        return Chat.objects.filter(id=self.chat_id).exists()

    @sync_to_async
    def is_chat_member(self):
        try:
            chat = Chat.objects.get(id=self.chat_id)
            return chat.users.filter(id=self.scope["user"].id).exists()
        except Chat.DoesNotExist:
            return False