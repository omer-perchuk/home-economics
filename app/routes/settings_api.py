from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.settings_service import get_settings, update_dashboard_title

router = APIRouter(prefix="/api", tags=["settings"])


class TitlePayload(BaseModel):
    dashboard_title: str


@router.get("/settings")
def api_get_settings(
    family_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return get_settings(db, family_id)


@router.put("/settings/title")
def api_update_title(
    payload: TitlePayload,
    family_id: int = Query(...),
    db: Session = Depends(get_db),
):
    clean_title = payload.dashboard_title.strip()
    return update_dashboard_title(db, family_id, clean_title)