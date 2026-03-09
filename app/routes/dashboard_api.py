from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Family
from app.services.report_service import (
    get_available_months,
    get_month_summary,
    get_transactions_by_month,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


def get_family_id_by_name(db: Session, family_name: str | None):
    if not family_name:
        return None

    family = db.query(Family).filter(Family.name == family_name).first()
    if not family:
        return None

    return family.id


@router.get("/months")
def api_months(
    family_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    family_id = get_family_id_by_name(db, family_name)
    data = get_available_months(db, family_id=family_id)
    return data


@router.get("/summary")
def api_summary(
    month: int,
    year: int,
    family_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    family_id = get_family_id_by_name(db, family_name)
    data = get_month_summary(db, month, year, family_id=family_id)
    return data


@router.get("/transactions")
def api_transactions(
    month: int,
    year: int,
    family_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    family_id = get_family_id_by_name(db, family_name)
    transactions = get_transactions_by_month(db, month, year, family_id=family_id)

    return [
        {
            "id": t.id,
            "date": t.created_at.strftime("%d/%m") if t.created_at else "",
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "type": t.type,
        }
        for t in transactions
    ]