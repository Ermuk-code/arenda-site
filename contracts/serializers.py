from rest_framework import serializers

from .models import Contract


class ContractSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source='booking.item.title', read_only=True)
    start_date = serializers.DateField(source='booking.start_date', read_only=True)
    end_date = serializers.DateField(source='booking.end_date', read_only=True)
    total_price = serializers.DecimalField(source='booking.total_price', max_digits=10, decimal_places=2, read_only=True)
    renter_username = serializers.CharField(source='booking.renter.username', read_only=True)
    owner_username = serializers.CharField(source='booking.item.owner.username', read_only=True)
    file_url = serializers.SerializerMethodField()
    preview_text = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    my_signed = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id',
            'booking',
            'document_number',
            'file_url',
            'preview_text',
            'status',
            'is_signed',
            'signed_at',
            'created_at',
            'item_title',
            'start_date',
            'end_date',
            'total_price',
            'renter_username',
            'owner_username',
            'renter_signer_name',
            'renter_signature_code',
            'renter_signed_at',
            'owner_signer_name',
            'owner_signature_code',
            'owner_signed_at',
            'my_role',
            'my_signed',
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_preview_text(self, obj):
        return obj.build_preview_text()

    def get_status(self, obj):
        if obj.is_signed:
            return 'signed'
        if obj.renter_signed_at or obj.owner_signed_at:
            return 'partially_signed'
        return 'draft'

    def get_my_role(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        if user == obj.booking.renter:
            return 'renter'
        if user == obj.booking.item.owner:
            return 'owner'
        return None

    def get_my_signed(self, obj):
        role = self.get_my_role(obj)
        if role == 'renter':
            return bool(obj.renter_signed_at)
        if role == 'owner':
            return bool(obj.owner_signed_at)
        return False


class ContractSignSerializer(serializers.Serializer):
    signer_name = serializers.CharField(max_length=255)
    certificate_pin = serializers.CharField(max_length=64)
