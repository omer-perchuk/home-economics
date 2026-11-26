import os

from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


def _client_id() -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured")
    return client_id


def verify_google_credential(credential: str) -> dict:
    """בודק מול גוגל שהאישור (ID token) אמיתי, בתוקף ומיועד לאתר שלנו.

    מחזיר את הפרטים מתוך האישור: sub (מזהה קבוע של החשבון), email ועוד.
    """
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            _client_id(),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    if not info.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    return info
