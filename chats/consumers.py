import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation
from .models import Message

@database_sync_to_async
def create_message(user, conversation_id, text):

    conversation = Conversation.objects.get(id=conversation_id)

    return Message.objects.create(
        conversation=conversation,
        sender=user,
        text=text
    )

class ChatConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def is_user_in_conversation(user, conversation_id):

        try:
            conversation = Conversation.objects.get(id=conversation_id)

            return (
                conversation.booking.renter == user
                or conversation.booking.item.owner == user
            )

        except Conversation.DoesNotExist:
            return False
    async def connect(self):

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close()
            return

        allowed = await is_user_in_conversation(user, self.conversation_id)

        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):

        data = json.loads(text_data)
        message = data['message']

        user = self.scope["user"]

        msg = await create_message(user, self.conversation_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': user.username,
                'message_id': msg.id
            }
        )

    async def chat_message(self, event):

        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'message_id': event['message_id']
        }))