from django.urls import path
from .views import RegisterView
from .views import ProfileView
from .views import ChangePasswordView
from .views import PasswordResetRequestView
from .views import PasswordResetConfirmView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('password-reset/request/', PasswordResetRequestView.as_view()),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
]
