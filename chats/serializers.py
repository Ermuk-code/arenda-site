from rest_framework import serializers
from .models import Message, Chat
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'sender_username', 'text', 'image', 'created_at', 'is_read']
        read_only_fields = ['id', 'sender', 'created_at']

class ChatSerializer(serializers.ModelSerializer):
    users = serializers.StringRelatedField(many=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'users', 'created_at', 'unread_count', 'last_message']

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {'text': msg.text, 'created_at': msg.created_at, 'sender': msg.sender.username}
        return None