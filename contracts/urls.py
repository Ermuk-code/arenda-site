from rest_framework.routers import DefaultRouter

from .views import ContractViewSet

router = DefaultRouter()
router.register(r'', ContractViewSet, basename='contracts')

urlpatterns = router.urls
