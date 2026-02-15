import pyotp
import qrcode
import io
import base64
from django.core.cache import cache
from django.conf import settings

def generate_2fa_secret():
    """Generate a new secret key for 2FA."""
    return pyotp.random_base32()

def generate_qr_code(user_email, secret):
    """Generate QR code for 2FA setup."""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name="CampusFix"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def verify_2fa_token(secret, token):
    """Verify a 2FA token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 step (30s) before/after

def generate_backup_codes():
    """Generate backup codes for 2FA recovery."""
    import random
    import string
    
    codes = []
    for _ in range(10):  # Generate 10 backup codes
        code = ''.join(random.choices(string.digits, k=8))
        codes.append(code)
    
    return codes

def cache_2fa_session(user_id, verified=False):
    """Cache 2FA verification status during login session."""
    cache_key = f"2fa_session_{user_id}"
    cache.set(cache_key, verified, timeout=300)  # 5 minutes timeout
