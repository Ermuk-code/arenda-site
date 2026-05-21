from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.email import (
    send_item_moderation_approved,
    send_item_moderation_rejected,
    send_item_moderation_request_to_admins,
)
from notifications.services import create_notification

from .models import ItemModerationRequest


def build_item_snapshot(item):
    return {
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'price_per_day': str(item.price_per_day),
        'status': item.status,
        'category': item.category.name if item.category else None,
        'category_id': item.category_id,
        'created_at': item.created_at.isoformat() if item.created_at else None,
    }


def build_user_snapshot(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'user_type': user.user_type,
        'full_name': user.full_name,
        'entrepreneur_name': user.entrepreneur_name,
        'company_name': user.company_name,
        'passport_series': user.passport_series,
        'passport_number': user.passport_number,
        'inn': user.inn,
        'kpp': user.kpp,
        'ogrnip': user.ogrnip,
        'profile_completed': user.profile_completed,
    }


def create_item_moderation_request(item, submitted_by, action):
    ItemModerationRequest.objects.filter(
        item=item,
        status=ItemModerationRequest.STATUS_PENDING,
    ).update(status=ItemModerationRequest.STATUS_REJECTED, rejection_reason='Заменена новой заявкой')

    request = ItemModerationRequest.objects.create(
        item=item,
        submitted_by=submitted_by,
        action=action,
        item_snapshot=build_item_snapshot(item),
        user_snapshot=build_user_snapshot(submitted_by),
    )
    notify_item_moderation_request(request)
    return request


def notify_item_moderation_request(moderation_request):
    User = get_user_model()
    admins = User.objects.filter(is_superuser=True, is_active=True)
    message = (
        f'Новая заявка на модерацию #{moderation_request.id}: '
        f'«{moderation_request.item.title}» от пользователя {moderation_request.submitted_by.username}'
    )

    for admin in admins:
        create_notification(
            user=admin,
            notification_type='item_moderation_request',
            message=message,
            metadata={
                'destination': 'item_moderation',
                'request_id': moderation_request.id,
                'item_id': moderation_request.item_id,
                'action': moderation_request.action,
            },
        )

    send_item_moderation_request_to_admins(moderation_request, admins)


def approve_item_moderation_request(moderation_request, admin):
    if moderation_request.item is None:
        return moderation_request

    moderation_request.item.status = 'available'
    moderation_request.item.save(update_fields=['status'])

    moderation_request.status = ItemModerationRequest.STATUS_APPROVED
    moderation_request.reviewed_by = admin
    moderation_request.reviewed_at = timezone.now()
    moderation_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

    create_notification(
        user=moderation_request.submitted_by,
        notification_type='item_moderation_approved',
        message=f'Ваше объявление «{moderation_request.item.title}» одобрено и опубликовано.',
        metadata={
            'destination': 'item',
            'request_id': moderation_request.id,
            'item_id': moderation_request.item_id,
        },
    )
    send_item_moderation_approved(moderation_request.submitted_by, moderation_request.item.title)
    return moderation_request


def reject_item_moderation_request(moderation_request, admin, reason):
    owner = moderation_request.submitted_by
    item = moderation_request.item
    title = item.title if item else moderation_request.item_snapshot.get('title', 'объявление')
    moderation_request.status = ItemModerationRequest.STATUS_REJECTED
    moderation_request.rejection_reason = reason
    moderation_request.reviewed_by = admin
    moderation_request.reviewed_at = timezone.now()
    moderation_request.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at', 'updated_at'])

    send_item_moderation_rejected(owner, title, reason)
    create_notification(
        user=owner,
        notification_type='item_moderation_rejected',
        message=f'Вам отказано в публикации объявления под названием «{title}» . Причина: {reason}',
        metadata={
            'destination': 'my_items',
            'request_id': moderation_request.id,
            'item_id': item.id if item else None,
            'reason': reason,
        },
    )
    if item is not None:
        item.delete()
    return moderation_request
