from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from bookings.models import Booking
from notifications.email import send_return_reminder
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Отправляет напоминания о возврате товаров (за 1 день до end_date)'

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timedelta(days=1)
        bookings = Booking.objects.filter(
            status='confirmed',
            end_date=tomorrow
        )
        count = 0
        for booking in bookings:
            Notification.objects.create(
                user=booking.renter,
                type='booking_created',  # используем существующий тип
                message=f"Reminder: return '{booking.item.title}' tomorrow"
            )
            send_return_reminder(booking)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Отправлено {count} напоминаний о возврате')
        )