from rest_framework import serializers
from .models import Booking, Review
class ReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='booking.renter.username', read_only=True)
    item_id = serializers.IntegerField(source='booking.item_id', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'booking', 'item_id', 'rating', 'comment', 'created_at', 'author_username']
        read_only_fields = ['booking', 'item_id', 'created_at', 'author_username']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value

class BookingSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source='item.title', read_only=True)
    renter_username = serializers.CharField(source='renter.username', read_only=True)
    renter_email = serializers.EmailField(source='renter.email', read_only=True)
    has_review = serializers.SerializerMethodField()
    can_leave_review = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

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

    def get_can_leave_review(self, obj):
        if hasattr(obj, 'review'):
            return False

        return obj.status == 'completed' or (
            obj.status == 'confirmed' and
            obj.payment_status == 'paid'
        )

    def get_review(self, obj):
        if not hasattr(obj, 'review'):
            return None
        return ReviewSerializer(obj.review).data


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
