from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Transaction
from app.services.report_service import (
    get_available_months,
    get_month_summary,
    get_transactions_by_month,
)
from app.utils.session_auth import get_current_session

router = APIRouter(prefix="/api", tags=["dashboard"])


class TransactionCreate(BaseModel):
    description: str
    amount: float
    category: str
    type: str
    day: int
    month: int
    year: int


class TransactionUpdate(BaseModel):
    description: str
    amount: float
    category: str
    type: str
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


@router.get("/months")
def api_months(
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return get_available_months(db, family_id=session.family_id)


@router.get("/summary")
def api_summary(
    month: int,
    year: int,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    return get_month_summary(db, month, year, family_id=session.family_id)


@router.get("/transactions")
def api_transactions(
    month: int,
    year: int,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    transactions = get_transactions_by_month(
        db,
        month,
        year,
        family_id=session.family_id,
    )

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


@router.post("/transactions")
def create_transaction(
    data: TransactionCreate,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    created_at = datetime(data.year, data.month, data.day)

    transaction = Transaction(
        original_text=data.description,
        description=data.description,
        amount=data.amount,
        category=data.category,
        type=data.type,
        family_id=session.family_id,
        user_id=session.user_id,
        created_at=created_at,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "message": "Transaction created",
        "id": transaction.id,
    }


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.family_id == session.family_id,
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted"}


@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.family_id == session.family_id,
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.description = data.description
    transaction.amount = data.amount
    transaction.category = data.category
    transaction.type = data.type

    if data.day is not None and data.month is not None and data.year is not None:
        transaction.created_at = datetime(data.year, data.month, data.day)

    db.commit()
    db.refresh(transaction)

    return {"message": "Transaction updated"}