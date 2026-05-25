import requests
from django.conf import settings


DADATA_SUGGEST_URL = (
    'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/postal_unit'
)


def _headers():
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Token {settings.DADATA_API_KEY}',
    }


def fetch_offices_from_dadata(query: str, city_kladr_id: str = None, count: int = 20) -> list[dict]:
    """
    Запрашивает отделения Почты России из DaData.
    query          — поисковая строка (адрес, индекс, название города)
    city_kladr_id  — КЛАДР-код города для фильтрации (опционально)
    count          — максимальное число результатов (макс. 20 у DaData)
    """
    payload = {
        'query': query,
        'count': count,
        'filters': [{'is_closed': False}],
    }
    if city_kladr_id:
        payload['filters'].append({'address_kladr_id': city_kladr_id})

    resp = requests.post(DADATA_SUGGEST_URL, json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get('suggestions', [])


def parse_office(suggestion: dict) -> dict:
    """Преобразует запись DaData в словарь для модели PostOffice."""
    data = suggestion.get('data') or {}
    address = suggestion.get('unrestricted_value', '') or data.get('address_str', '')

    # Пытаемся извлечь регион и город из адресной строки
    parts = [p.strip() for p in address.split(',')]
    region = parts[0] if len(parts) > 0 else ''
    city = ''
    for part in parts:
        low = part.lower()
        if 'г.' in low or 'город' in low or 'г ' in low:
            city = part.replace('г.', '').replace('г ', '').strip()
            break
    if not city and len(parts) > 1:
        city = parts[1]

    return {
        'postal_code': data.get('postal_code', ''),
        'address_str': address,
        'region': region,
        'city': city,
        'is_closed': bool(data.get('is_closed', False)),
        'type_code': str(data.get('type_code', '')),
        'geo_lat': data.get('geo_lat') or None,
        'geo_lon': data.get('geo_lon') or None,
        'schedule_mon': data.get('schedule_mon') or '',
        'schedule_tue': data.get('schedule_tue') or '',
        'schedule_wed': data.get('schedule_wed') or '',
        'schedule_thu': data.get('schedule_thu') or '',
        'schedule_fri': data.get('schedule_fri') or '',
        'schedule_sat': data.get('schedule_sat') or '',
        'schedule_sun': data.get('schedule_sun') or '',
    }
