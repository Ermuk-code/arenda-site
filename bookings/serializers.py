from rest_framework import serializers
from .models import Booking, Review
from items.models import Item
from datetime import datetime

class BookingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['renter', 'status', 'total_price']
    def validate(self, data):

        start = data.get('start_date')
        end = data.get('end_date')
        rent_type = data.get('rent_type')
        item = data.get('item')

        if start >= end:
            raise serializers.ValidationError("Дата окончания должна быть позже начала")

        if rent_type == 'hourly' and not item.price_per_hour:
            raise serializers.ValidationError("У товара нет почасовой аренды")

        if rent_type == 'daily' and not item.price_per_day:
            raise serializers.ValidationError("У товара нет посуточной аренды")

        return data
    def to_representation(self, instance):
        data = super().to_representation(instance)

        item = instance.item

        data['price_breakdown'] = {
            'rent': float(instance.total_price - item.deposit - item.delivery_price),
            'deposit': float(item.deposit),
            'delivery': float(item.delivery_price),
        }

        return data
    def create(self, validated_data):
        user = self.context['request'].user
        item = validated_data['item']
        rent_type = validated_data['rent_type']

        start = validated_data['start_date']
        end = validated_data['end_date']

        duration = end - start

        # 💰 считаем цену
        if rent_type == 'hourly':
            hours = duration.total_seconds() / 3600
            base_price = hours * item.price_per_hour

        elif rent_type == 'daily':
            days = duration.days
            if duration.seconds > 0:
                days += 1  # округление вверх
            base_price = days * item.price_per_day

        # 💥 ИТОГО
        total_price = (
            base_price +
            item.delivery_price +
            item.deposit
        )

        booking = Booking.objects.create(
            renter=user,
            total_price=total_price,
            **validated_data
        )

        return booking

class ReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['booking']
class BookingCalculateSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    rent_type = serializers.ChoiceField(choices=['hourly', 'daily'])
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        return data

    def calculate(self):
        item = Item.objects.get(id=self.validated_data['item'])
        rent_type = self.validated_data['rent_type']

        start = self.validated_data['start_date']
        end = self.validated_data['end_date']

        duration = end - start

        # 💰 аренда
        if rent_type == 'hourly':
            hours = duration.total_seconds() / 3600
            rent_price = hours * float(item.price_per_hour)

        else:
            days = duration.days
            if duration.seconds > 0:
                days += 1
            rent_price = days * float(item.price_per_day)

        # 💥 итог
        return {
            "rent_price": round(rent_price, 2),
            "delivery": float(item.delivery_price),
            "deposit": float(item.deposit),
            "total": round(
                rent_price + float(item.delivery_price) + float(item.deposit),
                2
            )
        }