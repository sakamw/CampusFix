from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    AvatarUpdateView,
    CloudinaryImageUploadView,
    TwoFactorUpdateView,
    TwoFactorSetupView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('avatar-url/', AvatarUpdateView.as_view(), name='avatar_update'),
    path('upload-avatar/', CloudinaryImageUploadView.as_view(), name='cloudinary_upload'),
    path('two-factor/', TwoFactorUpdateView.as_view(), name='two_factor_update'),
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='two_factor_setup'),
]
