import re
from rest_framework import serializers

def validate_inn(value):
    if not re.fullmatch(r'\d{10}|\d{12}', value):
        raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр.")
    return value
def validate_ogrn(value):
    if not re.fullmatch(r'\d{13}|\d{15}', value):
        raise serializers.ValidationError("ОГРН должен содержать 13 или 15 цифр.")
    return value
def validate_kpp(value):
    if not re.fullmatch(r'\d{9}', value):
        raise serializers.ValidationError("КПП должен содержать 9 цифр.")
    return value