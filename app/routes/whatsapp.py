import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Transaction, User

from app.services.merchant_memory_service import (
    extract_merchant_key,
    upsert_memory,
    find_memory_candidates,
    remember_transaction_choice,
)
from app.services.rule_based_categorizer import categorize_by_keywords, ALLOWED_CATEGORIES, INCOME_CATEGORIES
from app.services.message_intent_service import classify_message_intent
from app.services.magic_link_service import create_magic_link
from app.services.ai_categorizer import categorize_transaction_text
from app.services.report_service import (
    get_current_month_transactions,
    get_month_summary,
    parse_month_input,
    delete_transaction_by_id,
)
from app.services.onboarding_service import (
    get_or_create_user_by_phone,
    create_family_for_user,
    find_admin_by_phone,
    create_join_request,
    get_pending_join_request_for_admin,
    approve_join_request,
    reject_join_request,
)
from app.services.state_service import (
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.services.command_service import detect_command
from app.services.family_service import get_user_and_family_by_phone
from app.services.recurring_service import (
    create_recurring,
    get_active_recurring,
    deactivate_recurring,
    materialize_recurring_if_due,
)
from app.services.whatsapp_client import (
    send_whatsapp_message,
    send_whatsapp_cta_button,
)
from app.services.whatsapp_format_service import (
    format_summary_for_whatsapp_short,
    format_transactions_for_whatsapp_short,
    format_updated_transaction_message,
    format_added_transaction_message,
    format_deleted_transactions_message,
    format_help_message,
    format_short_amount,
    format_recurring_for_whatsapp,
    format_added_recurring_message,
    format_deleted_recurring_message,
)

from app.services.bot_event_service import log_event, mark_message_processed
from app.bot.fast_path import parse_entries
from app.bot.replies import Reply, send_reply
from app.bot.actions import (
    BTN_CATEGORY,
    BTN_CONFIRM_NO,
    BTN_CONFIRM_YES,
    BTN_MORE_CATEGORIES,
    BTN_SET_CATEGORY,
    BTN_SUMMARY,
    BTN_UNDO,
    CONFIRM_ACTION,
    category_picker,
    execute_confirmation,
    fast_add,
    month_summary_reply,
    set_transaction_category,
    undo_last_action,
)
from app.agent.llm import agent_enabled
from app.agent.runner import run_agent_and_reply

print("=== WHATSAPP ROUTE LOADED ===")

router = APIRouter()

DASHBOARD_URL = "https://main.d11fqx2zyfwk68.amplifyapp.com"

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")


def normalize_phone_for_db(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return phone

    if digits.startswith("0"):
        digits = "972" + digits[1:]

    if not digits.startswith("972"):
        digits = f"972{digits}"

    return f"whatsapp:+{digits}"


def normalize_admin_phone_input(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return phone

    if digits.startswith("0"):
        digits = "972" + digits[1:]

    if not digits.startswith("972"):
        digits = f"972{digits}"

    return f"whatsapp:+{digits}"


UNDO_PHRASES = ["מחק אחרון", "מחק את האחרון", "בטל אחרון", "בטל את האחרון", "תבטל את האחרון", "undo"]
CONFIRM_YES_WORDS = ["כן", "כן תמחק", "מאשר", "אישור", "yes", "y", "1"]
CONFIRM_NO_WORDS = ["לא", "no", "n", "2"]


def handle_interactive(db: Session, user, family, sender: str, interactive_id: str, user_state):
    """
    לחיצות על כפתורים / שורות ברשימה. מחזיר Reply, או None אם ה-id לא מוכר.
    """
    parts = interactive_id.split(":")
    kind = parts[0]

    if kind == BTN_UNDO:
        event_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        return undo_last_action(db, user, family, event_id)

    if kind == BTN_SUMMARY:
        now = datetime.utcnow()
        reply = month_summary_reply(db, family, now.month, now.year)
        reply.cta_text = "לחץ להיכנס לאתר 👇"
        reply.cta_url = create_magic_link(user_id=user.id, family_id=family.id)
        return reply

    if kind == BTN_CATEGORY and len(parts) == 2 and parts[1].isdigit():
        return category_picker(db, family, int(parts[1]))

    if kind == BTN_SET_CATEGORY and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        index = int(parts[2])
        if 0 <= index < len(ALLOWED_CATEGORIES):
            return set_transaction_category(db, user, family, int(parts[1]), ALLOWED_CATEGORIES[index])
        return None

    if kind == BTN_MORE_CATEGORIES and len(parts) == 2 and parts[1].isdigit():
        # הרשימה המלאה – ממשיכה בזרימת העדכון הממוספרת הקיימת
        set_user_state(sender, {"action": "update_field_value", "transaction_id": int(parts[1]), "field": "category"})
        categories_list = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(ALLOWED_CATEGORIES)])
        return Reply(text=f"📂 בחר קטגוריה (שלח מספר):\n{categories_list}")

    if interactive_id in (BTN_CONFIRM_YES, BTN_CONFIRM_NO):
        if not user_state or user_state.get("action") != CONFIRM_ACTION:
            return Reply(text="הבקשה הזו כבר לא בתוקף.")
        return execute_confirmation(db, user, family, sender, user_state, confirmed=interactive_id == BTN_CONFIRM_YES)

    return None


def build_empty_ok_response() -> Response:
    return Response(status_code=200, content="")


@router.get("/debug/webhook-test")
async def debug_webhook_test():
    return {"ok": True, "route": "whatsapp webhook file loaded"}


@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print("=== VERIFY WEBHOOK HIT ===")
    print("=== MODE ===", mode)
    print("=== TOKEN ===", token)
    print("=== EXPECTED TOKEN ===", META_VERIFY_TOKEN)

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "", status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    print("=== POST /webhook/whatsapp HIT ===")

    body = await request.json()
    print("=== INCOMING META WEBHOOK ===", body)

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages", [])
        if not messages:
            print("=== NO MESSAGES IN WEBHOOK ===")
            return build_empty_ok_response()

        message_data = messages[0]
        message_type = message_data.get("type")
        message_id = message_data.get("id", "")

        # לחיצה על כפתור / בחירה מרשימה – ה-id של הכפתור מגיע כ-interactive_id
        interactive_id = None
        interactive_title = None

        if message_type == "text":
            raw_message = message_data["text"]["body"].strip()
        elif message_type == "interactive":
            interactive = message_data.get("interactive", {})
            reply_data = interactive.get("button_reply") or interactive.get("list_reply") or {}
            interactive_id = reply_data.get("id", "")
            interactive_title = reply_data.get("title", "")
            raw_message = interactive_title
        else:
            print("=== UNSUPPORTED MESSAGE TYPE IGNORED ===", message_type)
            return build_empty_ok_response()

        message = raw_message.lower().strip()

        sender_raw = message_data.get("from", "")
        sender = normalize_phone_for_db(sender_raw)

        print("=== RAW MESSAGE ===", raw_message, "| INTERACTIVE ID ===", interactive_id)
        print("=== SENDER RAW ===", sender_raw)
        print("=== SENDER NORMALIZED ===", sender)

    except Exception as e:
        print(f"Failed to parse Meta webhook: {e}")
        return build_empty_ok_response()

    # Meta שולחת שוב הודעות אם התשובה התעכבה – לא מעבדים פעמיים
    if not mark_message_processed(db, message_id):
        print("=== DUPLICATE MESSAGE IGNORED ===", message_id)
        return build_empty_ok_response()

    user = get_or_create_user_by_phone(db, sender)
    family = None

    if user.family_id:
        user, family = get_user_and_family_by_phone(db, sender)

    print("=== USER FOUND ===", user)
    print("=== FAMILY FOUND ===", family)

    user_state = get_user_state(sender)

    # ===============================
    # זיהוי פקודות מהירות
    # ===============================
    if interactive_id:
        command = None
    elif message in UNDO_PHRASES:
        command = "undo"
    elif message in ["סיכום", "summary"]:
        command = "summary"
    elif message in ["הצג", "רשימה", "list"]:
        command = "list"
    elif message in ["אתר", "site"]:
        command = "site"
    elif message in [
        "עדכן",
        "תעדכן",
        "עדכון",
        "ערוך",
        "תערוך",
        "עריכה",
        "שנה",
        "שנה רשומה",
        "עדכן רשומה",
        "ערוך רשומה",
        "update",
        "edit",
        "modify",
    ]:
        command = "update"
    elif message in ["מחק", "מחיקה", "delete"]:
        command = "delete"
    elif message in ["עזרה", "help"]:
        command = "help"
    elif message in ["ביטול", "בטל", "cancel", "יציאה", "חזרה", "עצור", "דיי"]:
        command = "cancel"
    else:
        command = detect_command(message, strict=agent_enabled())

    print("=== DETECTED COMMAND ===", command)

    # ===============================
    # ביטול — יציאה מכל תהליך
    # ===============================
    if command == "cancel":
        if user_state:
            clear_user_state(sender)
            background_tasks.add_task(send_whatsapp_message, sender, "✅ הפעולה בוטלה.")
        elif family:
            # אין תהליך פתוח – "בטל" מבטל את הפעולה האחרונה (למשל רשומה שנוספה בטעות)
            background_tasks.add_task(send_reply, sender, undo_last_action(db, user, family))
        else:
            background_tasks.add_task(send_whatsapp_message, sender, "אין פעולה פעילה לביטול.")
        return build_empty_ok_response()

    if command == "undo" and family:
        clear_user_state(sender)
        background_tasks.add_task(send_reply, sender, undo_last_action(db, user, family))
        return build_empty_ok_response()

    # ===============================
    # אישור / דחיית בקשת הצטרפות לפי 1 / 2
    # ===============================
    if user_state and user_state.get("action") == "approve_join_request":
        if not user.is_admin or not user.family_id:
            clear_user_state(sender)
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "רק מנהל משפחה יכול לאשר או לדחות בקשות."
            )
            return build_empty_ok_response()

        join_request_id = user_state.get("join_request_id")
        join_request = get_pending_join_request_for_admin(db, join_request_id, user.id)

        if not join_request:
            clear_user_state(sender)
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא נמצאה בקשה ממתינה."
            )
            return build_empty_ok_response()

        if message == "1":
            requester = approve_join_request(db, join_request)
            clear_user_state(sender)

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "✅ הבקשה אושרה."
            )

            if requester:
                background_tasks.add_task(
                    send_whatsapp_message,
                    requester.phone,
                    "✅ הבקשה שלך אושרה! צורפת למשפחה."
                )

            return build_empty_ok_response()

        if message == "2":
            reject_join_request(db, join_request)
            clear_user_state(sender)

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "❌ הבקשה נדחתה."
            )

            requester_user = (
                db.query(User)
                .filter(User.id == join_request.requester_user_id)
                .first()
            )
            if requester_user:
                background_tasks.add_task(
                    send_whatsapp_message,
                    requester_user.phone,
                    "❌ הבקשה שלך להצטרף למשפחה נדחתה."
                )

            return build_empty_ok_response()

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "השב 1 כדי לאשר או 2 כדי לדחות."
        )
        return build_empty_ok_response()

    # ===============================
    # onboarding
    # ===============================
    if not user.family_id:
        if user_state and user_state.get("action") == "create_family_name":
            family_name = raw_message.strip()
            family = create_family_for_user(db, user, family_name)
            clear_user_state(sender)

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                f"✅ המשפחה '{family.name}' נפתחה בהצלחה.\nאתה מנהל המשפחה."
            )
            return build_empty_ok_response()

        if user_state and user_state.get("action") == "join_family_admin_phone":
            admin_phone = normalize_admin_phone_input(raw_message)
            admin_user = find_admin_by_phone(db, admin_phone)

            if not admin_user:
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "לא נמצא מנהל עם המספר הזה."
                )
                return build_empty_ok_response()

            if admin_user.phone == user.phone:
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "אי אפשר לשלוח בקשה לעצמך."
                )
                return build_empty_ok_response()

            join_request = create_join_request(db, user, admin_user)
            clear_user_state(sender)

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📨 בקשה נשלחה למנהל. מחכה לאישור."
            )

            set_user_state(
                admin_user.phone,
                {
                    "action": "approve_join_request",
                    "join_request_id": join_request.id,
                }
            )

            background_tasks.add_task(
                send_whatsapp_message,
                admin_user.phone,
                f"""👤 בקשת הצטרפות חדשה
מהמספר: {user.phone}

השב:
1 - אשר
2 - דחה"""
            )

            return build_empty_ok_response()

        if user_state and user_state.get("action") == "onboarding_choice":
            if message == "1":
                set_user_state(sender, {"action": "create_family_name"})
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "מה שם המשפחה?"
                )
                return build_empty_ok_response()

            if message == "2":
                set_user_state(sender, {"action": "join_family_admin_phone"})
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "📱 שלח מספר טלפון של מנהל (למשל: 0501234567)"
                )
                return build_empty_ok_response()

        set_user_state(sender, {"action": "onboarding_choice"})
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "ברוך הבא 👋\n1 לפתוח משפחה\n2 להצטרף"
        )
        return build_empty_ok_response()

    # היסטוריית שיחה – הסוכן משתמש בה כדי להבין הקשר ("תשנה את זה ל-25")
    log_event(db, user.id, family.id, "user", f"[לחיצה על כפתור: {interactive_title}]" if interactive_id else raw_message)

    # ===============================
    # שכבה 0 – כפתורים ואישורים (בלי LLM)
    # ===============================
    if interactive_id:
        reply = handle_interactive(db, user, family, sender, interactive_id, user_state)
        if reply:
            background_tasks.add_task(send_reply, sender, reply)
            return build_empty_ok_response()

    if user_state and user_state.get("action") == CONFIRM_ACTION:
        if message in CONFIRM_YES_WORDS or message in CONFIRM_NO_WORDS:
            reply = execute_confirmation(db, user, family, sender, user_state, confirmed=message in CONFIRM_YES_WORDS)
            background_tasks.add_task(send_reply, sender, reply)
            return build_empty_ok_response()

        # המשתמש המשיך הלאה בלי לאשר – לא מבצעים כלום
        clear_user_state(sender)
        user_state = None

    # ===============================
    # מחיקה - בחירת מספרים
    # ===============================
    if user_state and user_state.get("action") == "delete_select":
        transaction_ids = user_state.get("transaction_ids", [])

        parts = message.replace(",", " ").split()
        selected_indexes = []

        for p in parts:
            if p.isdigit():
                selected_indexes.append(int(p) - 1)

        if not selected_indexes:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "🗑️ שלח מספר רשומה או כמה מספרים למחיקה."
            )
            return build_empty_ok_response()

        deleted = []

        for index in selected_indexes:
            if 0 <= index < len(transaction_ids):
                transaction_id = transaction_ids[index]
                t = delete_transaction_by_id(db, transaction_id, family.id)

                if t:
                    amount = format_short_amount(t.amount)
                    description = t.description if t.description else "ללא תיאור"
                    deleted.append(f"{description} — {amount} ₪")

        clear_user_state(sender)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_deleted_transactions_message(deleted)
        )
        return build_empty_ok_response()

    # ===============================
    # סיכום - מחכים לחודש
    # ===============================
    if user_state and user_state.get("action") == "awaiting_summary_month":
        parsed_month = parse_month_input(message)

        if not parsed_month:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📅 לא הבנתי את החודש. שלח למשל: 3/2026 או מרץ 2026"
            )
            return build_empty_ok_response()

        month, year = parsed_month
        summary = get_month_summary(db, month, year, family.id)

        clear_user_state(sender)

        formatted_summary = format_summary_for_whatsapp_short(summary)
        magic_link = create_magic_link(
            user_id=user.id,
            family_id=family.id,
        )

        background_tasks.add_task(send_whatsapp_message, sender, formatted_summary)
        background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
        return build_empty_ok_response()

    # ===============================
    # עדכון - בחירת רשומה
    # ===============================
    if user_state and user_state.get("action") == "update_select":
        if not message.isdigit():
            background_tasks.add_task(send_whatsapp_message, sender, "✏️ שלח מספר רשומה לעדכון, או 'ביטול' לביטול.")
            return build_empty_ok_response()

        selected_index = int(message) - 1
        transaction_ids = user_state.get("transaction_ids", [])

        if selected_index < 0 or selected_index >= len(transaction_ids):
            background_tasks.add_task(send_whatsapp_message, sender, "המספר לא תקין. נסה שוב או שלח 'ביטול'.")
            return build_empty_ok_response()

        transaction_id = transaction_ids[selected_index]
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.family_id == family.id).first()

        if not transaction:
            clear_user_state(sender)
            background_tasks.add_task(send_whatsapp_message, sender, "לא נמצאה הרשומה.")
            return build_empty_ok_response()

        set_user_state(sender, {"action": "update_field_select", "transaction_id": transaction_id})
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"✏️ {transaction.description} — {format_short_amount(transaction.amount)} ₪\n\nמה לשנות?\n1. שם\n2. מחיר\n3. קטגוריה"
        )
        return build_empty_ok_response()

    # ===============================
    # עדכון - בחירת שדה
    # ===============================
    if user_state and user_state.get("action") == "update_field_select":
        transaction_id = user_state.get("transaction_id")
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.family_id == family.id).first()

        if not transaction:
            clear_user_state(sender)
            background_tasks.add_task(send_whatsapp_message, sender, "לא נמצאה הרשומה.")
            return build_empty_ok_response()

        if message in ["1", "שם", "שנה שם", "תיאור"]:
            field = "description"
            prompt = "✏️ שלח את השם החדש:"
        elif message in ["2", "מחיר", "סכום", "כמה"]:
            field = "amount"
            prompt = "💰 שלח את המחיר החדש (מספר בלבד):"
        elif message in ["3", "קטגוריה", "סוג"]:
            field = "category"
            categories_list = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(ALLOWED_CATEGORIES)])
            prompt = f"📂 בחר קטגוריה (שלח מספר):\n{categories_list}"
        else:
            background_tasks.add_task(send_whatsapp_message, sender, "שלח 1 לשם, 2 למחיר, 3 לקטגוריה — או 'ביטול'.")
            return build_empty_ok_response()

        set_user_state(sender, {"action": "update_field_value", "transaction_id": transaction_id, "field": field})
        background_tasks.add_task(send_whatsapp_message, sender, prompt)
        return build_empty_ok_response()

    # ===============================
    # עדכון - קבלת הערך החדש
    # ===============================
    if user_state and user_state.get("action") == "update_field_value":
        transaction_id = user_state.get("transaction_id")
        field = user_state.get("field")
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.family_id == family.id).first()

        if not transaction:
            clear_user_state(sender)
            background_tasks.add_task(send_whatsapp_message, sender, "לא נמצאה הרשומה.")
            return build_empty_ok_response()

        if field == "description":
            transaction.description = raw_message.strip()

        elif field == "amount":
            import re as _re
            cleaned = _re.sub(r"[^\d.]", "", raw_message)
            try:
                transaction.amount = float(cleaned)
            except Exception:
                background_tasks.add_task(send_whatsapp_message, sender, "לא הבנתי את המחיר. שלח מספר בלבד, למשל: 85")
                return build_empty_ok_response()

        elif field == "category":
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(ALLOWED_CATEGORIES):
                    transaction.category = ALLOWED_CATEGORIES[idx]
                else:
                    background_tasks.add_task(send_whatsapp_message, sender, f"מספר לא תקין. שלח מספר בין 1 ל-{len(ALLOWED_CATEGORIES)}.")
                    return build_empty_ok_response()
            else:
                matched = next((cat for cat in ALLOWED_CATEGORIES if raw_message.strip() in cat or cat in raw_message.strip()), None)
                if matched:
                    transaction.category = matched
                else:
                    categories_list = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(ALLOWED_CATEGORIES)])
                    background_tasks.add_task(send_whatsapp_message, sender, f"לא זיהיתי קטגוריה. שלח מספר:\n{categories_list}")
                    return build_empty_ok_response()

            transaction.type = "income" if transaction.category in INCOME_CATEGORIES else "expense"

        db.commit()
        remember_transaction_choice(
            db=db,
            user_id=user.id,
            family_id=family.id,
            original_text=transaction.original_text,
            description=transaction.description,
            category=transaction.category,
            tx_type=transaction.type,
        )
        clear_user_state(sender)
        background_tasks.add_task(send_whatsapp_message, sender, format_updated_transaction_message(transaction))
        return build_empty_ok_response()

    # ===============================
    # הוראת קבע - תפריט (הוספה / מחיקה)
    # ===============================
    if user_state and user_state.get("action") == "recurring_menu":
        if message in ["הוסף", "הוספה", "חדש", "add", "+"]:
            set_user_state(sender, {"action": "recurring_add_description"})
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "🔁 מה השם של התשלום הקבוע? (למשל: שכירות, ביטוח, ארנונה)"
            )
            return build_empty_ok_response()

        recurring_ids = user_state.get("recurring_ids", [])
        parts = message.replace(",", " ").split()
        selected_indexes = [int(p) - 1 for p in parts if p.isdigit()]

        if not selected_indexes:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "🔁 שלח מספר הוראת קבע למחיקה, או 'הוסף' להוספת הוראה חדשה."
            )
            return build_empty_ok_response()

        deleted = []
        for index in selected_indexes:
            if 0 <= index < len(recurring_ids):
                r = deactivate_recurring(db, recurring_ids[index], family.id)
                if r:
                    amount = format_short_amount(r.amount)
                    deleted.append(f"{r.description} — {amount} ₪")

        clear_user_state(sender)
        background_tasks.add_task(send_whatsapp_message, sender, format_deleted_recurring_message(deleted))
        return build_empty_ok_response()

    # ===============================
    # הוראת קבע - הוספה: שם
    # ===============================
    if user_state and user_state.get("action") == "recurring_add_description":
        description = raw_message.strip()

        if not description:
            background_tasks.add_task(send_whatsapp_message, sender, "🔁 שלח שם לתשלום הקבוע.")
            return build_empty_ok_response()

        set_user_state(sender, {"action": "recurring_add_amount", "description": description})
        background_tasks.add_task(send_whatsapp_message, sender, "💰 כמה זה עולה כל חודש? (מספר בלבד)")
        return build_empty_ok_response()

    # ===============================
    # הוראת קבע - הוספה: סכום
    # ===============================
    if user_state and user_state.get("action") == "recurring_add_amount":
        import re as _re
        cleaned = _re.sub(r"[^\d.]", "", raw_message)

        try:
            amount = float(cleaned)
            if amount <= 0:
                raise ValueError
        except Exception:
            background_tasks.add_task(send_whatsapp_message, sender, "לא הבנתי את הסכום. שלח מספר בלבד, למשל: 3500")
            return build_empty_ok_response()

        state_data = dict(user_state)
        state_data["action"] = "recurring_add_category"
        state_data["amount"] = amount
        set_user_state(sender, state_data)

        categories_list = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(ALLOWED_CATEGORIES)])
        background_tasks.add_task(send_whatsapp_message, sender, f"📂 בחר קטגוריה (שלח מספר):\n{categories_list}")
        return build_empty_ok_response()

    # ===============================
    # הוראת קבע - הוספה: קטגוריה
    # ===============================
    if user_state and user_state.get("action") == "recurring_add_category":
        category = None

        if message.isdigit():
            idx = int(message) - 1
            if 0 <= idx < len(ALLOWED_CATEGORIES):
                category = ALLOWED_CATEGORIES[idx]
        else:
            category = next((cat for cat in ALLOWED_CATEGORIES if raw_message.strip() in cat or cat in raw_message.strip()), None)

        if not category:
            categories_list = "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(ALLOWED_CATEGORIES)])
            background_tasks.add_task(send_whatsapp_message, sender, f"לא זיהיתי קטגוריה. שלח מספר:\n{categories_list}")
            return build_empty_ok_response()

        state_data = dict(user_state)
        state_data["action"] = "recurring_add_day"
        state_data["category"] = category
        set_user_state(sender, state_data)

        background_tasks.add_task(send_whatsapp_message, sender, "📅 באיזה יום בחודש לחייב? (מספר בין 1 ל-28)")
        return build_empty_ok_response()

    # ===============================
    # הוראת קבע - הוספה: יום בחודש + יצירה
    # ===============================
    if user_state and user_state.get("action") == "recurring_add_day":
        if not message.isdigit() or not (1 <= int(message) <= 28):
            background_tasks.add_task(send_whatsapp_message, sender, "שלח מספר יום בין 1 ל-28.")
            return build_empty_ok_response()

        day_of_month = int(message)
        description = user_state.get("description")
        amount = user_state.get("amount")
        category = user_state.get("category")
        tx_type = "income" if category in INCOME_CATEGORIES else "expense"

        recurring = create_recurring(
            db,
            family_id=family.id,
            user_id=user.id,
            description=description,
            amount=amount,
            tx_type=tx_type,
            category=category,
            day_of_month=day_of_month,
        )

        materialized = materialize_recurring_if_due(db, recurring)

        clear_user_state(sender)
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_added_recurring_message(recurring, materialized_now=materialized is not None)
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת מחיקה
    # ===============================
    if command == "delete":
        transactions = get_current_month_transactions(db, family.id)

        if not transactions:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📭 אין רשומות בחודש הנוכחי."
            )
            return build_empty_ok_response()

        transaction_ids = [t.id for t in transactions]

        set_user_state(
            sender,
            {
                "action": "delete_select",
                "transaction_ids": transaction_ids,
            }
        )

        formatted = format_transactions_for_whatsapp_short(
            transactions,
            include_delete_hint=True
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            formatted
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת עדכון
    # ===============================
    if command == "update":
        transactions = get_current_month_transactions(db, family.id)
        if not transactions:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📭 אין רשומות לעדכון."
            )
            return build_empty_ok_response()

        transaction_ids = [t.id for t in transactions]

        set_user_state(
            sender,
            {
                "action": "update_select",
                "transaction_ids": transaction_ids,
            }
        )

        formatted = format_transactions_for_whatsapp_short(transactions)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"{formatted}\n\n✏️ שלח את מספר הרשומה לעדכון"
        )
        return build_empty_ok_response()

    # ===============================
    # רשימת רשומות חודש נוכחי
    # ===============================
    if command == "list":
        transactions = get_current_month_transactions(db, family.id)
        formatted = format_transactions_for_whatsapp_short(transactions)

        magic_link = create_magic_link(
            user_id=user.id,
            family_id=family.id,
        )

        background_tasks.add_task(send_whatsapp_message, sender, formatted)
        background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
        return build_empty_ok_response()

    # ===============================
    # פקודת סיכום
    # ===============================
    if command == "summary":
        from datetime import datetime as _dt
        parsed_month = parse_month_input(raw_message)
        if parsed_month:
            month, year = parsed_month
        else:
            now = _dt.utcnow()
            month, year = now.month, now.year

        summary = get_month_summary(db, month, year, family.id)
        formatted_summary = format_summary_for_whatsapp_short(summary)
        magic_link = create_magic_link(user_id=user.id, family_id=family.id)

        background_tasks.add_task(send_whatsapp_message, sender, f"{formatted_summary}\n\n💡 לחודש אחר שלח: סיכום ספטמבר / סיכום שעבר")
        background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
        return build_empty_ok_response()

    # ===============================
    # פקודת אתר
    # ===============================
    if command == "site":
        magic_link = create_magic_link(
            user_id=user.id,
            family_id=family.id,
        )

        background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
        return build_empty_ok_response()

    # ===============================
    # פקודת עזרה
    # ===============================
    if command == "help":
        guide_link = create_magic_link(
            user_id=user.id,
            family_id=family.id,
            redirect_to="/guide",
        )
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_help_message()
        )
        background_tasks.add_task(
            send_whatsapp_cta_button,
            sender,
            "פתח את מדריך ההתחלה 👇",
            guide_link,
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת הוראת קבע
    # ===============================
    if command == "recurring":
        recurring_list = get_active_recurring(db, family.id)

        if recurring_list:
            recurring_ids = [r.id for r in recurring_list]
            set_user_state(sender, {"action": "recurring_menu", "recurring_ids": recurring_ids})
            formatted = format_recurring_for_whatsapp(recurring_list)
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                f"{formatted}\n\n➕ שלח 'הוסף' להוספת הוראת קבע חדשה\n🗑️ שלח מספר למחיקה"
            )
        else:
            set_user_state(sender, {"action": "recurring_add_description"})
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📭 אין לך עדיין הוראות קבע.\n\n🔁 מה השם של התשלום הקבוע? (למשל: שכירות, ביטוח, ארנונה)"
            )

        return build_empty_ok_response()

    # ===============================
    # שכבה 1 – מסלול מהיר: רשומות בפורמט מוכר ("ארומה 20", "סופר 340, דלק 250 אתמול")
    # ===============================
    entries = parse_entries(raw_message)
    if entries:
        background_tasks.add_task(send_reply, sender, fast_add(db, user, family, entries))
        return build_empty_ok_response()

    # ===============================
    # שכבה 2 – הסוכן: שאלות, בקשות מורכבות וניסוח חופשי
    # רץ ברקע כדי להחזיר 200 ל-Meta מיד
    # ===============================
    if agent_enabled():
        print("=== ROUTING TO AGENT ===")
        background_tasks.add_task(run_agent_and_reply, user.id, family.id, sender, raw_message)
        return build_empty_ok_response()

    # ===============================
    # הסוכן כבוי (AGENT_ENABLED=false) – ההתנהגות הקודמת
    # ===============================

    # ===============================
    # הוספת רשומה - memory -> rule-based -> AI
    # ===============================
    merchant_key = extract_merchant_key(raw_message)
    base_result = categorize_by_keywords(raw_message)
    print("=== RULE BASED RESULT ===", base_result)

    # אם אין סכום בכלל - נבדוק אם זו פקודה או רשומה חסרה
    if base_result["amount"] <= 0:
        intent = classify_message_intent(raw_message)
        print("=== MESSAGE INTENT ===", intent)

        if intent == "summary":
            from datetime import datetime as _dt
            now = _dt.utcnow()
            summary = get_month_summary(db, now.month, now.year, family.id)
            formatted_summary = format_summary_for_whatsapp_short(summary)
            magic_link = create_magic_link(user_id=user.id, family_id=family.id)

            background_tasks.add_task(send_whatsapp_message, sender, f"{formatted_summary}\n\n💡 לחודש אחר שלח: סיכום ספטמבר / סיכום שעבר")
            background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
            return build_empty_ok_response()

        if intent == "list":
            transactions = get_current_month_transactions(db, family.id)
            formatted = format_transactions_for_whatsapp_short(transactions)

            magic_link = create_magic_link(
                user_id=user.id,
                family_id=family.id,
            )

            background_tasks.add_task(send_whatsapp_message, sender, formatted)
            background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
            return build_empty_ok_response()

        if intent == "site":
            magic_link = create_magic_link(
                user_id=user.id,
                family_id=family.id,
            )

            background_tasks.add_task(send_whatsapp_cta_button, sender, "לחץ להיכנס לאתר 👇", magic_link)
            return build_empty_ok_response()

        if intent == "help":
            guide_link = create_magic_link(
                user_id=user.id,
                family_id=family.id,
                redirect_to="/guide",
            )
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                format_help_message()
            )
            background_tasks.add_task(
                send_whatsapp_cta_button,
                sender,
                "פתח את מדריך ההתחלה 👇",
                guide_link,
            )
            return build_empty_ok_response()

        if intent == "delete":
            transactions = get_current_month_transactions(db, family.id)

            if not transactions:
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "📭 אין רשומות בחודש הנוכחי."
                )
                return build_empty_ok_response()

            transaction_ids = [t.id for t in transactions]

            set_user_state(
                sender,
                {
                    "action": "delete_select",
                    "transaction_ids": transaction_ids,
                }
            )

            formatted = format_transactions_for_whatsapp_short(
                transactions,
                include_delete_hint=True
            )

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                formatted
            )
            return build_empty_ok_response()

        if intent == "update":
            transactions = get_current_month_transactions(db, family.id)
            if not transactions:
                background_tasks.add_task(
                    send_whatsapp_message,
                    sender,
                    "📭 אין רשומות לעדכון."
                )
                return build_empty_ok_response()

            transaction_ids = [t.id for t in transactions]

            set_user_state(
                sender,
                {
                    "action": "update_select",
                    "transaction_ids": transaction_ids,
                }
            )

            formatted = format_transactions_for_whatsapp_short(transactions)

            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                f"{formatted}\n\n✏️ שלח את מספר הרשומה לעדכון"
            )
            return build_empty_ok_response()

        if intent == "add_transaction_incomplete":
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "הכנס רשומה מחדש כולל מחיר."
            )
            return build_empty_ok_response()

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "🤔 לא הבנתי. שלח 'עזרה' לפקודות."
        )
        return build_empty_ok_response()

    # קודם כל בודקים זיכרון
    memory_candidates = {"user": [], "family": [], "global": []}
    if merchant_key:
        memory_candidates = find_memory_candidates(db, user.id, family.id, merchant_key)

    parsed_result = {
        **base_result
    }

    if memory_candidates["user"]:
        best = memory_candidates["user"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING USER MEMORY ===", best.category, best.tx_type)

    elif memory_candidates["family"]:
        best = memory_candidates["family"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING FAMILY MEMORY ===", best.category, best.tx_type)

    elif memory_candidates["global"]:
        best = memory_candidates["global"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING GLOBAL MEMORY ===", best.category, best.tx_type)

    # אם אין memory אבל rule-based זיהה קטגוריה - מספיק
    elif parsed_result["category"] != "אחר":
        print("=== USING RULE BASED CATEGORY ===", parsed_result["category"])

    # אם עדיין יצא 'אחר' - רק אז נשלח ל-AI
    else:
        ai_result = categorize_transaction_text(raw_message)
        print("=== AI CATEGORY RESULT ===", ai_result)

        if ai_result["amount"] > 0:
            parsed_result["category"] = ai_result["category"]
            parsed_result["type"] = ai_result["type"]

    transaction = Transaction(
        original_text=parsed_result["original_text"],
        description=parsed_result["description"],
        amount=parsed_result["amount"],
        type=parsed_result["type"],
        category=parsed_result["category"],
        family_id=family.id,
        user_id=user.id,
        user_phone=user.phone,
    )

    db.add(transaction)
    db.commit()

    # auto-learning: כל רשומה שנשמרה מחזקת את הזיכרון
    if merchant_key:
        upsert_memory(
            db,
            scope_type="user",
            scope_id=user.id,
            merchant_key=merchant_key,
            category=parsed_result["category"],
            tx_type=parsed_result["type"],
        )
        upsert_memory(
            db,
            scope_type="family",
            scope_id=family.id,
            merchant_key=merchant_key,
            category=parsed_result["category"],
            tx_type=parsed_result["type"],
        )
        upsert_memory(
            db,
            scope_type="global",
            scope_id=None,
            merchant_key=merchant_key,
            category=parsed_result["category"],
            tx_type=parsed_result["type"],
        )

    background_tasks.add_task(
        send_whatsapp_message,
        sender,
        format_added_transaction_message(parsed_result)
    )
    return build_empty_ok_response()
