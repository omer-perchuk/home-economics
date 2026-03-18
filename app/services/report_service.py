from collections import defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Transaction


def parse_month_input(text: str):
    text = text.strip()

    try:
        if "/" in text:
            month_str, year_str = text.split("/")
            month = int(month_str)
            year = int(year_str)

            if 1 <= month <= 12:
                return month, year
    except Exception:
        pass

    month_names = {
        "ינואר": 1,
        "פברואר": 2,
        "מרץ": 3,
        "אפריל": 4,
        "מאי": 5,
        "יוני": 6,
        "יולי": 7,
        "אוגוסט": 8,
        "ספטמבר": 9,
        "אוקטובר": 10,
        "נובמבר": 11,
        "דצמבר": 12,
    }

    parts = text.split()
    if len(parts) == 2:
        month_name, year_str = parts
        if month_name in month_names and year_str.isdigit():
            return month_names[month_name], int(year_str)

    return None


def get_current_month_transactions(db: Session, family_id: int | None = None):
    now = datetime.utcnow()

    query = db.query(Transaction).filter(Transaction.created_at.isnot(None))

    if family_id is not None:
        query = query.filter(Transaction.family_id == family_id)

    transactions = query.all()

    return [
        t for t in transactions
        if t.created_at.month == now.month and t.created_at.year == now.year
    ]


def get_transactions_for_month(
    db: Session,
    month: int,
    year: int,
    family_id: int | None = None,
):
    query = db.query(Transaction).filter(Transaction.created_at.isnot(None))

    if family_id is not None:
        query = query.filter(Transaction.family_id == family_id)

    transactions = query.all()

    return [
        t for t in transactions
        if t.created_at.month == month and t.created_at.year == year
    ]


def get_transactions_by_month(
    db: Session,
    month: int,
    year: int,
    family_id: int | None = None,
):
    return get_transactions_for_month(db, month, year, family_id)


def get_month_summary(
    db: Session,
    month: int,
    year: int,
    family_id: int | None = None,
):
    month_transactions = get_transactions_for_month(db, month, year, family_id)

    expenses_total = sum(t.amount for t in month_transactions if t.type == "expense")
    income_total = sum(t.amount for t in month_transactions if t.type == "income")
    balance = income_total - expenses_total

    categories_map = defaultdict(float)

    for t in month_transactions:
        if t.type == "expense":
            categories_map[t.category] += t.amount

    categories = [
        {"category": category, "amount": amount}
        for category, amount in categories_map.items()
    ]
    categories.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "month": month,
        "year": year,
        "expenses_total": expenses_total,
        "income_total": income_total,
        "balance": balance,
        "categories": categories,
    }


def get_available_months(db: Session, family_id: int | None = None):

    query = db.query(Transaction).filter(Transaction.created_at.isnot(None))

    if family_id is not None:
        query = query.filter(Transaction.family_id == family_id)

    transactions = query.all()

    unique_months = set()

    for t in transactions:
        unique_months.add((t.created_at.year, t.created_at.month))

    # מיון מהחדש לישן
    sorted_months = sorted(unique_months, reverse=True)

    return [
        {
            "year": year,
            "month": month,
        }
        for year, month in sorted_months
    ]


def delete_transaction_by_id(db: Session, transaction_id: int):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not transaction:
        return None

    db.delete(transaction)
    db.commit()

    return transaction


def get_category_summary(db: Session, family_id: int | None = None):
    query = db.query(Transaction)

    if family_id is not None:
        query = query.filter(Transaction.family_id == family_id)

    transactions = query.all()

    summary = defaultdict(float)

    for t in transactions:
        if t.type == "expense":
            summary[t.category] += t.amount

    return [
        {"category": category, "amount": amount}
        for category, amount in summary.items()
    ]