from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageUploadView, ItemImageDeleteView, CategoryViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'', ItemViewSet, basename='items')

urlpatterns = [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
    path('images/<int:pk>/', ItemImageDeleteView.as_view(), name='delete-image'),
] + router.urls
