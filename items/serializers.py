from rest_framework import serializers
from .models import Item, ItemImage

class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'image']
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
    def validate(self, data):
        rent_type = data.get('rent_type')

        # 💥 Проверка цен
        if rent_type in ['hourly', 'both'] and not data.get('price_per_hour'):
            raise serializers.ValidationError("Укажите цену за час")

        if rent_type in ['daily', 'both'] and not data.get('price_per_day'):
            raise serializers.ValidationError("Укажите цену за день")

        # 💥 Нельзя отрицательные значения
        for field in ['price_per_hour', 'price_per_day', 'deposit', 'delivery_price']:
            value = data.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError(f"{field} не может быть отрицательным")

        return data
