from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageUploadView, ItemVideoUploadView, CategoryViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'', ItemViewSet, basename='items')

urlpatterns = [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
    path('upload-video/', ItemVideoUploadView.as_view(), name='upload-video'),
] + router.urls
