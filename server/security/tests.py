from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

User = get_user_model()


class SecurityHeadersMiddlewareTest(TestCase):
    """Test security headers middleware."""
    
    def setUp(self):
        self.client = Client()
    
    def test_security_headers_present(self):
        """Test that security headers are present in responses."""
        response = self.client.get('/login/')
        
        # Check for security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        
        self.assertIn('X-Frame-Options', response)
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        
        self.assertIn('X-XSS-Protection', response)
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
        
        self.assertIn('Strict-Transport-Security', response)
        self.assertIn('Content-Security-Policy', response)
        self.assertIn('Referrer-Policy', response)
        self.assertIn('Permissions-Policy', response)


class InputValidationMiddlewareTest(APITestCase):
    """Test input validation middleware."""
    
    def setUp(self):
        self.client = APITestCase()
    
    def test_malicious_script_detection(self):
        """Test detection of malicious script content."""
        malicious_data = {
            'email': 'test@example.com',
            'first_name': '<script>alert("xss")</script>',
            'last_name': 'Test',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!'
        }
        
        response = self.client.post('/api/auth/register/', malicious_data, format='json')
        
        # Should be rejected due to malicious content
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid input detected', str(response.data))
    
    def test_javascript_url_detection(self):
        """Test detection of JavaScript URLs."""
        malicious_data = {
            'title': 'Test Issue',
            'description': 'Issue with javascript:alert("xss") in description',
            'category': 'other',
            'location': 'Test Location'
        }
        
        response = self.client.post('/api/issues/', malicious_data, format='json')
        
        # Should be rejected due to malicious content
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RateLimitingTest(APITestCase):
    """Test rate limiting functionality."""
    
    def setUp(self):
        self.client = APITestCase()
    
    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_registration_rate_limiting(self, mock_cache_set, mock_cache_get):
        """Test registration endpoint rate limiting."""
        # Mock cache to simulate rate limit exceeded
        mock_cache_get.return_value = 5  # Already at limit
        
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!'
        }
        
        response = self.client.post('/api/auth/register/', data, format='json')
        
        # Should be rate limited
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Rate limit exceeded', str(response.data))
    
    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_login_rate_limiting(self, mock_cache_set, mock_cache_get):
        """Test login endpoint rate limiting."""
        # Mock cache to simulate rate limit exceeded
        mock_cache_get.return_value = 5  # Already at limit
        
        data = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = self.client.post('/api/auth/login/', data, format='json')
        
        # Should be rate limited
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Rate limit exceeded', str(response.data))


class AuditLoggingTest(TestCase):
    """Test audit logging functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    @patch('logging.getLogger')
    def test_security_event_logging(self, mock_get_logger):
        """Test that security events are logged."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Trigger a security event (failed login)
        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, content_type='application/json')
        
        # Check that logging was called
        mock_logger.info.assert_called()


class SecurityValidatorsTest(TestCase):
    """Test security validators."""
    
    def test_no_malicious_content_validator(self):
        """Test malicious content validator."""
        from security.validators import NoMaliciousContentValidator
        
        validator = NoMaliciousContentValidator()
        
        # Valid content should pass
        try:
            validator("This is safe content")
        except Exception:
            self.fail("Valid content raised exception")
        
        # Malicious content should fail
        with self.assertRaises(Exception):
            validator("<script>alert('xss')</script>")
        
        with self.assertRaises(Exception):
            validator("javascript:alert('xss')")
        
        with self.assertRaises(Exception):
            validator("onclick=alert('xss')")
    
    def test_sql_injection_validator(self):
        """Test SQL injection validator."""
        from security.validators import SQLInjectionValidator
        
        validator = SQLInjectionValidator()
        
        # Valid content should pass
        try:
            validator("This is safe content")
        except Exception:
            self.fail("Valid content raised exception")
        
        # SQL injection attempts should fail
        with self.assertRaises(Exception):
            validator("'; DROP TABLE users; --")
        
        with self.assertRaises(Exception):
            validator("1' OR '1'='1")
    
    def test_file_upload_validation(self):
        """Test file upload validation."""
        from security.validators import validate_file_upload
        from django.core.exceptions import ValidationError
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Valid file should pass
        valid_file = SimpleUploadedFile(
            "test.jpg", 
            b"fake image content", 
            content_type="image/jpeg"
        )
        try:
            validate_file_upload(valid_file)
        except ValidationError:
            self.fail("Valid file raised ValidationError")
        
        # Invalid file type should fail
        invalid_file = SimpleUploadedFile(
            "test.exe", 
            b"fake executable content", 
            content_type="application/octet-stream"
        )
        with self.assertRaises(ValidationError):
            validate_file_upload(invalid_file)
        
        # Oversized file should fail
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large.jpg", 
            large_content, 
            content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError):
            validate_file_upload(large_file)


class InputSanitizationTest(TestCase):
    """Test input sanitization."""
    
    def test_sanitize_input(self):
        """Test input sanitization function."""
        from security.validators import sanitize_input
        
        # Normal input should remain unchanged
        result = sanitize_input("Normal text content")
        self.assertEqual(result, "Normal text content")
        
        # Dangerous characters should be removed
        result = sanitize_input("Text with <script>alert('xss')</script> tags")
        self.assertEqual(result, "Text with scriptalert('xss') tags")
        
        # Quotes should be removed
        result = sanitize_input('Text with "quotes" and \'apostrophes\'')
        self.assertEqual(result, "Text with quotes and apostrophes")
        
        # Excessive length should raise error
        long_text = "x" * 10001
        with self.assertRaises(Exception):
            sanitize_input(long_text)
