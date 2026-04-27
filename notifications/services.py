from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from notifications.email import (
    send_booking_cancelled,
    send_booking_confirmed,
    send_booking_created,
    send_new_message,
    send_new_review,
    send_payment_confirmed,
    send_return_reminder,
)
from notifications.models import Notification
from notifications.serializers import NotificationSerializer


def create_notification(user, notification_type, message, metadata=None):
    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        message=message,
        metadata=metadata or {},
    )
    broadcast_notification(notification)
    return notification


def broadcast_notification(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.user_id}',
            {
                'type': 'notification_created',
                'notification': NotificationSerializer(notification).data,
            }
        )
    except Exception:
        # Realtime delivery is optional; notification creation must still succeed.
        return


def notify_booking_created(booking):
    notification = create_notification(
        user=booking.item.owner,
        notification_type='booking_created',
        message=f'Новая заявка на аренду товара «{booking.item.title}»',
        metadata={
            'destination': 'incoming_bookings',
            'booking_id': booking.id,
            'item_id': booking.item_id,
        },
    )
    send_booking_created(booking)
    return notification


def notify_booking_confirmed(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='booking_confirmed',
        message=f'Ваше бронирование товара «{booking.item.title}» подтверждено',
        metadata={
            'destination': 'rent_payment',
            'booking_id': booking.id,
            'item_id': booking.item_id,
        },
    )
    send_booking_confirmed(booking)
    return notification


def notify_payment_confirmed(booking):
    notification = create_notification(
        user=booking.item.owner,
        notification_type='payment_confirmed',
        message=f'Оплата за товар «{booking.item.title}» подтверждена',
        metadata={
            'destination': 'my_items',
            'booking_id': booking.id,
            'item_id': booking.item_id,
        },
    )
    send_payment_confirmed(booking)
    return notification


def notify_booking_cancelled(booking, cancelled_by):
    initiator_label = 'арендатором' if cancelled_by == booking.renter else 'владельцем'

    notifications = [
        create_notification(
            user=booking.item.owner,
            notification_type='booking_cancelled',
            message=f'Бронирование товара «{booking.item.title}» было отменено {initiator_label}',
            metadata={
                'destination': 'incoming_bookings',
                'booking_id': booking.id,
                'item_id': booking.item_id,
            },
        ),
        create_notification(
            user=booking.renter,
            notification_type='booking_cancelled',
            message=f'Бронирование товара «{booking.item.title}» было отменено {initiator_label}',
            metadata={
                'destination': 'item',
                'booking_id': booking.id,
                'item_id': booking.item_id,
            },
        ),
    ]
    send_booking_cancelled(booking, cancelled_by)
    return notifications


def notify_return_reminder(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='return_reminder',
        message=f'Напоминание: верните товар «{booking.item.title}» до {booking.end_date}',
        metadata={
            'destination': 'item',
            'booking_id': booking.id,
            'item_id': booking.item_id,
        },
    )
    send_return_reminder(booking)
    return notification


def notify_new_message(message):
    recipients = message.chat.users.exclude(id=message.sender_id)
    notifications = []

    for recipient in recipients:
        notifications.append(
            create_notification(
                user=recipient,
                notification_type='new_message',
                message=f'Пользователь {message.sender.username} отправил вам новое сообщение',
                metadata={
                    'destination': 'chat',
                    'chat_id': message.chat_id,
                    'item_id': message.chat.item_id,
                },
            )
        )
        send_new_message(recipient, message.sender.username)

    return notifications


def notify_new_review(review):
    review_message = f'Вы получили новый отзыв о товаре «{review.booking.item.title}». Оценка: {review.rating}/5'
    if review.comment:
        review_message += f'. Комментарий: {review.comment}'

    notification = create_notification(
        user=review.booking.item.owner,
        notification_type='new_review',
        message=review_message,
        metadata={
            'destination': 'item',
            'booking_id': review.booking_id,
            'item_id': review.booking.item_id,
            'review_id': review.id,
            'rating': review.rating,
            'comment': review.comment,
        },
    )
    send_new_review(review.booking)
    return notification
