from django.urls import path
from .views import MessageListView, ChatListView

urlpatterns = [
    path('', ChatListView.as_view()),
    path('<int:chat_id>/messages/', MessageListView.as_view()),
]