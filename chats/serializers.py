from rest_framework import serializers
from .models import Message, Chat
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    image = serializers.ImageField(read_only=True, use_url=True)

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender_id', 'sender_username', 'text', 'image', 'created_at', 'is_read']
        read_only_fields = ['id', 'sender_id', 'sender_username', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text', 'image']

    def validate(self, attrs):
        text = (attrs.get('text') or '').strip()
        image = attrs.get('image')

        if not text and not image:
            raise serializers.ValidationError('Message must contain text or image.')

        attrs['text'] = text
        return attrs


class ChatSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'other_user', 'created_at', 'unread_count', 'last_message']

    def get_other_user(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        other = obj.users.exclude(id=request.user.id).first()
        if other:
            return {'id': other.id, 'username': other.username}
        return None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'text': msg.text or ('[Изображение]' if msg.image else ''),
                'image': msg.image.url if msg.image else None,
                'created_at': msg.created_at.isoformat(),
                'sender': msg.sender.username
            }
        return None
