"""
Удаление приложения postoffices.

Эта миграция:
1. Удаляет таблицу postoffices_postoffice из БД (если существует).
2. Удаляет записи о миграциях postoffices из django_migrations,
   чтобы Django не пытался их применить при следующем makemigrations/migrate.
"""

from django.db import migrations


def drop_postoffices_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DROP TABLE IF EXISTS postoffices_postoffice CASCADE;"
        )
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'postoffices';"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_booking_platform_fee_booking_rent_amount'),
    ]

    operations = [
        migrations.RunPython(
            drop_postoffices_table,
            migrations.RunPython.noop,  # rollback — ничего не делаем
        ),
    ]
