from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.user_session import UserSession
from app.utils.auth_tokens import hash_token


def get_current_session(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    raw_token = auth_header.replace("Bearer ", "")
    token_hash = hash_token(raw_token)

    session = (
        db.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash)
        .first()
    )

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    return session