from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.login_token import LoginToken
from app.utils.auth_tokens import generate_raw_token, hash_token


MAGIC_LINK_TTL_MINUTES = 15

FRONTEND_URL = "https://aws-migration-test.d11fqx2zyfwk68.amplifyapp.com"


def create_magic_link(user_id: int, family_id: int) -> str:
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

        # ✅ שולחים ל-FRONTEND (ולא לבקאנד)
        return f"{FRONTEND_URL}/auth?token={raw_token}"

    finally:
        db.close()