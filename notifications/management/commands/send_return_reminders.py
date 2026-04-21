from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking
from notifications.services import notify_return_reminder


class Command(BaseCommand):
    help = 'Send email reminders for confirmed bookings ending tomorrow.'

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)
        bookings = Booking.objects.filter(status='confirmed', end_date=tomorrow)

        sent_count = 0
        for booking in bookings:
            notify_return_reminder(booking)
            sent_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Sent {sent_count} return reminder(s).')
        )
