from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageUploadView, BookingCalculateView, CategoryViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'', ItemViewSet, basename='items')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = router.urls + [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
    path('calculate/', BookingCalculateView.as_view()),
]