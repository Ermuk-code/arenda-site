from django.db import models


class PostOffice(models.Model):
    """Отделение Почты России, загруженное из DaData."""

    postal_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Почтовый индекс'
    )
    address_str = models.CharField(
        max_length=500,
        verbose_name='Адрес'
    )
    region = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Регион'
    )
    city = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Город'
    )
    is_closed = models.BooleanField(
        default=False,
        verbose_name='Закрыто'
    )
    type_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Тип отделения'
    )
    geo_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Широта'
    )
    geo_lon = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Долгота'
    )
    schedule_mon = models.CharField(max_length=50, blank=True, default='')
    schedule_tue = models.CharField(max_length=50, blank=True, default='')
    schedule_wed = models.CharField(max_length=50, blank=True, default='')
    schedule_thu = models.CharField(max_length=50, blank=True, default='')
    schedule_fri = models.CharField(max_length=50, blank=True, default='')
    schedule_sat = models.CharField(max_length=50, blank=True, default='')
    schedule_sun = models.CharField(max_length=50, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Отделение Почты России'
        verbose_name_plural = 'Отделения Почты России'
        ordering = ['postal_code']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['postal_code']),
        ]

    def __str__(self):
        return f'{self.postal_code} — {self.address_str}'
