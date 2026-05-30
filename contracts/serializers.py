from rest_framework import serializers
from .models import Contract


class ContractSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id',
            'booking',
            'file_url',
            'is_signed',
            'signed_by_renter',
            'signed_by_owner',
            'signed_at'
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None