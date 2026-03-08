from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Transaction
from app.services.report_service import (
    get_available_months,
    get_month_summary,
    get_transactions_by_month,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


class TransactionUpdate(BaseModel):
    description: str
    amount: float
    category: str
    type: str


@router.get("/months")
def api_months(db: Session = Depends(get_db)):
    data = get_available_months(db)
    return JSONResponse(content=data)


@router.get("/summary")
def api_summary(month: int, year: int, db: Session = Depends(get_db)):
    data = get_month_summary(db, month, year)
    return JSONResponse(content=data)


@router.get("/transactions")
def api_transactions(month: int, year: int, db: Session = Depends(get_db)):
    transactions = get_transactions_by_month(db, month, year)

    data = [
        {
            "id": t.id,
            "date": t.created_at.strftime("%d/%m"),
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "type": t.type,
        }
        for t in transactions
    ]

    return JSONResponse(content=data)


@router.delete("/transactions/{transaction_id}")
def api_delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return JSONResponse(content={"status": "deleted", "id": transaction_id})


@router.put("/transactions/{transaction_id}")
def api_update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db)
):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.description = payload.description
    transaction.amount = payload.amount
    transaction.category = payload.category
    transaction.type = payload.type

    db.commit()
    db.refresh(transaction)

    return JSONResponse(content={
        "id": transaction.id,
        "description": transaction.description,
        "amount": transaction.amount,
        "category": transaction.category,
        "type": transaction.type,
    })