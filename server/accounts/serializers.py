from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from security.validators import (
    secure_email_validator, 
    secure_phone_validator,
    NoMaliciousContentValidator,
    sanitize_input
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'student_id', 'phone', 'role', 'avatar', 'two_factor_enabled', 'created_at', 'is_superuser', 'is_staff']
        read_only_fields = ['id', 'email', 'role', 'created_at', 'is_superuser', 'is_staff']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True, validators=[secure_email_validator])
    first_name = serializers.CharField(required=True, validators=[NoMaliciousContentValidator()])
    last_name = serializers.CharField(required=True, validators=[NoMaliciousContentValidator()])
    student_id = serializers.CharField(required=False, allow_blank=True, validators=[NoMaliciousContentValidator()])
    phone = serializers.CharField(required=False, allow_blank=True, validators=[secure_phone_validator])
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'student_id', 'phone', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Sanitize text inputs
        for field in ['first_name', 'last_name', 'student_id']:
            if field in attrs and attrs[field]:
                attrs[field] = sanitize_input(attrs[field])
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""
    
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting password with token."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs


class AvatarUpdateSerializer(serializers.Serializer):
    """Serializer for updating user avatar URL."""
    
    avatar = serializers.URLField(required=False, allow_null=True)


class CloudinaryImageUploadSerializer(serializers.Serializer):
    """Serializer for uploading images to Cloudinary."""
    
    image = serializers.ImageField(required=True)


class TwoFactorUpdateSerializer(serializers.Serializer):
    """Serializer for updating two-factor authentication settings."""
    
    two_factor_enabled = serializers.BooleanField(required=True)
