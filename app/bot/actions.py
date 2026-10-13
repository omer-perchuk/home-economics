"""
פעולות של הבוט שמשותפות למסלול המהיר, לכפתורים ולסוכן.
כל פונקציה מחזירה Reply – השליחה עצמה נעשית בשכבה שקראה לה.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.bot.replies import Reply
from app.db.models import RecurringTransaction, Transaction
from app.services.bot_event_service import get_undoable_action, log_event, mark_action_undone
from app.services.merchant_memory_service import remember_transaction_choice
from app.services.recurring_service import deactivate_recurring
from app.services.report_service import delete_transaction_by_id, get_month_summary
from app.services.rule_based_categorizer import ALLOWED_CATEGORIES, INCOME_CATEGORIES
from app.services.state_service import clear_user_state, set_user_state
from app.services.transaction_entry_service import categorize_entry, create_transaction, resolve_type
from app.services.whatsapp_format_service import (
    format_added_entries_message,
    format_short_amount,
    format_summary_for_whatsapp_short,
    format_transaction_line,
    format_updated_transaction_message,
)

# מזהי כפתורים (חוזרים ל-webhook כ-interactive reply)
BTN_UNDO = "undo"
BTN_SUMMARY = "summary"
BTN_CATEGORY = "cat"
BTN_SET_CATEGORY = "setcat"
BTN_MORE_CATEGORIES = "catmore"
BTN_CONFIRM_YES = "confirm:yes"
BTN_CONFIRM_NO = "confirm:no"

CONFIRM_ACTION = "confirm_action"


# ===============================
# snapshot – לשחזור במחיקה / עדכון
# ===============================

def transaction_snapshot(t: Transaction) -> dict:
    return {
        "id": t.id,
        "original_text": t.original_text,
        "description": t.description,
        "amount": t.amount,
        "type": t.type,
        "category": t.category,
        "user_id": t.user_id,
        "user_phone": t.user_phone,
        "recurring_id": t.recurring_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def get_family_transaction(db: Session, family_id: int, transaction_id: int) -> Optional[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.family_id == family_id)
        .first()
    )


# ===============================
# הוספה מהירה
# ===============================

def fast_add(db: Session, user, family, entries: List[dict]) -> Reply:
    created = []
    uncertain_ids = set()

    for entry in entries:
        result = categorize_entry(db, user.id, family.id, entry["description"], entry["amount"])
        transaction = create_transaction(
            db,
            user,
            family,
            description=entry["description"],
            amount=entry["amount"],
            category=result["category"],
            tx_type=resolve_type(result["category"], result["type"]),
            original_text=entry["original_text"],
            entry_date=entry.get("date"),
        )
        created.append(transaction)
        if result["uncertain"]:
            uncertain_ids.add(transaction.id)

    show_dates = any(entry.get("date") for entry in entries)
    text = format_added_entries_message(created, uncertain_ids, show_dates=show_dates)

    ids = [t.id for t in created]
    event = log_event(
        db,
        user.id,
        family.id,
        "assistant",
        f"{text}\n(מזהי רשומות: {', '.join(str(i) for i in ids)})",
        action={"kind": "add", "transaction_ids": ids},
    )

    buttons = [(f"{BTN_UNDO}:{event.id}", "↩️ בטל")]
    if len(created) == 1:
        buttons.append((f"{BTN_CATEGORY}:{created[0].id}", "🏷️ קטגוריה"))
    buttons.append((BTN_SUMMARY, "📊 סיכום"))

    return Reply(text=text, buttons=buttons)


# ===============================
# ביטול פעולה אחרונה
# ===============================

def undo_last_action(db: Session, user, family, event_id: Optional[int] = None) -> Reply:
    event, action = get_undoable_action(db, user.id, event_id)
    if not event:
        return Reply(text="אין פעולה אחרונה לביטול.")

    kind = action.get("kind")
    lines = []

    if kind == "add":
        for transaction_id in action.get("transaction_ids", []):
            t = delete_transaction_by_id(db, transaction_id, family.id)
            if t:
                lines.append(format_transaction_line(t))
        title = "↩️ בוטלה ההוספה:"

    elif kind == "delete":
        for snap in action.get("snapshots", []):
            restored = Transaction(
                original_text=snap["original_text"],
                description=snap["description"],
                amount=snap["amount"],
                type=snap["type"],
                category=snap["category"],
                family_id=family.id,
                user_id=snap["user_id"],
                user_phone=snap["user_phone"],
                recurring_id=snap["recurring_id"],
            )
            if snap.get("created_at"):
                restored.created_at = datetime.fromisoformat(snap["created_at"])
            db.add(restored)
            db.commit()
            lines.append(format_transaction_line(restored))
        title = "↩️ הרשומות שוחזרו:"

    elif kind == "update":
        snap = action.get("before", {})
        t = get_family_transaction(db, family.id, snap.get("id"))
        if t:
            t.description = snap["description"]
            t.amount = snap["amount"]
            t.category = snap["category"]
            t.type = snap["type"]
            if snap.get("created_at"):
                t.created_at = datetime.fromisoformat(snap["created_at"])
            db.commit()
            lines.append(format_transaction_line(t))
        title = "↩️ העדכון בוטל:"

    elif kind == "recurring_add":
        for recurring_id in action.get("recurring_ids", []):
            r = deactivate_recurring(db, recurring_id, family.id)
            if r:
                lines.append(f"🔁 {r.description} — {format_short_amount(r.amount)} ₪")
        for transaction_id in action.get("transaction_ids", []):
            delete_transaction_by_id(db, transaction_id, family.id)
        title = "↩️ הוראת הקבע בוטלה:"

    elif kind == "recurring_cancel":
        for recurring_id in action.get("recurring_ids", []):
            r = (
                db.query(RecurringTransaction)
                .filter(RecurringTransaction.id == recurring_id, RecurringTransaction.family_id == family.id)
                .first()
            )
            if r:
                r.is_active = True
                db.commit()
                lines.append(f"🔁 {r.description} — {format_short_amount(r.amount)} ₪")
        title = "↩️ הוראת הקבע הופעלה מחדש:"

    else:
        return Reply(text="אין פעולה אחרונה לביטול.")

    mark_action_undone(db, event)

    if not lines:
        return Reply(text="הפעולה כבר לא קיימת – אין מה לבטל.")

    text = "\n".join([title, *lines])
    log_event(db, user.id, family.id, "assistant", text)
    return Reply(text=text)


# ===============================
# קטגוריה – בחירה מכפתורים
# ===============================

def category_picker(db: Session, family, transaction_id: int, suggestions: Optional[List[str]] = None) -> Reply:
    t = get_family_transaction(db, family.id, transaction_id)
    if not t:
        return Reply(text="לא נמצאה הרשומה.")

    ordered = []
    for category in (suggestions or []) + ALLOWED_CATEGORIES:
        if category != t.category and category in ALLOWED_CATEGORIES and category not in ordered:
            ordered.append(category)

    # עד 10 שורות ברשימה – 9 קטגוריות + "עוד"
    rows = [
        (f"{BTN_SET_CATEGORY}:{t.id}:{ALLOWED_CATEGORIES.index(category)}", category, "")
        for category in ordered[:9]
    ]
    rows.append((f"{BTN_MORE_CATEGORIES}:{t.id}", "עוד קטגוריות…", "רשימה מלאה ממוספרת"))

    return Reply(
        text=f"🏷️ לאיזו קטגוריה להעביר?\n{format_transaction_line(t)}",
        list_rows=rows,
        list_button="בחר קטגוריה",
    )


def set_transaction_category(db: Session, user, family, transaction_id: int, category: str) -> Reply:
    t = get_family_transaction(db, family.id, transaction_id)
    if not t or category not in ALLOWED_CATEGORIES:
        return Reply(text="לא נמצאה הרשומה.")

    before = transaction_snapshot(t)
    t.category = category
    t.type = "income" if category in INCOME_CATEGORIES else "expense"
    db.commit()

    remember_transaction_choice(
        db=db,
        user_id=user.id,
        family_id=family.id,
        original_text=t.original_text,
        description=t.description,
        category=t.category,
        tx_type=t.type,
    )

    text = format_updated_transaction_message(t) + "\n🧠 אזכור את זה לפעם הבאה."
    log_event(db, user.id, family.id, "assistant", text, action={"kind": "update", "before": before})
    return Reply(text=text)


# ===============================
# אישור פעולות הרסניות
# ===============================

def request_confirmation(phone: str, kind: str, ids: List[int], summary_text: str) -> Reply:
    set_user_state(phone, {"action": CONFIRM_ACTION, "kind": kind, "ids": ids})
    return Reply(
        text=summary_text,
        buttons=[(BTN_CONFIRM_YES, "✅ כן"), (BTN_CONFIRM_NO, "❌ לא")],
    )


def execute_confirmation(db: Session, user, family, phone: str, pending: dict, confirmed: bool) -> Reply:
    clear_user_state(phone)

    if not confirmed:
        text = "👍 בוטל, לא שיניתי כלום."
        log_event(db, user.id, family.id, "assistant", text)
        return Reply(text=text)

    kind = pending.get("kind")
    ids = pending.get("ids", [])

    if kind == "delete_transactions":
        snapshots = []
        lines = []
        for transaction_id in ids:
            t = get_family_transaction(db, family.id, transaction_id)
            if not t:
                continue
            snapshots.append(transaction_snapshot(t))
            lines.append(format_transaction_line(t))
            delete_transaction_by_id(db, transaction_id, family.id)

        if not lines:
            return Reply(text="הרשומות כבר לא קיימות.")

        text = "\n".join([f"🗑️ נמחקו {len(lines)} רשומות:", *lines])
        event = log_event(db, user.id, family.id, "assistant", text, action={"kind": "delete", "snapshots": snapshots})
        return Reply(text=text, buttons=[(f"{BTN_UNDO}:{event.id}", "↩️ שחזר")])

    if kind == "cancel_recurring":
        lines = []
        cancelled = []
        for recurring_id in ids:
            r = deactivate_recurring(db, recurring_id, family.id)
            if r:
                cancelled.append(r.id)
                lines.append(f"🔁 {r.description} — {format_short_amount(r.amount)} ₪")

        if not lines:
            return Reply(text="הוראת הקבע כבר לא קיימת.")

        text = "\n".join(["🛑 הוראת קבע בוטלה:", *lines])
        event = log_event(
            db, user.id, family.id, "assistant", text,
            action={"kind": "recurring_cancel", "recurring_ids": cancelled},
        )
        return Reply(text=text, buttons=[(f"{BTN_UNDO}:{event.id}", "↩️ שחזר")])

    return Reply(text="לא הבנתי מה לאשר.")


# ===============================
# סיכום חודש
# ===============================

def month_summary_reply(db: Session, family, month: int, year: int) -> Reply:
    summary = get_month_summary(db, month, year, family.id)
    return Reply(text=f"{format_summary_for_whatsapp_short(summary)}\n\n💡 לחודש אחר שלח: סיכום ספטמבר / סיכום שעבר")
