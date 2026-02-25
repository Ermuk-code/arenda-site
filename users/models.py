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

    profile_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.username