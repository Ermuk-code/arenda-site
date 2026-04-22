from notifications.email import (
    send_booking_cancelled,
    send_booking_confirmed,
    send_booking_created,
    send_new_message,
    send_new_review,
    send_return_reminder,
)
from notifications.models import Notification


def create_notification(user, notification_type, message):
    return Notification.objects.create(
        user=user,
        type=notification_type,
        message=message,
    )


def notify_booking_created(booking):
    notification = create_notification(
        user=booking.item.owner,
        notification_type='booking_created',
        message=f"Новая заявка на аренду товара «{booking.item.title}»",
    )
    send_booking_created(booking)
    return notification


def notify_booking_confirmed(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='booking_confirmed',
        message=f"Ваше бронирование товара «{booking.item.title}» подтверждено",
    )
    send_booking_confirmed(booking)
    return notification


def notify_payment_confirmed(booking):
    return create_notification(
        user=booking.item.owner,
        notification_type='payment_confirmed',
        message=f"Оплата за товар «{booking.item.title}» подтверждена",
    )


def notify_booking_cancelled(booking, cancelled_by):
    initiator_label = 'арендатором' if cancelled_by == booking.renter else 'владельцем'

    notifications = [
        create_notification(
            user=booking.item.owner,
            notification_type='booking_cancelled',
            message=f"Бронирование товара «{booking.item.title}» было отменено {initiator_label}",
        ),
        create_notification(
            user=booking.renter,
            notification_type='booking_cancelled',
            message=f"Бронирование товара «{booking.item.title}» было отменено {initiator_label}",
        ),
    ]
    send_booking_cancelled(booking, cancelled_by)
    return notifications


def notify_return_reminder(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='return_reminder',
        message=f"Напоминание: верните товар «{booking.item.title}» до {booking.end_date}",
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
                message=f"Пользователь {message.sender.username} отправил вам новое сообщение",
            )
        )
        send_new_message(recipient, message.sender.username)

    return notifications


def notify_new_review(review):
    notification = create_notification(
        user=review.booking.item.owner,
        notification_type='new_review',
        message=f"Вы получили новый отзыв о товаре «{review.booking.item.title}»",
    )
    send_new_review(review.booking)
    return notification
