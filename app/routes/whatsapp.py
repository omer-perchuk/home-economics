import os
import httpx

from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Transaction, User

from app.services.merchant_memory_service import (
    extract_merchant_key,
    upsert_memory,
    find_memory_candidates,
)
from app.services.intent_service import detect_intent_ai
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
from app.services.whatsapp_format_service import (
    format_summary_for_whatsapp_short,
    format_transactions_for_whatsapp_short,
    format_updated_transaction_message,
    format_added_transaction_message,
    format_deleted_transactions_message,
    format_help_message,
    format_short_amount,
)

print("=== WHATSAPP ROUTE LOADED ===")

router = APIRouter()

DASHBOARD_URL = "https://aws-migration-test.d11fqx2zyfwk68.amplifyapp.com"

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")


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


async def send_whatsapp_message(to_number: str, message: str) -> None:
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("Meta credentials are missing. Message was not sent.")
        return

    digits = "".join(ch for ch in to_number if ch.isdigit())
    if not digits:
        print(f"Invalid destination number: {to_number}")
        return

    url = f"https://graph.facebook.com/v22.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": digits,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)
            print("=== META SEND STATUS ===", response.status_code)
            print("=== META SEND BODY ===", response.text)
            response.raise_for_status()
        print(f"Sent WhatsApp reply to {digits}: {message}")
    except Exception as e:
        print(f"Failed to send WhatsApp reply to {digits}: {e}")


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

        if message_data.get("type") != "text":
            print("=== NON-TEXT MESSAGE IGNORED ===", message_data.get("type"))
            return build_empty_ok_response()

        raw_message = message_data["text"]["body"].strip()
        message = raw_message.lower().strip()

        sender_raw = message_data.get("from", "")
        sender = normalize_phone_for_db(sender_raw)

        print("=== RAW MESSAGE ===", raw_message)
        print("=== SENDER RAW ===", sender_raw)
        print("=== SENDER NORMALIZED ===", sender)

    except Exception as e:
        print(f"Failed to parse Meta webhook: {e}")
        return build_empty_ok_response()

    user = get_or_create_user_by_phone(db, sender)
    family = None

    if user.family_id:
        user, family = get_user_and_family_by_phone(db, sender)

    print("=== USER FOUND ===", user)
    print("=== FAMILY FOUND ===", family)

    user_state = get_user_state(sender)

    if message in ["סיכום", "summary"]:
        command = "summary"
    elif message in ["הצג", "רשימה", "list"]:
        command = "list"
    elif message in ["אתר", "site"]:
        command = "site"
    elif message in ["עדכן", "עדכון", "update"]:
        command = "update"
    elif message in ["מחק", "מחיקה", "delete"]:
        command = "delete"
    elif message in ["עזרה", "help"]:
        command = "help"
    else:
        command = detect_command(message)
    if not command or command == "unknown":
        command = detect_intent_ai(raw_message)

    print("=== DETECTED COMMAND ===", command)

    # ===============================
    # אישור / דחייה על ידי מנהל
    # ===============================
    if message.startswith("אשר "):
        if not user.is_admin or not user.family_id:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "רק מנהל משפחה יכול לאשר בקשות."
            )
            return build_empty_ok_response()

        request_id_text = message.replace("אשר", "", 1).strip()
        if not request_id_text.isdigit():
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "שלח: אשר <מספר בקשה>"
            )
            return build_empty_ok_response()

        join_request = get_pending_join_request_for_admin(
            db, int(request_id_text), user.id
        )
        if not join_request:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא נמצאה בקשה ממתינה."
            )
            return build_empty_ok_response()

        requester = approve_join_request(db, join_request)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"✅ הבקשה {join_request.id} אושרה."
        )

        if requester:
            background_tasks.add_task(
                send_whatsapp_message,
                requester.phone,
                "✅ הבקשה שלך אושרה! צורפת למשפחה."
            )

        return build_empty_ok_response()

    if message.startswith("דחה "):
        if not user.is_admin or not user.family_id:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "רק מנהל משפחה יכול לדחות בקשות."
            )
            return build_empty_ok_response()

        request_id_text = message.replace("דחה", "", 1).strip()
        if not request_id_text.isdigit():
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "שלח: דחה <מספר בקשה>"
            )
            return build_empty_ok_response()

        join_request = get_pending_join_request_for_admin(
            db, int(request_id_text), user.id
        )
        if not join_request:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא נמצאה בקשה ממתינה."
            )
            return build_empty_ok_response()

        reject_join_request(db, join_request)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"❌ הבקשה {join_request.id} נדחתה."
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

            background_tasks.add_task(
                send_whatsapp_message,
                admin_user.phone,
                f"👤 בקשה חדשה\n{user.phone}\nאשר {join_request.id} / דחה {join_request.id}"
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
                t = delete_transaction_by_id(db, transaction_id)

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

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""{formatted_summary}

🔐 כניסה מאובטחת לאתר:
{magic_link}"""
        )
        return build_empty_ok_response()

    # ===============================
    # עדכון - בחירת רשומה
    # ===============================
    if user_state and user_state.get("action") == "update_select":
        if not message.isdigit():
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "✏️ שלח מספר רשומה לעדכון."
            )
            return build_empty_ok_response()

        selected_index = int(message) - 1
        transaction_ids = user_state.get("transaction_ids", [])

        if selected_index < 0 or selected_index >= len(transaction_ids):
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "המספר לא תקין."
            )
            return build_empty_ok_response()

        transaction_id = transaction_ids[selected_index]

        set_user_state(
            sender,
            {
                "action": "update_new_value",
                "transaction_id": transaction_id,
            }
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "✏️ שלח ערך חדש.\nלדוגמה: ארומה 42"
        )
        return build_empty_ok_response()

    # ===============================
    # עדכון - קבלת ערך חדש
    # ===============================
    if user_state and user_state.get("action") == "update_new_value":
        transaction_id = user_state.get("transaction_id")

        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id)
            .first()
        )

        if not transaction:
            clear_user_state(sender)
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא נמצאה רשומה לעדכון."
            )
            return build_empty_ok_response()

        ai_result = categorize_transaction_text(raw_message)

        if ai_result["amount"] <= 0:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא הצלחתי להבין. שלח למשל: שופרסל 280"
            )
            return build_empty_ok_response()

        transaction.original_text = ai_result["original_text"]
        transaction.description = ai_result["description"]
        transaction.amount = ai_result["amount"]
        transaction.type = ai_result["type"]
        transaction.category = ai_result["category"]

        db.commit()

        merchant_key = extract_merchant_key(raw_message)

        if merchant_key:
            upsert_memory(
                db,
                scope_type="user",
                scope_id=user.id,
                merchant_key=merchant_key,
                category=transaction.category,
                tx_type=transaction.type,
            )

            upsert_memory(
                db,
                scope_type="family",
                scope_id=family.id,
                merchant_key=merchant_key,
                category=transaction.category,
                tx_type=transaction.type,
            )

            upsert_memory(
                db,
                scope_type="global",
                scope_id=None,
                merchant_key=merchant_key,
                category=transaction.category,
                tx_type=transaction.type,
            )

        clear_user_state(sender)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_updated_transaction_message(transaction)
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

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""{formatted}

🔐 כניסה מאובטחת לאתר:
{magic_link}"""
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת סיכום
    # ===============================
    if command == "summary":
        set_user_state(
            sender,
            {"action": "awaiting_summary_month"}
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "📅 איזה חודש?\nלמשל: 3/2026 או מרץ 2026"
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת אתר
    # ===============================
    if command == "site":
        magic_link = create_magic_link(
            user_id=user.id,
            family_id=family.id,
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""🔐 כניסה מאובטחת לאתר:
{magic_link}"""
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת עזרה
    # ===============================
    if command == "help":
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_help_message()
        )
        return build_empty_ok_response()

    if user_state and user_state.get("action") == "choose_category":
        ai_result = user_state.get("pending_ai_result")

        if message.isdigit():
            index = int(message) - 1
            suggestions = ai_result.get("suggestions", [])

            if 0 <= index < len(suggestions):
                ai_result["category"] = suggestions[index]
        else:
            ai_result["category"] = raw_message.strip()

        clear_user_state(sender)

        transaction = Transaction(
            original_text=ai_result["original_text"],
            description=ai_result["description"],
            amount=ai_result["amount"],
            type=ai_result["type"],
            category=ai_result["category"],
            family_id=family.id,
            user_id=user.id,
            user_phone=user.phone,
        )

        db.add(transaction)
        db.commit()

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_added_transaction_message(ai_result)
        )

        return build_empty_ok_response()

    # ===============================
    # הוספת רשומה (AI + memory)
    # ===============================
    merchant_key = extract_merchant_key(raw_message)

    memory_candidates = {"user": [], "family": [], "global": []}
    if merchant_key:
        memory_candidates = find_memory_candidates(db, user.id, family.id, merchant_key)

    # קוראים ל-AI פעם אחת
    ai_base = categorize_transaction_text(raw_message)

    # אם יש זיכרון → משתמשים בו
    if memory_candidates["user"]:
        best = memory_candidates["user"][0]
        ai_result = {
            **ai_base,
            "category": best.category,
            "type": best.tx_type,
        }

    elif memory_candidates["family"]:
        best = memory_candidates["family"][0]
        ai_result = {
            **ai_base,
            "category": best.category,
            "type": best.tx_type,
        }

    elif memory_candidates["global"]:
        best = memory_candidates["global"][0]
        ai_result = {
            **ai_base,
            "category": best.category,
            "type": best.tx_type,
        }

    else:
        ai_result = ai_base

    has_memory = (
            memory_candidates["user"]
            or memory_candidates["family"]
    )

    needs_clarification = (
            not has_memory and (
            ai_result.get("confidence", 1) < 0.6
            or ai_result["category"] == "אחר"
    )
    )
    if needs_clarification:
        suggestions = []

        for m in memory_candidates["user"][:2]:
            if m.category not in suggestions:
                suggestions.append(m.category)

        for s in ai_result.get("suggestions", []):
            if s not in suggestions:
                suggestions.append(s)

        suggestions = suggestions[:3]

        if not suggestions:
            suggestions = ["אוכל בחוץ וקפה", "סופר וקניות לבית", "אחר"]

        set_user_state(sender, {
            "action": "choose_category",
            "pending_ai_result": ai_result,
        })

        options_text = "\n".join(
            [f"{i + 1}. {cat}" for i, cat in enumerate(suggestions)]
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""לא בטוח 🤔
    בחר קטגוריה:
    {options_text}

    או כתוב בעצמך"""
        )

        return build_empty_ok_response()

    if ai_result["amount"] > 0:

        transaction = Transaction(
            original_text=ai_result["original_text"],
            description=ai_result["description"],
            amount=ai_result["amount"],
            type=ai_result["type"],
            category=ai_result["category"],
            family_id=family.id,
            user_id=user.id,
            user_phone=user.phone,
        )

        db.add(transaction)
        db.commit()

        if merchant_key:
            upsert_memory(
                db,
                scope_type="user",
                scope_id=user.id,
                merchant_key=merchant_key,
                category=ai_result["category"],
                tx_type=ai_result["type"],
            )

            upsert_memory(
                db,
                scope_type="family",
                scope_id=family.id,
                merchant_key=merchant_key,
                category=ai_result["category"],
                tx_type=ai_result["type"],
            )

            upsert_memory(
                db,
                scope_type="global",
                scope_id=None,
                merchant_key=merchant_key,
                category=ai_result["category"],
                tx_type=ai_result["type"],
            )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_added_transaction_message(ai_result)
        )
        return build_empty_ok_response()

    # ===============================
    # fallback
    # ===============================
    background_tasks.add_task(
        send_whatsapp_message,
        sender,
        "🤔 לא הבנתי. שלח 'עזרה' לפקודות."
    )
    return build_empty_ok_response()