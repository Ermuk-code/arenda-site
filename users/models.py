from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    USER_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('entrepreneur', 'Entrepreneur'),
        ('legal', 'Legal Entity'),
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='individual'  # важно!
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    entrepreneur_name = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    # физ лицо
    passport_series = models.CharField(max_length=4, blank=True)
    passport_number = models.CharField(max_length=6, blank=True)
    inn = models.CharField(max_length=12, blank=True)

    # ИП / юр лицо
    kpp = models.CharField(max_length=9, blank=True)
    ogrnip = models.CharField(max_length=15, blank=True)
    
    

    profile_completed = models.BooleanField(default=False)
    average_rating = models.DecimalField(
    max_digits=3,
    decimal_places=2,
    default=0
    )

    reviews_count = models.IntegerField(default=0)
    def __str__(self):
        return self.username
