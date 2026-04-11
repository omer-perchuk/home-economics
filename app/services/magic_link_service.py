from datetime import datetime, timedelta
from urllib.parse import quote

from app.db.database import SessionLocal
from app.db.login_token import LoginToken
from app.utils.auth_tokens import generate_raw_token, hash_token


MAGIC_LINK_TTL_MINUTES = 15

FRONTEND_URL = "https://main.d11fqx2zyfwk68.amplifyapp.com"


def create_magic_link(user_id: int, family_id: int, redirect_to: str = "/") -> str:
    db = SessionLocal()
    try:
        raw_token = generate_raw_token()
        token_hash = hash_token(raw_token)

        login_token = LoginToken(
            token_hash=token_hash,
            user_id=user_id,
            family_id=family_id,
            expires_at=datetime.utcnow() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES),
        )

        db.add(login_token)
        db.commit()

        safe_redirect = redirect_to if redirect_to.startswith("/") else "/"
        encoded_redirect = quote(safe_redirect, safe="")

        return f"{FRONTEND_URL}/auth?token={raw_token}&redirect={encoded_redirect}"

    finally:
        db.close()
