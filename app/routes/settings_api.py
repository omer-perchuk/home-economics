from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from app.services.settings_service import get_settings, update_dashboard_title

router = APIRouter(prefix="/api/settings", tags=["settings"])


class TitlePayload(BaseModel):
    dashboard_title: str


@router.get("")
def api_get_settings():
    return JSONResponse(content=get_settings())


@router.put("/title")
def api_update_title(payload: TitlePayload):
    clean_title = payload.dashboard_title.strip()

    if not clean_title:
        clean_title = "כלכלת הבית"

    updated = update_dashboard_title(clean_title)
    return JSONResponse(content=updated)