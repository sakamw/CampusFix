import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

# Custom validators for security
class NoMaliciousContentValidator:
    """Validator to check for malicious content in text fields."""
    
    def __init__(self):
        self.malicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                 # Event handlers
            r'eval\s*\(',                 # eval() calls
            r'expression\s*\(',           # CSS expressions
            r'@import',                   # CSS imports
            r'binding\s*:',               # XML binding
        ]
    
    def __call__(self, value):
        if not isinstance(value, str):
            return
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                raise ValidationError(
                    _('Potentially malicious content detected.'),
                    code='malicious_content'
                )
    
    def deconstruct(self):
        return (
            'security.validators.NoMaliciousContentValidator',
            [],
            {}
        )


class SQLInjectionValidator:
    """Validator to detect potential SQL injection patterns."""
    
    def __init__(self):
        self.sql_patterns = [
            r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|\/\*|\*\/)",
            r"(\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b)",
        ]
    
    def __call__(self, value):
        if not isinstance(value, str):
            return
        
        for pattern in self.sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    _('Invalid characters detected.'),
                    code='sql_injection'
                )
    
    def deconstruct(self):
        return (
            'security.validators.SQLInjectionValidator',
            [],
            {}
        )


class XSSValidator:
    """Validator to detect XSS patterns."""
    
    def __init__(self):
        self.xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'vbscript:',
            r'data:text/html',
        ]
    
    def __call__(self, value):
        if not isinstance(value, str):
            return
        
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    _('Invalid HTML content detected.'),
                    code='xss'
                )
    
    def deconstruct(self):
        return (
            'security.validators.XSSValidator',
            [],
            {}
        )


# Regex validators for common fields
secure_username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_\-\.]{3,30}$',
    message=_('Username can only contain letters, numbers, dots, hyphens, and underscores (3-30 characters).'),
    code='invalid_username'
)

secure_email_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    message=_('Enter a valid email address.'),
    code='invalid_email'
)

secure_phone_validator = RegexValidator(
    regex=r'^\+?[\d\s\-\(\)]{10,20}$',
    message=_('Enter a valid phone number.'),
    code='invalid_phone'
)

secure_filename_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_\-\.]{1,255}$',
    message=_('Filename can only contain letters, numbers, dots, hyphens, and underscores.'),
    code='invalid_filename'
)

secure_location_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9\s\-\.,\/]{1,255}$',
    message=_('Location can only contain letters, numbers, spaces, dots, commas, hyphens, and forward slashes.'),
    code='invalid_location'
)


def validate_file_upload(file):
    """Validate uploaded files for security."""
    if not file:
        return
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(_('File size cannot exceed 10MB.'))
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt']
    file_extension = file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(_('File type not allowed.'))
    
    # Check filename for malicious patterns
    if any(pattern in file.name.lower() for pattern in ['script', 'exec', 'shell', 'cmd']):
        raise ValidationError(_('Invalid filename.'))


def sanitize_input(value):
    """Basic input sanitization."""
    if not isinstance(value, str):
        return value
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', value)
    
    # Limit length
    max_length = 10000
    if len(sanitized) > max_length:
        raise ValidationError(_('Input too long.'))
    
    return sanitized.strip()
