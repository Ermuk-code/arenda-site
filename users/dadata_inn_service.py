"""
Сервис для работы с DaData API: поиск организаций и ИП по ИНН.
Используется для кнопки «Заполнить по ИНН» при регистрации/в профиле.
"""
import requests
from django.conf import settings


DADATA_FIND_BY_ID_PARTY = (
    'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party'
)


def _headers() -> dict:
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Token {settings.DADATA_API_KEY}',
        'X-Secret': settings.DADATA_SECRET_KEY,
    }


def find_party_by_inn(inn: str) -> list[dict]:
    """
    Находит юрлицо или ИП по ИНН через DaData.
    Возвращает список найденных записей (обычно 1-2).
    """
    payload = {'query': inn}
    resp = requests.post(
        DADATA_FIND_BY_ID_PARTY,
        json=payload,
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get('suggestions', [])


def parse_legal_entity(suggestion: dict) -> dict:
    """
    Разбирает запись DaData для юридического лица (ООО, АО и т.д.).
    Возвращает словарь с полями: company_name, inn, kpp.
    """
    data = suggestion.get('data') or {}
    return {
        'company_name': suggestion.get('value', '') or data.get('name', {}).get('full_with_opf', ''),
        'inn': data.get('inn', ''),
        'kpp': data.get('kpp', ''),
    }


def parse_entrepreneur(suggestion: dict) -> dict:
    """
    Разбирает запись DaData для индивидуального предпринимателя.
    Возвращает словарь с полями: entrepreneur_name, inn, ogrnip.
    """
    data = suggestion.get('data') or {}
    return {
        'entrepreneur_name': suggestion.get('value', '') or data.get('name', {}).get('full', ''),
        'inn': data.get('inn', ''),
        'ogrnip': data.get('ogrn', ''),
    }


def get_party_info(inn: str) -> dict:
    """
    Основная функция: по ИНН возвращает данные об организации или ИП.

    Возвращает словарь вида:
      {
        'type': 'legal' | 'entrepreneur' | None,
        'data': { ... } | None,
        'error': str | None,
      }

    Тип определяется по длине ИНН:
      - 10 цифр → юридическое лицо
      - 12 цифр → ИП (физическое лицо)
    """
    inn = (inn or '').strip()

    if not inn:
        return {'type': None, 'data': None, 'error': 'ИНН не передан'}

    if len(inn) not in (10, 12) or not inn.isdigit():
        return {'type': None, 'data': None, 'error': 'Некорректный ИНН'}

    try:
        suggestions = find_party_by_inn(inn)
    except requests.RequestException as exc:
        return {'type': None, 'data': None, 'error': f'Ошибка запроса к DaData: {exc}'}

    if not suggestions:
        return {'type': None, 'data': None, 'error': 'Организация не найдена'}

    suggestion = suggestions[0]
    party_type = (suggestion.get('data') or {}).get('type', '')

    # DaData возвращает: LEGAL — юрлицо, INDIVIDUAL — ИП
    if party_type == 'LEGAL':
        return {
            'type': 'legal',
            'data': parse_legal_entity(suggestion),
            'error': None,
        }
    elif party_type == 'INDIVIDUAL':
        return {
            'type': 'entrepreneur',
            'data': parse_entrepreneur(suggestion),
            'error': None,
        }
    else:
        # Попытка определить по длине ИНН как запасной вариант
        if len(inn) == 10:
            return {
                'type': 'legal',
                'data': parse_legal_entity(suggestion),
                'error': None,
            }
        else:
            return {
                'type': 'entrepreneur',
                'data': parse_entrepreneur(suggestion),
                'error': None,
            }
