from django.urls import path
from .views import ConversationListCreateView, ConversationDetailView, ConversationMessageCreateView, MarkReadView, SupportFAQView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view()),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view()),
    path('conversations/<int:conversation_id>/messages/', ConversationMessageCreateView.as_view()),
    path('conversations/<int:conversation_id>/mark_read/', MarkReadView.as_view()),
    path('support-faq/', SupportFAQView.as_view()),
]
