from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from items.models import Item

User = get_user_model()

class Chat(models.Model):
    users = models.ManyToManyField(User)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

