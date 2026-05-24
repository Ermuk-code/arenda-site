from django.urls import path
from .views import (
    RegisterView,
    ProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    SendEmailVerificationCodeView,
    FillByInnView,
)

urlpatterns = [
    path('send-email-code/', SendEmailVerificationCodeView.as_view(), name='send-email-code'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Кнопка «Заполнить по ИНН» — доступна всем (в т.ч. при регистрации)
    path('fill-by-inn/', FillByInnView.as_view(), name='fill-by-inn'),
]
