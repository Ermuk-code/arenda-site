from rest_framework import serializers
from .models import PostOffice


class PostOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostOffice
        fields = [
            'id',
            'postal_code',
            'address_str',
            'region',
            'city',
            'is_closed',
            'type_code',
            'geo_lat',
            'geo_lon',
            'schedule_mon',
            'schedule_tue',
            'schedule_wed',
            'schedule_thu',
            'schedule_fri',
            'schedule_sat',
            'schedule_sun',
        ]