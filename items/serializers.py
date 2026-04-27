from rest_framework import serializers

from .models import Item, ItemImage, ItemVideo, Category, ItemReview

class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'image']


class ItemVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVideo
        fields = ['id', 'video']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ItemSerializer(serializers.ModelSerializer):
    images = ItemImageSerializer(many=True, read_only=True)
    videos = ItemVideoSerializer(many=True, read_only=True)
    booked_ranges = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    item_reviews = serializers.SerializerMethodField()
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

    def get_booked_ranges(self, obj):
        active_bookings = obj.bookings.filter(status__in=['pending', 'confirmed']).order_by('start_date')
        return [
            {
                'start_date': booking.start_date.isoformat(),
                'end_date': booking.end_date.isoformat(),
            }
            for booking in active_bookings
        ]

    def get_item_reviews(self, obj):
        from bookings.models import Review

        reviews = Review.objects.filter(
            booking__item=obj
        ).select_related('booking__renter').order_by('-created_at')[:6]

        return [
            {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat(),
                'author_username': review.booking.renter.username,
            }
            for review in reviews
        ]


class ItemReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = ItemReview
        fields = ['id', 'item', 'author', 'author_username', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'item', 'author', 'author_username', 'created_at']
