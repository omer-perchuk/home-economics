import calendar
from datetime import datetime
from typing import Optional

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.db.models import RecurringTransaction, Transaction


def create_recurring(
    db: Session,
    family_id: int,
    user_id: Optional[int],
    description: str,
    amount: float,
    tx_type: str,
    category: str,
    day_of_month: int,
) -> RecurringTransaction:
    recurring = RecurringTransaction(
        description=description,
        amount=amount,
        type=tx_type,
        category=category,
        day_of_month=day_of_month,
        family_id=family_id,
        user_id=user_id,
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return recurring


def get_active_recurring(db: Session, family_id: int):
    return (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.family_id == family_id,
            RecurringTransaction.is_active == True,
        )
        .order_by(RecurringTransaction.day_of_month.asc())
        .all()
    )


def deactivate_recurring(db: Session, recurring_id: int) -> Optional[RecurringTransaction]:
    recurring = (
        db.query(RecurringTransaction)
        .filter(RecurringTransaction.id == recurring_id)
        .first()
    )
    if not recurring:
        return None

    recurring.is_active = False
    db.commit()
    return recurring


def _target_day_for_month(day_of_month: int, year: int, month: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return min(day_of_month, last_day)


def _already_materialized(db: Session, recurring_id: int, year: int, month: int) -> bool:
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.recurring_id == recurring_id,
            extract("year", Transaction.created_at) == year,
            extract("month", Transaction.created_at) == month,
        )
        .first()
    )
    return existing is not None


def materialize_recurring(db: Session, recurring: RecurringTransaction) -> Optional[Transaction]:
    now = datetime.utcnow()

    if _already_materialized(db, recurring.id, now.year, now.month):
        return None

    transaction = Transaction(
        original_text=recurring.description,
        description=recurring.description,
        amount=recurring.amount,
        type=recurring.type,
        category=recurring.category,
        family_id=recurring.family_id,
        user_id=recurring.user_id,
        recurring_id=recurring.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def materialize_recurring_if_due(db: Session, recurring: RecurringTransaction) -> Optional[Transaction]:
    now = datetime.utcnow()
    target_day = _target_day_for_month(recurring.day_of_month, now.year, now.month)

    if now.day < target_day:
        return None

    return materialize_recurring(db, recurring)


def process_due_recurring_transactions(db: Session):
    active = (
        db.query(RecurringTransaction)
        .filter(RecurringTransaction.is_active == True)
        .all()
    )

    created = []
    for recurring in active:
        transaction = materialize_recurring_if_due(db, recurring)
        if transaction:
            created.append((recurring, transaction))

    return created
