import os
from typing import Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet


ITERATIONS = 390_000
KEY_LENGTH = 32


def generate_salt() -> bytes:
    return os.urandom(16)


def derive_key(master_password: str, salt: bytes) -> bytes:
    password_bytes = master_password.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(password_bytes)


def build_fernet(master_password: str, salt: bytes) -> Fernet:
    raw_key = derive_key(master_password, salt)
    # Fernet expects a base64 urlsafe key
    import base64

    key = base64.urlsafe_b64encode(raw_key)
    return Fernet(key)


def encrypt_password(fernet: Fernet, plaintext: str) -> bytes:
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_password(fernet: Fernet, token: bytes) -> str:
    return fernet.decrypt(token).decode("utf-8")


