from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.settings_service import get_settings, update_dashboard_title

router = APIRouter(prefix="/api", tags=["settings"])


class TitlePayload(BaseModel):
    dashboard_title: str


@router.get("/settings")
def api_get_settings(
    family_id: int = Query(...),
):
    return get_settings(family_id)


@router.put("/settings/title")
def api_update_title(
    payload: TitlePayload,
    family_id: int = Query(...),
):
    clean_title = payload.dashboard_title.strip()
    return update_dashboard_title(family_id, clean_title)