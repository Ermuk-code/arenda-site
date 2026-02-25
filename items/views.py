from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsProfileCompleted
from .models import Item
from .serializers import ItemSerializer

class ItemListCreateView(generics.ListCreateAPIView):

    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated, IsProfileCompleted]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)