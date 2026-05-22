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
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None),
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as e:
        # Не роняем сервер если почта недоступна
        print(f"[EMAIL ERROR] {e}")


def send_password_reset_code(user, code):
    """Письмо с кодом восстановления пароля."""
    _send(
        to_email=user.email,
        subject='Код для восстановления пароля',
        message=(
            f'Здравствуйте, {user.username}!\n\n'
            f'Ваш код для восстановления пароля: {code}\n'
            'Код действует 15 минут.\n\n'
            'Если это были не вы, просто проигнорируйте это письмо.'
        )
    )


def send_item_moderation_request_to_admins(moderation_request, admins):
    item = moderation_request.item
    owner = moderation_request.submitted_by
    action_label = 'создание' if moderation_request.action == 'create' else 'редактирование'
    subject = f"Новая заявка на модерацию объявления: {item.title}"
    message = (
        f"Заявка на модерацию #{moderation_request.id}\n\n"
        f"Действие: {action_label}\n"
        f"Объявление: {item.title}\n"
        f"Цена за день: {item.price_per_day} руб.\n"
        f"Категория: {item.category.name if item.category else 'Без категории'}\n\n"
        f"Пользователь: {owner.username}\n"
        f"Email: {owner.email}\n"
        f"Телефон: {owner.phone or 'не указан'}\n"
        f"Тип пользователя: {owner.user_type}\n\n"
        "Откройте раздел модерации на сайте, чтобы одобрить или отклонить заявку."
    )
    for admin in admins:
        _send(admin.email, subject, message)


def send_item_moderation_approved(user, item_title):
    _send(
        to_email=user.email,
        subject=f"Объявление одобрено: {item_title}",
        message=(
            f"Здравствуйте, {user.username}!\n\n"
            f"Ваше объявление «{item_title}» одобрено и опубликовано на сайте.\n\n"
            "С уважением, команда Mokitoki"
        ),
    )


def send_item_moderation_rejected(user, item_title, reason):
    _send(
        to_email=user.email,
        subject=f"Объявление отклонено: {item_title}",
        message=(
            f"Здравствуйте, {user.username}!\n\n"
            f"Ваша заявка на публикацию или редактирование объявления «{item_title}» отклонена модератором.\n\n"
            f"Причина: {reason}\n\n"
            "Объявление снято с публикации. Вы можете создать новое объявление после исправления причины отказа.\n\n"
            "С уважением, команда Mokitoki"
        ),
    )


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
