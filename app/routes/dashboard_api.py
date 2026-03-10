from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.report_service import (
    get_available_months,
    get_month_summary,
    get_transactions_by_month,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/months")
def api_months(
    family_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_available_months(db, family_id=family_id)


@router.get("/summary")
def api_summary(
    month: int,
    year: int,
    family_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_month_summary(db, month, year, family_id=family_id)


@router.get("/transactions")
def api_transactions(
    month: int,
    year: int,
    family_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
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