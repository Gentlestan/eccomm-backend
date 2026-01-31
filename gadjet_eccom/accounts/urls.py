# accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

# Auth views
from .views.auth_views import (
    RegisterView,
    LoginView,
    VerifyEmailView,
    ForgotPasswordView,
    ResetPasswordView,
)

# User views
from .views.user_views import (
    MeView,
    UpdateProfileView,
    ChangePasswordView,
)

urlpatterns = [
    # -------------------- Auth --------------------
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # -------------------- Email Verification --------------------
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),

    # -------------------- Password Reset --------------------
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    # -------------------- User / Profile --------------------
    path('me/', MeView.as_view(), name='me'),  # get current user
    path('update/', UpdateProfileView.as_view(), name='update-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
