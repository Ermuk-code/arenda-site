from rest_framework.routers import DefaultRouter
from .views import ItemViewSet
from django.urls import path
from .views import ItemImageUploadView

router = DefaultRouter()
router.register(r'', ItemViewSet, basename='items')

urlpatterns = router.urls + [
    path('upload-image/', ItemImageUploadView.as_view(), name='upload-image'),
]