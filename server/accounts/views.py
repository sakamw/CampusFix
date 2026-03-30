from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    LoginSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    AvatarUpdateSerializer,
    CloudinaryImageUploadSerializer,
    TwoFactorUpdateSerializer,
)
from .models import PasswordResetToken, EmailVerificationToken, SupportRequest
from .cloudinary_utils import upload_image_to_cloudinary
from security.decorators import auth_rate_limit, user_rate_limit
from utils.email_service import (
    send_verification_email,
    send_account_verified_email,
    send_password_reset_email,
    send_password_changed_email
)
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import secrets
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """View for user registration."""
    
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    @auth_rate_limit(rate='3/m', block_time=900)  # 3 registrations per minute
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Accounts are created inactive until email is verified
        user.is_active = False
        user.save()
        
        # Generate verification token
        token_obj = EmailVerificationToken.objects.create(user=user)
        
        # Send verification email
        send_verification_email(user, token_obj.token)
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Account created successfully! Please check your email to verify your account.',
            'success': True
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """View for user login."""
    
    permission_classes = [AllowAny]
    
    @auth_rate_limit(rate='5/m', block_time=900)  # 5 login attempts per minute
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            # Check if it was an inactive user with correct password
            try:
                inactive_user = User.objects.get(email=email, is_active=False)
                if inactive_user.check_password(password):
                    reason = inactive_user.deactivation_reason or 'No reason provided'
                    message = f"Account Deactivated: {reason}. Please contact admin for assistance."
                    return Response(
                        {
                            'error': message,
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except User.DoesNotExist:
                pass

            return Response(
                {
                    'error': 'Invalid login credentials',
                    'message': 'The email address or password you entered is incorrect. Please check your credentials and try again.'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Prevent staff/admin accounts from using the student-facing API login.
        # These accounts should authenticate via the CampusFix Admin Dashboard instead.
        if getattr(user, "role", None) in {"staff", "admin"} or user.is_staff or user.is_superuser:
            return Response(
                {
                    "error": "Admin or staff account login not allowed here",
                    "message": "Staff and admin accounts must use the CampusFix Admin Dashboard to sign in.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Welcome back! You have successfully logged in.',
            'success': True
        })


class LogoutView(APIView):
    """View for user logout."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({
                'message': 'You have been successfully logged out.',
                'success': True
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                'message': 'You have been successfully logged out.',
                'success': True
            }, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user profile."""
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """View for changing password."""
    
    permission_classes = [IsAuthenticated]
    
    @user_rate_limit(rate='10/h', block_time=1800)  # 10 password changes per hour
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {
                    'error': 'Invalid current password',
                    'message': 'The current password you entered is incorrect. Please verify your password and try again.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Send security notification
        send_password_changed_email(user)
        
        return Response({
            'message': 'Your password has been successfully changed.',
            'success': True
        })


class ForgotPasswordView(APIView):
    """View for requesting password reset."""
    
    permission_classes = [AllowAny]
    
    @auth_rate_limit(rate='3/h', block_time=3600)  # 3 password reset requests per hour per IP
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Use a generic message to prevent email enumeration
        success_response = Response({
            'message': 'If an account with this email exists, a password reset link has been sent to your email address.',
            'success': True
        })

        try:
            user = User.objects.get(email=email)
            
            # Generate token using Django's built-in generator
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            reset_url = f"{settings.SITE_URL}/auth/reset-password/{uid}/{token}/"
            
            # Send email
            send_password_reset_email(user, reset_url)
            
            return success_response
        except User.DoesNotExist:
            return success_response


class ResetPasswordView(APIView):
    """View for resetting password with token."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        # The request expects token, uidb64 (if following Django pattern) and new_password
        # Let's adjust to the uidb64/token pattern from the request
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not all([uidb64, token, new_password]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            
            # Send confirmation email
            send_password_changed_email(user)
            
            return Response({
                'message': 'Your password has been successfully reset. You can now log in with your new password.',
                'success': True
            })
        else:
            return Response(
                {
                    'error': 'Invalid or expired reset link',
                    'message': 'This password reset link is invalid or has expired. Please request a new password reset.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class AvatarUpdateView(APIView):
    """View for updating user avatar URL."""
    
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        serializer = AvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        avatar_url = serializer.validated_data.get('avatar')
        
        # Update user avatar
        user.avatar = avatar_url
        user.save()
        
        return Response({
            'message': 'Avatar updated successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class CloudinaryImageUploadView(APIView):
    """View for uploading images to Cloudinary."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CloudinaryImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_file = serializer.validated_data['image']
        
        try:
            # Upload to Cloudinary
            avatar_url = upload_image_to_cloudinary(image_file)
            
            # Update user's avatar
            user = request.user
            user.avatar = avatar_url
            user.save()
            
            return Response({
                'message': 'Image uploaded successfully',
                'avatar_url': avatar_url,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorUpdateView(APIView):
    """View for updating two-factor authentication settings."""
    
    permission_classes = [IsAuthenticated]
    
    def patch(self, request):
        serializer = TwoFactorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_enabled = serializer.validated_data['two_factor_enabled']
        
        # Update user's two-factor setting
        user.two_factor_enabled = two_factor_enabled
        user.save()
        
        return Response({
            'message': f'Two-factor authentication {"enabled" if two_factor_enabled else "disabled"} successfully',
            'two_factor_enabled': two_factor_enabled,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class TwoFactorSetupView(APIView):
    """View for setting up 2FA."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate 2FA secret and QR code for setup."""
        from .two_factor_utils import generate_2fa_secret, generate_qr_code, generate_backup_codes
        
        user = request.user
        if user.two_factor_enabled:
            return Response({
                'message': '2FA is already enabled',
                'two_factor_enabled': True
            }, status=status.HTTP_200_OK)
        
        # Generate new secret and QR code
        secret = generate_2fa_secret()
        qr_code = generate_qr_code(user.email, secret)
        backup_codes = generate_backup_codes()
        
        # Temporarily store the secret (in production, use cache)
        user.two_factor_secret = secret
        user.save(update_fields=['two_factor_secret'])
        
        return Response({
            'secret': secret,
            'qr_code': qr_code,
            'backup_codes': backup_codes,
            'instructions': 'Scan the QR code with your authenticator app or enter the secret manually'
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Verify and enable 2FA."""
        from .two_factor_utils import verify_2fa_token
        
        token = request.data.get('token')
        if not token or len(token) != 6:
            return Response({
                'error': 'Invalid verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        if not user.two_factor_secret:
            return Response({
                'error': '2FA setup not initiated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not verify_2fa_token(user.two_factor_secret, token):
            return Response({
                'error': 'Invalid verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Enable 2FA
        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_enabled'])
        
        return Response({
            'message': '2FA enabled successfully',
            'two_factor_enabled': True,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class SupportRequestView(APIView):
    """View for handling in-app support requests."""
    
    permission_classes = [IsAuthenticated]
    
    @user_rate_limit(rate='5/h', block_time=3600)  # 5 support requests per hour
    def post(self, request):
        user = request.user
        support_type = request.data.get('support_type')
        subject = request.data.get('subject')
        message = request.data.get('message')
        
        if not all([support_type, subject, message]):
            return Response(
                {
                    'error': 'Missing required fields',
                    'message': 'Please provide the support type, subject, and message.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Construct email content
        email_subject = f"[{support_type}] {subject} - From: {user.first_name} {user.last_name}"
        email_body = f"""
New support request from CampusFix Application:

Reporter Details:
-----------------
Name: {user.first_name} {user.last_name}
Email: {user.email}
Role: {user.role}
Student ID: {getattr(user, 'student_id', 'N/A')}

Support Details:
----------------
Type: {support_type}
Subject: {subject}

Message:
--------
{message}
"""

        # Save to database
        support_request = SupportRequest.objects.create(
            user=user,
            support_type=support_type,
            subject=subject,
            message=message
        )
        
        try:
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.SUPPORT_EMAIL],
                fail_silently=False,
            )
            
            return Response({
                'message': 'Your support request has been sent successfully. Our team will get back to you shortly.',
                'success': True
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to send support request',
                'message': 'An error occurred while sending your request. Please try again later or email us directly.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyEmailView(APIView):
    """View for verifying user email."""
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        try:
            token_obj = EmailVerificationToken.objects.get(token=token)
            
            if not token_obj.is_valid():
                return Response(
                    {
                        'error': 'Link expired or invalid',
                        'message': 'This verification link has expired or is invalid. Please request a new verification email.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Activate user
            user = token_obj.user
            user.is_active = True
            user.save()
            
            # Mark token as used
            token_obj.is_used = True
            token_obj.save()
            
            # Send confirmation email
            send_account_verified_email(user)
            
            return Response({
                'message': 'Your email has been verified successfully! You can now log in.',
                'success': True
            })
            
        except (EmailVerificationToken.DoesNotExist, ValueError):
            return Response(
                {
                    'error': 'Invalid verification link',
                    'message': 'This verification link is invalid. Please check your email for the correct link.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class ResendVerificationView(APIView):
    """View for resending verification email."""
    permission_classes = [AllowAny]
    
    @auth_rate_limit(rate='3/h', block_time=3600)  # 3 resends per hour
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                return Response({'message': 'Account is already active.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Invalidate old tokens
            EmailVerificationToken.objects.filter(user=user, is_used=False).delete()
            
            # Generate new token
            token_obj = EmailVerificationToken.objects.create(user=user)
            
            # Send email
            send_verification_email(user, token_obj.token)
            
            return Response({
                'message': 'Verification email has been resent. Please check your inbox.',
                'success': True
            })
        except User.DoesNotExist:
            # Generic response to prevent enumeration
            return Response({
                'message': 'If an account with this email exists and is not yet verified, a new verification link has been sent.',
                'success': True
            })

