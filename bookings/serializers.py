from rest_framework import serializers
from .models import Booking, Review

class BookingSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source='item.title', read_only=True)
    renter_username = serializers.CharField(source='renter.username', read_only=True)
    renter_email = serializers.EmailField(source='renter.email', read_only=True)
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = [
            'renter',
            'status',
            'total_price',
            'payment_method',
            'payment_status',
            'payment_reference',
            'payment_expires_at',
            'paid_at',
        ]

    def get_has_review(self, obj):
        return hasattr(obj, 'review')


class BookingPaymentSerializer(serializers.Serializer):
    provider = serializers.CharField()
    booking_id = serializers.IntegerField()
    payment_method = serializers.CharField()
    payment_status = serializers.CharField()
    payment_reference = serializers.CharField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    expires_at = serializers.CharField(allow_null=True)
    bank_name = serializers.CharField()
    recipient = serializers.CharField()
    phone_number = serializers.CharField()
    deeplink = serializers.CharField()
    qr_payload = serializers.CharField()

class ReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['booking']
