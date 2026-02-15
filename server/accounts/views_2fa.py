from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from .serializers_2fa import TwoFactorSetupSerializer, TwoFactorVerifySerializer, TwoFactorLoginSerializer
from .two_factor_utils import cache_2fa_session

User = get_user_model()

class TwoFactorSetupView(APIView):
    """Setup 2FA for a user account."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate 2FA secret and QR code."""
        serializer = TwoFactorSetupSerializer(context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Verify and enable 2FA."""
        serializer = TwoFactorVerifySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_enabled'])
        
        return Response({
            'message': '2FA enabled successfully',
            'two_factor_enabled': True
        }, status=status.HTTP_200_OK)

class TwoFactorLoginView(APIView):
    """Verify 2FA token during login."""
    
    def post(self, request):
        """Verify 2FA token for login completion."""
        serializer = TwoFactorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Cache the 2FA verification for this login session
        cache_2fa_session(user.id, verified=True)
        
        return Response({
            'message': '2FA verification successful',
            'user_id': user.id
        }, status=status.HTTP_200_OK)

class TwoFactorDisableView(APIView):
    """Disable 2FA for a user account."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Disable 2FA (requires password confirmation)."""
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({
                'error': 'Invalid password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.save(update_fields=['two_factor_enabled', 'two_factor_secret'])
        
        return Response({
            'message': '2FA disabled successfully',
            'two_factor_enabled': False
        }, status=status.HTTP_200_OK)
