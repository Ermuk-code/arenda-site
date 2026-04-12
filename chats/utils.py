from django.core.mail import send_mail


def send_new_message_email(user, message):
    send_mail(
        subject="Новое сообщение",
        message=f"Вам написал {message.sender.username}: {message.text}",
        from_email="mokitoki.notifications@gmail.com",
        recipient_list=[user.email],
    )
