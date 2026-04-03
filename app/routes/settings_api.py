from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.settings_service import get_settings, update_dashboard_title
from app.utils.session_auth import get_current_session

router = APIRouter(prefix="/api", tags=["settings"])


class TitlePayload(BaseModel):
    dashboard_title: str


@router.get("/settings")
def api_get_settings(
    session = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return get_settings(db, session.family_id)


@router.put("/settings/title")
def api_update_title(
    payload: TitlePayload,
    session = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    clean_title = payload.dashboard_title.strip()
    return update_dashboard_title(db, session.family_id, clean_title)