from rest_framework import serializers
from .models import Item, ItemImage, Category

class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'image']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ItemSerializer(serializers.ModelSerializer):
    images = ItemImageSerializer(many=True, read_only=True)
    owner_rating = serializers.DecimalField(
    source='owner.average_rating',
    max_digits=3,
    decimal_places=2,
    read_only=True
    )

    owner_reviews_count = serializers.IntegerField(
        source='owner.reviews_count',
        read_only=True
    )
    class Meta:
        model = Item
        fields = '__all__'
