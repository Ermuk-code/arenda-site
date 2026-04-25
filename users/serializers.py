from rest_framework import serializers
from .models import User
import re


def validate_inn(value):
    if value == '':
        return value
    if not re.fullmatch(r'\d{10}|\d{12}', value):
        raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр.")
    return value


def validate_kpp(value):
    if value == '':
        return value
    if not re.fullmatch(r'\d{9}', value):
        raise serializers.ValidationError("КПП должен содержать 9 цифр.")
    return value


def validate_ogrnip(value):
    if value == '':
        return value
    if not re.fullmatch(r'\d{15}', value):
        raise serializers.ValidationError("ОГРНИП должен содержать 15 цифр.")
    return value


def validate_passport_series(value):
    if value == '':
        return value
    if not re.fullmatch(r'\d{4}', value):
        raise serializers.ValidationError("Серия паспорта — 4 цифры")
    return value


def validate_passport_number(value):
    if value == '':
        return value
    if not re.fullmatch(r'\d{6}', value):
        raise serializers.ValidationError("Номер паспорта — 6 цифр")
    return value


class BaseUserDataMixin:
    def _is_profile_complete(self, user):
        if user.user_type == 'individual':
            return bool(user.full_name and user.passport_series and user.passport_number and user.inn)
        if user.user_type == 'entrepreneur':
            return bool(user.entrepreneur_name and user.inn and user.ogrnip)
        if user.user_type == 'legal':
            return bool(user.company_name and user.inn and user.kpp)
        return False


class RegisterSerializer(BaseUserDataMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    entrepreneur_name = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    inn = serializers.CharField(required=False, allow_blank=True, validators=[validate_inn])
    kpp = serializers.CharField(required=False, allow_blank=True, validators=[validate_kpp])
    ogrnip = serializers.CharField(required=False, allow_blank=True, validators=[validate_ogrnip])
    passport_series = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_series])
    passport_number = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_number])

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'user_type',
            'full_name',
            'entrepreneur_name',
            'company_name',
            'passport_series',
            'passport_number',
            'inn',
            'kpp',
            'ogrnip',
        ]

    def validate(self, data):
        if len(data['password']) < 6:
            raise serializers.ValidationError("Password too short")

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists")

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type'),
            full_name=validated_data.get('full_name', ''),
            entrepreneur_name=validated_data.get('entrepreneur_name', ''),
            company_name=validated_data.get('company_name', ''),
            passport_series=validated_data.get('passport_series', ''),
            passport_number=validated_data.get('passport_number', ''),
            inn=validated_data.get('inn', ''),
            kpp=validated_data.get('kpp', ''),
            ogrnip=validated_data.get('ogrnip', ''),
        )
        user.profile_completed = self._is_profile_complete(user)
        user.save(update_fields=['profile_completed'])
        return user


class ProfileSerializer(BaseUserDataMixin, serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False, allow_blank=True)
    entrepreneur_name = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    inn = serializers.CharField(required=False, allow_blank=True, validators=[validate_inn])
    kpp = serializers.CharField(required=False, allow_blank=True, validators=[validate_kpp])
    ogrnip = serializers.CharField(required=False, allow_blank=True, validators=[validate_ogrnip])
    passport_series = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_series])
    passport_number = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_number])

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'user_type',
            'full_name',
            'entrepreneur_name',
            'company_name',
            'passport_series',
            'passport_number',
            'inn',
            'kpp',
            'ogrnip',
        ]

    @staticmethod
    def _field_error(field, message):
        raise serializers.ValidationError({field: message})

    def validate(self, data):
        user_type = data.get('user_type', getattr(self.instance, 'user_type', None))
        merged = {}
        if self.instance:
            for field in self.Meta.fields:
                merged[field] = getattr(self.instance, field, '')
        merged.update(data)

        email = merged.get('email')
        if email:
            qs = User.objects.filter(email=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"email": "Email already exists"})

        if user_type == 'individual':
            if not merged.get('full_name'):
                self._field_error('full_name', 'Full name required')
            if not merged.get('passport_series'):
                self._field_error('passport_series', 'Passport series required')
            if not merged.get('passport_number'):
                self._field_error('passport_number', 'Passport number required')
            if not merged.get('inn'):
                self._field_error('inn', 'INN required')

        if user_type == 'entrepreneur':
            if not merged.get('entrepreneur_name'):
                self._field_error('entrepreneur_name', 'Entrepreneur name required')
            if not merged.get('inn'):
                self._field_error('inn', 'INN required')
            if not merged.get('ogrnip'):
                self._field_error('ogrnip', 'OGRNIP required')

        if user_type == 'legal':
            if not merged.get('company_name'):
                self._field_error('company_name', 'Company name required')
            if not merged.get('inn'):
                self._field_error('inn', 'INN required')
            if not merged.get('kpp'):
                self._field_error('kpp', 'KPP required')

        return data

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.profile_completed = self._is_profile_complete(instance)
        instance.save()
        return instance
