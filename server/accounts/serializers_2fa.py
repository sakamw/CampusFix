from rest_framework import serializers
from .two_factor_utils import generate_2fa_secret, generate_qr_code, verify_2fa_token, generate_backup_codes
from django.contrib.auth import get_user_model

User = get_user_model()

class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for setting up 2FA."""
    
    def to_representation(self, instance):
        user = self.context['request'].user
        if not user.two_factor_enabled:
            secret = generate_2fa_secret()
            # Temporarily store secret for this user (you might want to use cache)
            user.two_factor_secret = secret
            user.save(update_fields=['two_factor_secret'])
            
            qr_code = generate_qr_code(user.email, secret)
            backup_codes = generate_backup_codes()
            
            return {
                'secret': secret,
                'qr_code': qr_code,
                'backup_codes': backup_codes,
                'instructions': 'Scan the QR code with your authenticator app or enter the secret manually'
            }
        return {'message': '2FA is already enabled'}

class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for verifying 2FA setup."""
    
    token = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        user = self.context['request'].user
        token = attrs['token']
        
        if not user.two_factor_secret:
            raise serializers.ValidationError("2FA setup not initiated")
        
        if not verify_2fa_token(user.two_factor_secret, token):
            raise serializers.ValidationError("Invalid verification code")
        
        return attrs

class TwoFactorLoginSerializer(serializers.Serializer):
    """Serializer for 2FA during login."""
    
    token = serializers.CharField(max_length=6, min_length=6)
    email = serializers.EmailField()
    
    def validate(self, attrs):
        token = attrs['token']
        email = attrs['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")
        
        if not user.two_factor_enabled or not user.two_factor_secret:
            raise serializers.ValidationError("2FA not enabled for this account")
        
        if not verify_2fa_token(user.two_factor_secret, token):
            raise serializers.ValidationError("Invalid verification code")
        
        attrs['user'] = user
        return attrs
