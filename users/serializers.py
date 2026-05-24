from rest_framework import serializers
from .models import User
import re


# ---------------------------------------------------------------------------
# Валидаторы полей
# ---------------------------------------------------------------------------

def _luhn_inn10(inn: str) -> bool:
    """Контрольная цифра ИНН 10 знаков (для юрлиц)."""
    k = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    total = sum(k[i] * int(inn[i]) for i in range(9))
    return (total % 11 % 10) == int(inn[9])


def _luhn_inn12(inn: str) -> bool:
    """Контрольные цифры ИНН 12 знаков (для ИП / физлиц)."""
    k1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    k2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    n11 = (sum(k1[i] * int(inn[i]) for i in range(10)) % 11) % 10
    n12 = (sum(k2[i] * int(inn[i]) for i in range(11)) % 11) % 10
    return n11 == int(inn[10]) and n12 == int(inn[11])


def validate_inn(value: str) -> str:
    """
    Проверяет ИНН:
      - 10 цифр  → юридическое лицо (контрольная цифра)
      - 12 цифр  → ИП / физлицо (две контрольные цифры)
    """
    if value == '':
        return value
    if not re.fullmatch(r'\d{10}|\d{12}', value):
        raise serializers.ValidationError('ИНН должен содержать 10 (юрлицо) или 12 (ИП/физлицо) цифр.')
    if len(value) == 10 and not _luhn_inn10(value):
        raise serializers.ValidationError('ИНН юридического лица не прошёл проверку контрольной цифры.')
    if len(value) == 12 and not _luhn_inn12(value):
        raise serializers.ValidationError('ИНН ИП/физлица не прошёл проверку контрольных цифр.')
    return value


def validate_inn_legal(value: str) -> str:
    """ИНН строго для юрлица — ровно 10 цифр."""
    if value == '':
        return value
    if not re.fullmatch(r'\d{10}', value):
        raise serializers.ValidationError('ИНН юридического лица должен содержать ровно 10 цифр.')
    if not _luhn_inn10(value):
        raise serializers.ValidationError('ИНН юридического лица не прошёл проверку контрольной цифры.')
    return value


def validate_inn_entrepreneur(value: str) -> str:
    """ИНН строго для ИП — ровно 12 цифр."""
    if value == '':
        return value
    if not re.fullmatch(r'\d{12}', value):
        raise serializers.ValidationError('ИНН ИП должен содержать ровно 12 цифр.')
    if not _luhn_inn12(value):
        raise serializers.ValidationError('ИНН ИП не прошёл проверку контрольных цифр.')
    return value


def validate_kpp(value: str) -> str:
    """
    КПП: 9 символов, формат NNNNPPXXX
      NNNN — код налогового органа (4 цифры)
      PP   — причина постановки на учёт (2 цифры или буквы)
      XXX  — порядковый номер (3 цифры)
    """
    if value == '':
        return value
    if not re.fullmatch(r'\d{4}[\dA-Z]{2}\d{3}', value, re.IGNORECASE):
        raise serializers.ValidationError(
            'КПП должен содержать 9 символов в формате NNNNPPXXX '
            '(4 цифры кода ФНС + 2 знака причины + 3 цифры порядка).'
        )
    return value.upper()


def validate_ogrnip(value: str) -> str:
    """
    ОГРНИП: 15 цифр + контрольная цифра.
    Алгоритм: ОГРНИП[0:14] mod 13 mod 10 == ОГРНИП[14]
    """
    if value == '':
        return value
    if not re.fullmatch(r'\d{15}', value):
        raise serializers.ValidationError('ОГРНИП должен содержать ровно 15 цифр.')
    base = int(value[:14])
    check = base % 13 % 10
    if check != int(value[14]):
        raise serializers.ValidationError('ОГРНИП не прошёл проверку контрольной цифры.')
    return value


def validate_passport_series(value: str) -> str:
    if value == '':
        return value
    if not re.fullmatch(r'\d{4}', value):
        raise serializers.ValidationError('Серия паспорта — 4 цифры.')
    return value


def validate_passport_number(value: str) -> str:
    if value == '':
        return value
    if not re.fullmatch(r'\d{6}', value):
        raise serializers.ValidationError('Номер паспорта — 6 цифр.')
    return value


# ---------------------------------------------------------------------------
# Mixin: проверка заполненности профиля
# ---------------------------------------------------------------------------

class BaseUserDataMixin:
    def _is_profile_complete(self, user) -> bool:
        if user.user_type == 'individual':
            return bool(user.full_name and user.passport_series and user.passport_number and user.inn)
        if user.user_type == 'entrepreneur':
            return bool(user.entrepreneur_name and user.inn and user.ogrnip)
        if user.user_type == 'legal':
            return bool(user.company_name and user.inn and user.kpp)
        return False


# ---------------------------------------------------------------------------
# Серилизатор регистрации
# ---------------------------------------------------------------------------

class RegisterSerializer(BaseUserDataMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    entrepreneur_name = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    inn = serializers.CharField(required=False, allow_blank=True)
    kpp = serializers.CharField(required=False, allow_blank=True)
    ogrnip = serializers.CharField(required=False, allow_blank=True)
    passport_series = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_series])
    passport_number = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_number])

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'user_type',
            'full_name', 'entrepreneur_name', 'company_name',
            'passport_series', 'passport_number',
            'inn', 'kpp', 'ogrnip',
            'is_staff', 'is_superuser',
        ]
        read_only_fields = ['is_staff', 'is_superuser']

    def validate(self, data):
        if len(data.get('password', '')) < 6:
            raise serializers.ValidationError('Пароль должен содержать не менее 6 символов.')

        email = data.get('email', '')
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'Пользователь с таким email уже существует.'})

        user_type = data.get('user_type', 'individual')
        inn = data.get('inn', '')
        kpp = data.get('kpp', '')
        ogrnip = data.get('ogrnip', '')

        # Тип-зависимая валидация ИНН и других реквизитов
        if user_type == 'legal':
            if inn:
                validate_inn_legal(inn)
            if kpp:
                validate_kpp(kpp)

        elif user_type == 'entrepreneur':
            if inn:
                validate_inn_entrepreneur(inn)
            if ogrnip:
                validate_ogrnip(ogrnip)

        elif user_type == 'individual':
            if inn:
                validate_inn(inn)  # физлицо — 12 цифр, но не принуждаем здесь

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'individual'),
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


# ---------------------------------------------------------------------------
# Серилизатор профиля
# ---------------------------------------------------------------------------

class ProfileSerializer(BaseUserDataMixin, serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False, allow_blank=True)
    entrepreneur_name = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(required=False, allow_blank=True)
    inn = serializers.CharField(required=False, allow_blank=True)
    kpp = serializers.CharField(required=False, allow_blank=True)
    ogrnip = serializers.CharField(required=False, allow_blank=True)
    passport_series = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_series])
    passport_number = serializers.CharField(required=False, allow_blank=True, validators=[validate_passport_number])

    class Meta:
        model = User
        fields = [
            'username', 'email', 'user_type',
            'full_name', 'entrepreneur_name', 'company_name',
            'passport_series', 'passport_number',
            'inn', 'kpp', 'ogrnip',
            'is_staff', 'is_superuser',
        ]
        read_only_fields = ['is_staff', 'is_superuser']

    @staticmethod
    def _field_error(field: str, message: str):
        raise serializers.ValidationError({field: message})

    def validate(self, data):
        user_type = data.get('user_type', getattr(self.instance, 'user_type', None))

        # Строим объединённый словарь (текущие значения + новые)
        merged = {}
        if self.instance:
            for field in self.Meta.fields:
                merged[field] = getattr(self.instance, field, '')
        merged.update(data)

        # Проверка уникальности email
        email = merged.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'email': 'Пользователь с таким email уже существует.'})

        inn = merged.get('inn', '')
        kpp = merged.get('kpp', '')
        ogrnip = merged.get('ogrnip', '')

        # Тип-зависимая валидация обязательных полей и форматов
        if user_type == 'individual':
            if not merged.get('full_name'):
                self._field_error('full_name', 'Укажите ФИО.')
            if not merged.get('passport_series'):
                self._field_error('passport_series', 'Укажите серию паспорта.')
            if not merged.get('passport_number'):
                self._field_error('passport_number', 'Укажите номер паспорта.')
            if not inn:
                self._field_error('inn', 'Укажите ИНН.')
            else:
                validate_inn(inn)

        elif user_type == 'entrepreneur':
            if not merged.get('entrepreneur_name'):
                self._field_error('entrepreneur_name', 'Укажите наименование ИП.')
            if not inn:
                self._field_error('inn', 'Укажите ИНН.')
            else:
                validate_inn_entrepreneur(inn)
            if not ogrnip:
                self._field_error('ogrnip', 'Укажите ОГРНИП.')
            else:
                validate_ogrnip(ogrnip)

        elif user_type == 'legal':
            if not merged.get('company_name'):
                self._field_error('company_name', 'Укажите наименование организации.')
            if not inn:
                self._field_error('inn', 'Укажите ИНН.')
            else:
                validate_inn_legal(inn)
            if not kpp:
                self._field_error('kpp', 'Укажите КПП.')
            else:
                validate_kpp(kpp)

        return data

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.profile_completed = self._is_profile_complete(instance)
        instance.save()
        return instance
