from datetime import datetime

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.db.models import Transaction


HEBREW_MONTHS = {
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
from sqlalchemy import func, extract


def get_available_months(db: Session):
    results = (
        db.query(
            extract("year", Transaction.created_at).label("year"),
            extract("month", Transaction.created_at).label("month")
        )
        .distinct()
        .order_by(
            extract("year", Transaction.created_at).desc(),
            extract("month", Transaction.created_at).desc()
        )
        .all()
    )

    return [
        {"year": int(year), "month": int(month)}
        for year, month in results
    ]


def get_transactions_by_month(db: Session, month: int, year: int):
    return (
        db.query(Transaction)
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )

def get_category_summary(db: Session):
    results = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount)
        )
        .filter(Transaction.type == "expense")
        .group_by(Transaction.category)
        .all()
    )

    return {category: float(amount) for category, amount in results}


def get_current_month_transactions(db: Session):
    now = datetime.utcnow()
    month = now.month
    year = now.year

    return (
        db.query(Transaction)
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )


def get_transactions_by_month(db: Session, month: int, year: int):
    return (
        db.query(Transaction)
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )


def delete_transaction_by_id(db: Session, transaction_id: int):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if transaction:
        db.delete(transaction)
        db.commit()

    return transaction


def format_transactions_for_whatsapp(transactions, include_delete_hint: bool = False):
    if not transactions:
        return "אין רשומות לתצוגה."

    lines = ["רשומות:\n"]

    for i, t in enumerate(transactions, start=1):
        date_str = t.created_at.strftime("%d/%m")
        lines.append(
            f"{i}. {date_str} | {t.description} | {t.amount:.2f} ₪ | {t.category}"
        )

    if include_delete_hint:
        lines.append("\nשלח מספר או מספרים למחיקה (לדוגמה: 2 או 2,4)")

    return "\n".join(lines)


def get_month_summary(db: Session, month: int, year: int):
    expenses_total = (
        db.query(func.sum(Transaction.amount))
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
            Transaction.type == "expense",
        )
        .scalar()
    ) or 0.0

    income_total = (
        db.query(func.sum(Transaction.amount))
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
            Transaction.type == "income",
        )
        .scalar()
    ) or 0.0

    category_results = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount)
        )
        .filter(
            extract("month", Transaction.created_at) == month,
            extract("year", Transaction.created_at) == year,
            Transaction.type == "expense",
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    category_summary = [
        {"category": category, "amount": float(amount)}
        for category, amount in category_results
    ]

    return {
        "month": month,
        "year": year,
        "expenses_total": float(expenses_total),
        "income_total": float(income_total),
        "balance": float(income_total) - float(expenses_total),
        "categories": category_summary,
    }


def format_summary_for_whatsapp(summary: dict) -> str:
    lines = [
        f"סיכום עבור {summary['month']:02d}/{summary['year']}\n",
        f"הוצאות: {summary['expenses_total']:.2f} ₪",
        f"הכנסות: {summary['income_total']:.2f} ₪",
        f"מאזן: {summary['balance']:.2f} ₪",
    ]

    if summary["categories"]:
        lines.append("\nחלוקה לפי קטגוריות:")
        for item in summary["categories"]:
            lines.append(f"• {item['category']}: {item['amount']:.2f} ₪")
    else:
        lines.append("\nאין נתונים לחודש הזה.")

    return "\n".join(lines)


def parse_month_input(text: str):
    text = text.strip()

    if "/" in text:
        parts = text.split("/")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            month = int(parts[0])
            year = int(parts[1])

            if 1 <= month <= 12:
                return month, year

    for month_name, month_number in HEBREW_MONTHS.items():
        if month_name in text:
            year_parts = [part for part in text.split() if part.isdigit()]
            if year_parts:
                return month_number, int(year_parts[0])

    return None