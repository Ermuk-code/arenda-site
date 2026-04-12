from django.urls import path
from .views import MessageListView

urlpatterns = [
    path('<int:chat_id>/messages/', MessageListView.as_view()),
]
