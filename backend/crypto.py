import os, base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def _get_key():
    secret = os.getenv('ENCRYPTION_KEY', 'vaultkey-encryption-secret-32chars!')
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'vaultkey_salt_v1',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)

def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ''
    f = _get_key()
    return f.encrypt(plain_text.encode()).decode()

def decrypt(cipher_text: str) -> str:
    if not cipher_text:
        return ''
    try:
        f = _get_key()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return cipher_text
