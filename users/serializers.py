from rest_framework import serializers
from .models import User
import re


# ===== ВАЛИДАТОРЫ =====

def validate_inn(value):
    if not re.fullmatch(r'\d{10}|\d{12}', value):
        raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр.")
    return value


def validate_kpp(value):
    if not re.fullmatch(r'\d{9}', value):
        raise serializers.ValidationError("КПП должен содержать 9 цифр.")
    return value


def validate_ogrnip(value):
    if not re.fullmatch(r'\d{15}', value):
        raise serializers.ValidationError("ОГРНИП должен содержать 15 цифр.")
    return value


def validate_passport_series(value):
    if not re.fullmatch(r'\d{4}', value):
        raise serializers.ValidationError("Серия паспорта — 4 цифры")
    return value


def validate_passport_number(value):
    if not re.fullmatch(r'\d{6}', value):
        raise serializers.ValidationError("Номер паспорта — 6 цифр")
    return value


# ===== REGISTER =====

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'user_type']

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
            user_type=validated_data.get('user_type')
        )
        return user


# ===== PROFILE =====

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    inn = serializers.CharField(required=False, validators=[validate_inn])
    kpp = serializers.CharField(required=False, validators=[validate_kpp])
    ogrnip = serializers.CharField(required=False, validators=[validate_ogrnip])

    passport_series = serializers.CharField(required=False, validators=[validate_passport_series])
    passport_number = serializers.CharField(required=False, validators=[validate_passport_number])

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'user_type',
            'passport_series',
            'passport_number',
            'inn',
            'kpp',
            'ogrnip'
        ]

    def validate(self, data):
        user_type = data.get('user_type', getattr(self.instance, 'user_type', None))
        email = data.get('email')

        if email:
            qs = User.objects.filter(email=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'email': 'Email already exists'})

        # 👤 Физ лицо
        if user_type == 'individual':
            if not data.get('passport_series'):
                raise serializers.ValidationError("Passport series required")
            if not data.get('passport_number'):
                raise serializers.ValidationError("Passport number required")
            if not data.get('inn'):
                raise serializers.ValidationError("INN required")

        # 🧑‍💼 ИП
        if user_type == 'entrepreneur':
            if not data.get('inn'):
                raise serializers.ValidationError("INN required")
            if not data.get('ogrnip'):
                raise serializers.ValidationError("OGRNIP required")

        # 🏢 Юр лицо
        if user_type == 'legal':
            if not data.get('inn'):
                raise serializers.ValidationError("INN required")
            if not data.get('kpp'):
                raise serializers.ValidationError("KPP required")

        return data

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.profile_completed = True
        instance.save()
        return instance
