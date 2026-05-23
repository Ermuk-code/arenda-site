from django.urls import path
from .views import PostOfficeSearchView, PostOfficeDetailView

urlpatterns = [
    path('search/', PostOfficeSearchView.as_view(), name='post-offices-search'),
    path('<str:postal_code>/', PostOfficeDetailView.as_view(), name='post-office-detail'),
]
