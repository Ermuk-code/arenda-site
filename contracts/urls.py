from rest_framework.routers import DefaultRouter
from .views import ContractViewSet

router = DefaultRouter()
router.register('', ContractViewSet)

urlpatterns = router.urls