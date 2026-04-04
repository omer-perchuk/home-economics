from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.login_token import LoginToken
from app.utils.auth_tokens import generate_raw_token, hash_token


MAGIC_LINK_TTL_MINUTES = 15
BACKEND_URL = "https://ph6dqc68jq.us-east-1.awsapprunner.com"


def create_magic_link(user_id: int, family_id: int, base_url: str) -> str:
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

        return f"{BACKEND_URL}/api/auth/magic-login?token={raw_token}"
    finally:
        db.close()