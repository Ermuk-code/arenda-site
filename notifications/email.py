from django.core.mail import send_mail
from django.conf import settings


def _send(to_email, subject, message):
    """Базовая отправка. Если email пустой — молча пропускаем."""
    if not to_email:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as e:
        # Не роняем сервер если почта недоступна
        print(f"[EMAIL ERROR] {e}")


def send_booking_created(booking):
    """Арендодателю: новая заявка на бронирование"""
    owner = booking.item.owner
    renter = booking.renter
    _send(
        to_email=owner.email,
        subject=f"Новая заявка на аренду: {booking.item.title}",
        message=(
            f"Здравствуйте, {owner.username}!\n\n"
            f"Пользователь {renter.username} хочет арендовать «{booking.item.title}».\n"
            f"Даты: {booking.start_date} — {booking.end_date}\n"
            f"Сумма: {booking.total_price} руб.\n\n"
            f"Войдите на сайт, чтобы подтвердить или отклонить заявку.\n\n"
            f"С уважением, команда Mokitoki"
        )
    )


def send_booking_confirmed(booking):
    """Арендатору: бронирование подтверждено"""
    renter = booking.renter
    _send(
        to_email=renter.email,
        subject=f"Бронирование подтверждено: {booking.item.title}",
        message=(
            f"Здравствуйте, {renter.username}!\n\n"
            f"Ваше бронирование «{booking.item.title}» подтверждено.\n"
            f"Даты аренды: {booking.start_date} — {booking.end_date}\n"
            f"Итоговая сумма: {booking.total_price} руб.\n\n"
            f"Хорошей аренды!\n\n"
            f"С уважением, команда Mokitoki"
        )
    )


def send_payment_confirmed(booking):
    """Арендодателю: оплата по подтвержденной аренде прошла"""
    owner = booking.item.owner
    renter = booking.renter
    _send(
        to_email=owner.email,
        subject=f"Оплата подтверждена: {booking.item.title}",
        message=(
            f"Здравствуйте, {owner.username}!\n\n"
            f"Пользователь {renter.username} оплатил аренду «{booking.item.title}».\n"
            f"Даты: {booking.start_date} — {booking.end_date}\n"
            f"Сумма: {booking.total_price} руб.\n\n"
            f"Войдите на сайт, чтобы посмотреть детали бронирования.\n\n"
            f"С уважением, команда Mokitoki"
        )
    )


def send_booking_cancelled(booking, cancelled_by):
    """Обеим сторонам: бронирование отменено"""
    owner = booking.item.owner
    renter = booking.renter
    who = "арендатором" if cancelled_by == renter else "арендодателем"

    for user in [owner, renter]:
        _send(
            to_email=user.email,
            subject=f"Бронирование отменено: {booking.item.title}",
            message=(
                f"Здравствуйте, {user.username}!\n\n"
                f"Бронирование «{booking.item.title}» ({booking.start_date} — {booking.end_date}) "
                f"было отменено {who}.\n\n"
                f"С уважением, команда Mokitoki"
            )
        )


def send_return_reminder(booking):
    """Арендатору: напоминание о возврате (за 1 день до end_date)"""
    renter = booking.renter
    _send(
        to_email=renter.email,
        subject=f"Напоминание о возврате: {booking.item.title}",
        message=(
            f"Здравствуйте, {renter.username}!\n\n"
            f"Напоминаем, что завтра ({booking.end_date}) истекает срок аренды «{booking.item.title}».\n"
            f"Пожалуйста, не забудьте вернуть товар.\n\n"
            f"С уважением, команда Mokitoki"
        )
    )


def send_new_message(recipient, sender_username):
    """Получателю: новое сообщение в чате"""
    _send(
        to_email=recipient.email,
        subject="Новое сообщение на Mokitoki",
        message=(
            f"Здравствуйте, {recipient.username}!\n\n"
            f"Вам написал пользователь {sender_username}.\n"
            f"Войдите на сайт, чтобы ответить.\n\n"
            f"С уважением, команда Mokitoki"
        )
    )


def send_new_review(booking):
    """Арендодателю: новый отзыв"""
    owner = booking.item.owner
    renter = booking.renter
    _send(
        to_email=owner.email,
        subject=f"Новый отзыв о товаре: {booking.item.title}",
        message=(
            f"Здравствуйте, {owner.username}!\n\n"
            f"Пользователь {renter.username} оставил отзыв о «{booking.item.title}».\n"
            f"Войдите на сайт, чтобы посмотреть.\n\n"
            f"С уважением, команда Mokitoki"
        )
    )
