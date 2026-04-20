from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageUploadView, CategoryViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'', ItemViewSet, basename='items')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
] + router.urls