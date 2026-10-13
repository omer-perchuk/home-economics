"""
צנרת משותפת להוספת רשומה: memory -> rule-based -> AI, ואז שמירה + לימוד.
משמשת גם את המסלול המהיר וגם את הסוכן, כדי שהקטגוריזציה תהיה זהה בשניהם.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.services.ai_categorizer import categorize_transaction_text
from app.services.merchant_memory_service import (
    extract_merchant_key,
    find_memory_candidates,
    upsert_memory,
)
from app.services.rule_based_categorizer import (
    ALLOWED_CATEGORIES,
    INCOME_CATEGORIES,
    categorize_by_keywords,
)

# מתחת לזה מציגים למשתמש "לא בטוח בקטגוריה"
AI_CONFIDENCE_THRESHOLD = 0.7


def categorize_entry(db: Session, user_id: int, family_id: int, description: str, amount: float) -> dict:
    """
    מחזיר {"category", "type", "source", "uncertain", "suggestions"}.
    source: memory / rules / ai / none
    """
    merchant_key = extract_merchant_key(description)

    if merchant_key:
        candidates = find_memory_candidates(db, user_id, family_id, merchant_key)
        for scope in ("user", "family", "global"):
            if candidates[scope]:
                best = candidates[scope][0]
                return {
                    "category": best.category,
                    "type": best.tx_type,
                    "source": "memory",
                    "uncertain": False,
                    "suggestions": [],
                }

    rules = categorize_by_keywords(description)
    if rules["category"] != "אחר":
        return {
            "category": rules["category"],
            "type": rules["type"],
            "source": "rules",
            "uncertain": False,
            "suggestions": [],
        }

    ai = categorize_transaction_text(f"{description} {amount:g}")
    if ai.get("confidence", 0) > 0:
        uncertain = ai["category"] == "אחר" or ai.get("confidence", 0) < AI_CONFIDENCE_THRESHOLD
        return {
            "category": ai["category"],
            "type": ai["type"],
            "source": "ai",
            "uncertain": uncertain,
            "suggestions": ai.get("suggestions", []),
        }

    return {
        "category": "אחר",
        "type": "expense",
        "source": "none",
        "uncertain": True,
        "suggestions": [],
    }


def resolve_type(category: str, requested_type: Optional[str] = None) -> str:
    if category in INCOME_CATEGORIES:
        return "income"
    if requested_type in ("income", "expense"):
        return requested_type
    return "expense"


def to_transaction_datetime(entry_date: Optional[date]) -> Optional[datetime]:
    # צהריים – כדי שהפרש שעות מול UTC לא יזיז את הרשומה ליום/חודש אחר
    if entry_date is None:
        return None
    return datetime(entry_date.year, entry_date.month, entry_date.day, 12, 0)


def create_transaction(
    db: Session,
    user,
    family,
    description: str,
    amount: float,
    category: str,
    tx_type: str,
    original_text: Optional[str] = None,
    entry_date: Optional[date] = None,
    learn: bool = True,
) -> Transaction:
    if category not in ALLOWED_CATEGORIES:
        category = "אחר"

    transaction = Transaction(
        original_text=original_text or description,
        description=description,
        amount=amount,
        type=tx_type,
        category=category,
        family_id=family.id,
        user_id=user.id,
        user_phone=user.phone,
    )

    created_at = to_transaction_datetime(entry_date)
    if created_at is not None:
        transaction.created_at = created_at

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # auto-learning: כל רשומה שנשמרה מחזקת את הזיכרון
    merchant_key = extract_merchant_key(description)
    if learn and merchant_key:
        for scope_type, scope_id in (("user", user.id), ("family", family.id), ("global", None)):
            upsert_memory(
                db,
                scope_type=scope_type,
                scope_id=scope_id,
                merchant_key=merchant_key,
                category=category,
                tx_type=tx_type,
            )

    return transaction
