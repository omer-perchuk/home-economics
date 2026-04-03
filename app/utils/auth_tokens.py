import hashlib
import secrets


def generate_raw_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()