"""
לולאת הסוכן: היסטוריה + הודעה -> המודל מפעיל כלים -> תשובה סופית.
"""
import time

from sqlalchemy.orm import Session

from app.agent import llm
from app.agent.prompt import build_system_prompt
from app.agent.tools import TOOL_DEFINITIONS, AgentContext, run_tool
from app.bot.actions import BTN_UNDO
from app.bot.replies import Reply, send_reply_sync
from app.db.database import SessionLocal
from app.db.models import Family, User
from app.services.bot_event_service import get_recent_history, log_event

MAX_ROUNDS = 6
FALLBACK_TEXT = "😕 משהו השתבש אצלי. נסה לנסח שוב, או שלח 'עזרה'."


def _history_messages(db: Session, user_id: int) -> list:
    # ההיסטוריה כוללת כבר את ההודעה הנוכחית של המשתמש (נרשמה ב-webhook)
    messages = []
    for event in get_recent_history(db, user_id):
        role = "user" if event.role == "user" else "assistant"
        messages.append({"role": role, "content": event.content})

    # המודל מצפה שהשיחה תתחיל בהודעת משתמש
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    return messages


def run_agent(db: Session, user, family, phone: str, user_text: str) -> Reply:
    ctx = AgentContext(db=db, user=user, family=family, phone=phone)

    messages = [{"role": "system", "content": build_system_prompt(user, family)}]
    history = _history_messages(db, user.id)
    if not history or history[-1]["content"] != user_text:
        history.append({"role": "user", "content": user_text})
    messages.extend(history)

    final_text = None
    started = time.time()
    total_tokens = 0

    for _ in range(MAX_ROUNDS):
        message, usage = llm.chat(messages, TOOL_DEFINITIONS)
        if usage:
            total_tokens += usage.total_tokens or 0

        if not message.tool_calls:
            final_text = (message.content or "").strip()
            break

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in message.tool_calls
            ],
        })

        for call in message.tool_calls:
            result = run_tool(ctx, call.function.name, call.function.arguments)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    print(
        f"=== AGENT DONE === tools={ctx.tool_log} tokens={total_tokens} "
        f"seconds={time.time() - started:.1f}"
    )

    # בקשת אישור (מחיקה / ביטול הוראת קבע) – הודעת הכפתורים היא התשובה
    if ctx.confirm_reply:
        reply = ctx.confirm_reply
    else:
        reply = Reply(text=final_text or FALLBACK_TEXT)
        if ctx.undo_event_id:
            reply.buttons = [(f"{BTN_UNDO}:{ctx.undo_event_id}", "↩️ בטל")]

    reply.cta_text = ctx.cta_text
    reply.cta_url = ctx.cta_url

    log_event(db, user.id, family.id, "assistant", reply.text)
    return reply


def run_agent_and_reply(user_id: int, family_id: int, phone: str, user_text: str) -> None:
    """
    רץ כ-background task (ב-thread), עם session משלו – ה-session של ה-request כבר נסגר.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        family = db.query(Family).filter(Family.id == family_id).first()
        if not user or not family:
            return

        try:
            reply = run_agent(db, user, family, phone, user_text)
        except Exception as e:
            db.rollback()
            print(f"=== AGENT ERROR === {e}")
            reply = Reply(text=FALLBACK_TEXT)

        send_reply_sync(phone, reply)
    finally:
        db.close()
