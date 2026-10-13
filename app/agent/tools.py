"""
הכלים של הסוכן. כל כלי הוא עטיפה דקה לשירותים הקיימים.

כלל ברזל: family_id ו-user מגיעים מה-AgentContext (מה-session של WhatsApp),
לעולם לא מהמודל. כל גישה לרשומה לפי id מסוננת לפי המשפחה.
"""
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bot import actions
from app.bot.replies import Reply
from app.db.models import Transaction, User
from app.services.bot_event_service import log_event
from app.services.magic_link_service import create_magic_link
from app.services.merchant_memory_service import remember_transaction_choice, remember_user_category_choice
from app.services.recurring_service import create_recurring, get_active_recurring, materialize_recurring_if_due
from app.services.report_service import get_month_summary
from app.services.rule_based_categorizer import ALLOWED_CATEGORIES, INCOME_CATEGORIES
from app.services.transaction_entry_service import (
    categorize_entry,
    create_transaction,
    resolve_type,
    to_transaction_datetime,
)
from app.services.whatsapp_format_service import format_short_amount, format_transaction_line

MAX_SEARCH_RESULTS = 30


@dataclass
class AgentContext:
    db: Session
    user: Any
    family: Any
    phone: str
    # מה שהכלים מבקשים לצרף לתשובה הסופית
    confirm_reply: Optional[Reply] = None
    undo_event_id: Optional[int] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    tool_log: List[str] = field(default_factory=list)


class ToolError(Exception):
    pass


# ===============================
# עזרים
# ===============================

def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ToolError(f"תאריך לא תקין: {value}. השתמש בפורמט YYYY-MM-DD")


def _valid_category(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value not in ALLOWED_CATEGORIES:
        raise ToolError(f"קטגוריה לא קיימת: {value}. קטגוריות מותרות: {', '.join(ALLOWED_CATEGORIES)}")
    return value


def _tx_dict(t: Transaction, user_names: Dict[int, str]) -> dict:
    return {
        "id": t.id,
        "date": t.created_at.strftime("%Y-%m-%d") if t.created_at else None,
        "description": t.description,
        "amount": t.amount,
        "type": t.type,
        "category": t.category,
        "added_by": user_names.get(t.user_id),
        "recurring": t.recurring_id is not None,
    }


def _family_user_names(ctx: AgentContext) -> Dict[int, str]:
    users = ctx.db.query(User).filter(User.family_id == ctx.family.id).all()
    return {u.id: u.name for u in users}


# ===============================
# כלים
# ===============================

def search_transactions(
    ctx: AgentContext,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    text: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 15,
):
    query = ctx.db.query(Transaction).filter(Transaction.family_id == ctx.family.id)

    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start:
        query = query.filter(Transaction.created_at >= datetime.combine(start, datetime.min.time()))
    if end:
        query = query.filter(Transaction.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()))

    category = _valid_category(category)
    if category:
        query = query.filter(Transaction.category == category)

    if type in ("income", "expense"):
        query = query.filter(Transaction.type == type)

    if text:
        pattern = f"%{text.strip()}%"
        query = query.filter(or_(Transaction.description.ilike(pattern), Transaction.original_text.ilike(pattern)))

    matches = query.order_by(Transaction.created_at.desc(), Transaction.id.desc()).all()
    limit = max(1, min(int(limit or 15), MAX_SEARCH_RESULTS))
    names = _family_user_names(ctx)

    return {
        "count": len(matches),
        "total_expenses": round(sum(t.amount for t in matches if t.type == "expense"), 2),
        "total_income": round(sum(t.amount for t in matches if t.type == "income"), 2),
        "showing": min(limit, len(matches)),
        "items": [_tx_dict(t, names) for t in matches[:limit]],
    }


def get_monthly_summary(ctx: AgentContext, month: int, year: int):
    summary = get_month_summary(ctx.db, int(month), int(year), ctx.family.id)
    return {
        "month": summary["month"],
        "year": summary["year"],
        "expenses_total": round(summary["expenses_total"], 2),
        "income_total": round(summary["income_total"], 2),
        "balance": round(summary["balance"], 2),
        "expenses_by_category": [
            {"category": c["category"], "amount": round(c["amount"], 2)} for c in summary["categories"]
        ],
    }


def add_transactions(ctx: AgentContext, items: List[dict]):
    if not items:
        raise ToolError("לא התקבלו רשומות להוספה")

    created = []
    for item in items:
        description = str(item.get("description", "")).strip()
        try:
            amount = float(item.get("amount", 0))
        except (TypeError, ValueError):
            raise ToolError(f"סכום לא תקין: {item.get('amount')}")
        if not description or amount <= 0:
            raise ToolError("לכל רשומה צריך תיאור וסכום חיובי")

        entry_date = _parse_date(item.get("date"))
        category = _valid_category(item.get("category"))
        if category:
            tx_type = resolve_type(category, item.get("type"))
        else:
            result = categorize_entry(ctx.db, ctx.user.id, ctx.family.id, description, amount)
            category = result["category"]
            tx_type = resolve_type(category, item.get("type") or result["type"])

        transaction = create_transaction(
            ctx.db,
            ctx.user,
            ctx.family,
            description=description,
            amount=amount,
            category=category,
            tx_type=tx_type,
            entry_date=entry_date,
        )
        created.append(transaction)

    ids = [t.id for t in created]
    event = log_event(
        ctx.db, ctx.user.id, ctx.family.id, "assistant",
        "נוספו רשומות: " + "; ".join(format_transaction_line(t) for t in created),
        action={"kind": "add", "transaction_ids": ids},
    )
    ctx.undo_event_id = event.id

    names = _family_user_names(ctx)
    return {"added": [_tx_dict(t, names) for t in created]}


def update_transaction(
    ctx: AgentContext,
    transaction_id: int,
    description: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
):
    t = actions.get_family_transaction(ctx.db, ctx.family.id, int(transaction_id))
    if not t:
        raise ToolError(f"לא נמצאה רשומה {transaction_id}")

    before = actions.transaction_snapshot(t)

    if description:
        t.description = description.strip()
    if amount is not None:
        amount = float(amount)
        if amount <= 0:
            raise ToolError("סכום חייב להיות חיובי")
        t.amount = amount
    category = _valid_category(category)
    if category:
        t.category = category
        t.type = "income" if category in INCOME_CATEGORIES else "expense"
    new_date = _parse_date(date)
    if new_date:
        t.created_at = to_transaction_datetime(new_date)

    ctx.db.commit()

    if category:
        remember_transaction_choice(
            db=ctx.db,
            user_id=ctx.user.id,
            family_id=ctx.family.id,
            original_text=t.original_text,
            description=t.description,
            category=t.category,
            tx_type=t.type,
        )

    event = log_event(
        ctx.db, ctx.user.id, ctx.family.id, "assistant",
        f"עודכנה רשומה {t.id}: {format_transaction_line(t, include_date=True)}",
        action={"kind": "update", "before": before},
    )
    ctx.undo_event_id = event.id

    return {"updated": _tx_dict(t, _family_user_names(ctx))}


def delete_transactions(ctx: AgentContext, transaction_ids: List[int]):
    found = []
    for transaction_id in transaction_ids or []:
        t = actions.get_family_transaction(ctx.db, ctx.family.id, int(transaction_id))
        if t:
            found.append(t)

    if not found:
        raise ToolError("לא נמצאו רשומות כאלה")

    lines = [format_transaction_line(t, include_date=True) for t in found]
    ctx.confirm_reply = actions.request_confirmation(
        ctx.phone,
        "delete_transactions",
        [t.id for t in found],
        "\n".join([f"🗑️ למחוק {len(found)} רשומות?", *lines]),
    )
    return {
        "status": "awaiting_user_confirmation",
        "note": "המחיקה לא בוצעה עדיין. נשלחו למשתמש כפתורי אישור. אל תכתוב שהרשומות נמחקו.",
        "items": [{"id": t.id, "description": t.description, "amount": t.amount} for t in found],
    }


def list_recurring(ctx: AgentContext):
    return {
        "recurring": [
            {
                "id": r.id,
                "description": r.description,
                "amount": r.amount,
                "category": r.category,
                "type": r.type,
                "day_of_month": r.day_of_month,
            }
            for r in get_active_recurring(ctx.db, ctx.family.id)
        ]
    }


def add_recurring(
    ctx: AgentContext,
    description: str,
    amount: float,
    day_of_month: int,
    category: Optional[str] = None,
):
    amount = float(amount)
    day_of_month = int(day_of_month)
    if amount <= 0:
        raise ToolError("סכום חייב להיות חיובי")
    if not 1 <= day_of_month <= 28:
        raise ToolError("יום בחודש חייב להיות בין 1 ל-28")

    category = _valid_category(category)
    if not category:
        category = categorize_entry(ctx.db, ctx.user.id, ctx.family.id, description, amount)["category"]

    recurring = create_recurring(
        ctx.db,
        family_id=ctx.family.id,
        user_id=ctx.user.id,
        description=description.strip(),
        amount=amount,
        tx_type=resolve_type(category),
        category=category,
        day_of_month=day_of_month,
    )
    materialized = materialize_recurring_if_due(ctx.db, recurring)

    event = log_event(
        ctx.db, ctx.user.id, ctx.family.id, "assistant",
        f"נוספה הוראת קבע {recurring.id}: {recurring.description} {format_short_amount(amount)} ₪ כל {day_of_month} לחודש",
        action={
            "kind": "recurring_add",
            "recurring_ids": [recurring.id],
            "transaction_ids": [materialized.id] if materialized else [],
        },
    )
    ctx.undo_event_id = event.id

    return {
        "created": {"id": recurring.id, "description": recurring.description, "amount": amount,
                    "category": category, "day_of_month": day_of_month},
        "charged_this_month": materialized is not None,
    }


def cancel_recurring(ctx: AgentContext, recurring_id: int):
    active = {r.id: r for r in get_active_recurring(ctx.db, ctx.family.id)}
    r = active.get(int(recurring_id))
    if not r:
        raise ToolError(f"לא נמצאה הוראת קבע פעילה {recurring_id}")

    ctx.confirm_reply = actions.request_confirmation(
        ctx.phone,
        "cancel_recurring",
        [r.id],
        f"🛑 לבטל את הוראת הקבע?\n🔁 {r.description} — {format_short_amount(r.amount)} ₪ (כל {r.day_of_month} לחודש)",
    )
    return {
        "status": "awaiting_user_confirmation",
        "note": "הביטול לא בוצע עדיין. נשלחו למשתמש כפתורי אישור.",
    }


def remember_merchant(ctx: AgentContext, merchant: str, category: str):
    category = _valid_category(category)
    if not category:
        raise ToolError("חסרה קטגוריה")
    remember_user_category_choice(
        db=ctx.db,
        user_id=ctx.user.id,
        family_id=ctx.family.id,
        source_text=merchant,
        category=category,
        tx_type=resolve_type(category),
    )
    return {"remembered": {"merchant": merchant, "category": category}}


def get_site_link(ctx: AgentContext, page: str = "dashboard"):
    redirect = "/guide" if page == "guide" else "/"
    ctx.cta_url = create_magic_link(user_id=ctx.user.id, family_id=ctx.family.id, redirect_to=redirect)
    ctx.cta_text = "פתח את המדריך 👇" if page == "guide" else "לחץ להיכנס לאתר 👇"
    return {"status": "הקישור יישלח למשתמש ככפתור נפרד אחרי התשובה שלך. אל תכתוב קישור בעצמך."}


# ===============================
# הגדרות הכלים למודל
# ===============================

_DATE = {"type": "string", "description": "תאריך בפורמט YYYY-MM-DD"}
_CATEGORY = {"type": "string", "enum": ALLOWED_CATEGORIES}


def _tool(name: str, description: str, properties: dict, required: Optional[List[str]] = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


TOOL_DEFINITIONS = [
    _tool(
        "search_transactions",
        "חיפוש רשומות (הוצאות והכנסות) של המשפחה עם סינון. מחזיר מספר תוצאות, סכומים כוללים ורשימת רשומות "
        "(עם id). השתמש בזה כדי לענות על שאלות 'כמה הוצאנו על...', וכדי למצוא id של רשומה לפני עדכון או מחיקה.",
        {
            "date_from": _DATE,
            "date_to": {**_DATE, "description": "תאריך סיום כולל, בפורמט YYYY-MM-DD"},
            "category": _CATEGORY,
            "text": {"type": "string", "description": "חיפוש חופשי בתיאור הרשומה, למשל 'ארומה' או 'סופר'"},
            "type": {"type": "string", "enum": ["expense", "income"]},
            "limit": {"type": "integer", "description": "כמה רשומות להחזיר (ברירת מחדל 15, מקסימום 30)"},
        },
    ),
    _tool(
        "get_monthly_summary",
        "סיכום חודשי: סה\"כ הוצאות, הכנסות, מאזן, והוצאות לפי קטגוריה.",
        {"month": {"type": "integer"}, "year": {"type": "integer"}},
        ["month", "year"],
    ),
    _tool(
        "add_transactions",
        "הוספת רשומה אחת או יותר. אם לא ידוע לך מה הקטגוריה – אל תשלח category, המערכת תסווג לבד.",
        {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "תיאור קצר, בדרך כלל שם העסק"},
                        "amount": {"type": "number"},
                        "date": {**_DATE, "description": "רק אם המשתמש ציין תאריך שאינו היום"},
                        "category": _CATEGORY,
                        "type": {"type": "string", "enum": ["expense", "income"]},
                    },
                    "required": ["description", "amount"],
                },
            }
        },
        ["items"],
    ),
    _tool(
        "update_transaction",
        "עדכון רשומה קיימת לפי id. שלח רק את השדות שמשתנים. השינוי מתבצע מיד וניתן לביטול.",
        {
            "transaction_id": {"type": "integer"},
            "description": {"type": "string"},
            "amount": {"type": "number"},
            "category": _CATEGORY,
            "date": _DATE,
        },
        ["transaction_id"],
    ),
    _tool(
        "delete_transactions",
        "בקשת מחיקה של רשומות לפי id. לא מוחק מיד – שולח למשתמש כפתורי אישור.",
        {"transaction_ids": {"type": "array", "items": {"type": "integer"}}},
        ["transaction_ids"],
    ),
    _tool("list_recurring", "רשימת הוראות הקבע הפעילות של המשפחה.", {}),
    _tool(
        "add_recurring",
        "הוספת הוראת קבע חודשית (תשלום או הכנסה שחוזרים כל חודש).",
        {
            "description": {"type": "string"},
            "amount": {"type": "number"},
            "day_of_month": {"type": "integer", "description": "יום בחודש, 1 עד 28"},
            "category": _CATEGORY,
        },
        ["description", "amount", "day_of_month"],
    ),
    _tool(
        "cancel_recurring",
        "בקשת ביטול הוראת קבע לפי id. לא מבטל מיד – שולח למשתמש כפתורי אישור.",
        {"recurring_id": {"type": "integer"}},
        ["recurring_id"],
    ),
    _tool(
        "remember_merchant",
        "לזכור שבית עסק מסוים שייך תמיד לקטגוריה מסוימת (למשל 'ארומה זה תמיד אוכל בחוץ').",
        {"merchant": {"type": "string"}, "category": _CATEGORY},
        ["merchant", "category"],
    ),
    _tool(
        "get_site_link",
        "שליחת קישור כניסה מאובטח לאתר (dashboard) או למדריך (guide).",
        {"page": {"type": "string", "enum": ["dashboard", "guide"]}},
    ),
]

TOOL_FUNCTIONS: Dict[str, Callable] = {
    "search_transactions": search_transactions,
    "get_monthly_summary": get_monthly_summary,
    "add_transactions": add_transactions,
    "update_transaction": update_transaction,
    "delete_transactions": delete_transactions,
    "list_recurring": list_recurring,
    "add_recurring": add_recurring,
    "cancel_recurring": cancel_recurring,
    "remember_merchant": remember_merchant,
    "get_site_link": get_site_link,
}


def run_tool(ctx: AgentContext, name: str, arguments_json: str) -> str:
    """
    מריץ כלי ומחזיר JSON כטקסט. שגיאות חוזרות למודל כטקסט כדי שיוכל לתקן ולנסות שוב.
    """
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return json.dumps({"error": f"כלי לא מוכר: {name}"}, ensure_ascii=False)

    try:
        arguments = json.loads(arguments_json or "{}")
        if not isinstance(arguments, dict):
            raise ToolError("הארגומנטים חייבים להיות אובייקט")
        result = func(ctx, **arguments)
    except ToolError as e:
        ctx.db.rollback()
        result = {"error": str(e)}
    except TypeError as e:
        ctx.db.rollback()
        result = {"error": f"ארגומנטים לא תקינים: {e}"}
    except Exception as e:
        ctx.db.rollback()
        print(f"=== AGENT TOOL ERROR === {name}: {e}")
        result = {"error": "שגיאה פנימית בהרצת הכלי"}

    ctx.tool_log.append(name)
    return json.dumps(result, ensure_ascii=False, default=str)
