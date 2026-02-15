from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

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
from .models import PasswordResetToken
from .cloudinary_utils import upload_image_to_cloudinary
import secrets

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """View for user registration."""
    
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """View for user login."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Login successful'
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
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user profile."""
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """View for changing password."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})


class ForgotPasswordView(APIView):
    """View for requesting password reset."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Invalidate any existing tokens
            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
            
            # Create new token
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(user=user, token=token)
            
            # In production, send email with reset link
            # For now, return success message
            return Response({
                'message': 'If an account with this email exists, a password reset link has been sent.',
                # Include token in dev mode for testing - remove in production!
                'reset_token': token,
            })
        except User.DoesNotExist:
            # Return same message to prevent email enumeration
            return Response({
                'message': 'If an account with this email exists, a password reset link has been sent.'
            })


class ResetPasswordView(APIView):
    """View for resetting password with token."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if not reset_token.is_valid():
                return Response(
                    {'error': 'This reset link has expired or already been used'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset password
            user = reset_token.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Mark token as used
            reset_token.used = True
            reset_token.save()
            
            return Response({'message': 'Password has been reset successfully'})
            
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset token'},
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
