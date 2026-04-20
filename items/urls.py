from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageUploadView
from django.urls import path

router = DefaultRouter()
router.register(r'', ItemViewSet, basename='items')

router = DefaultRouter()
router.register(r'', ItemViewSet, basename='items')

urlpatterns = [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
] + router.urls