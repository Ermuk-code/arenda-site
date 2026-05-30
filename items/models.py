from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):  # ✅ исправлено
        return self.name


class Item(models.Model):

    STATUS_CHOICES = (
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('blocked', 'Blocked'),
    )

    RENT_TYPE_CHOICES = (
        ('hourly', 'Почасовая'),
        ('daily', 'Посуточная'),
        ('both', 'Почасовая и посуточная'),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='items'
    )

    title = models.CharField(max_length=255)
    description = models.TextField()

    # 🔥 НОВОЕ
    rent_type = models.CharField(
        max_length=10,
        choices=RENT_TYPE_CHOICES,
        default='daily'
    )

    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    price_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    deposit = models.DecimalField(  # 💰 залог
        max_digits=10,
        decimal_places=2,
        default=0
    )

    delivery_price = models.DecimalField(  # 🚚 доставка
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ⭐ рейтинг
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    reviews_count = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )

    def __str__(self):  # ✅ исправлено
        return self.title


class ItemImage(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='items/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.item.title}"