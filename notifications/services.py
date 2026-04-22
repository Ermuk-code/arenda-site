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
        message=f"New booking request for {booking.item.title}",
    )
    send_booking_created(booking)
    return notification


def notify_booking_confirmed(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='booking_confirmed',
        message=f"Your booking for {booking.item.title} was confirmed",
    )
    send_booking_confirmed(booking)
    return notification


def notify_payment_confirmed(booking):
    return create_notification(
        user=booking.item.owner,
        notification_type='payment_confirmed',
        message=f"Payment for {booking.item.title} was confirmed",
    )


def notify_booking_cancelled(booking, cancelled_by):
    initiator_label = 'renter' if cancelled_by == booking.renter else 'owner'

    notifications = [
        create_notification(
            user=booking.item.owner,
            notification_type='booking_cancelled',
            message=f"Booking for {booking.item.title} was cancelled by the {initiator_label}",
        ),
        create_notification(
            user=booking.renter,
            notification_type='booking_cancelled',
            message=f"Booking for {booking.item.title} was cancelled by the {initiator_label}",
        ),
    ]
    send_booking_cancelled(booking, cancelled_by)
    return notifications


def notify_return_reminder(booking):
    notification = create_notification(
        user=booking.renter,
        notification_type='return_reminder',
        message=f"Reminder: return {booking.item.title} by {booking.end_date}",
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
                message=f"{message.sender.username} sent you a new message",
            )
        )
        send_new_message(recipient, message.sender.username)

    return notifications


def notify_new_review(review):
    notification = create_notification(
        user=review.booking.item.owner,
        notification_type='new_review',
        message=f"You received a new review for {review.booking.item.title}",
    )
    send_new_review(review.booking)
    return notification
