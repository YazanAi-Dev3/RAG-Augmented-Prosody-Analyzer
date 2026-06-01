import hashlib
import hmac
import os
from typing import Optional


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt_hex = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200000)
    return f"{salt_hex}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, _ = stored_hash.split("$", 1)
        candidate = hash_password(password, salt_hex)
        return hmac.compare_digest(candidate, stored_hash)
    except ValueError:
        return False
