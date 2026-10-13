"""
בדיקות end-to-end של ה-webhook: payload בפורמט של Meta, תשובות נאספות במקום להישלח.
הסוכן רץ מול LLM מזויף שמחזיר tool calls מתוסרטים.
"""
import itertools
import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.agent.llm as llm
import app.agent.runner as runner
import app.routes.whatsapp as whatsapp
from app.db.models import BotEvent, Transaction
from app.main import app

PHONE_DIGITS = "972500000001"
_message_ids = itertools.count(1)


@pytest.fixture
def replies(monkeypatch):
    sent = []

    async def fake_send_reply(phone, reply):
        sent.append(reply)

    monkeypatch.setattr(whatsapp, "send_reply", fake_send_reply)
    monkeypatch.setattr(runner, "send_reply_sync", lambda phone, reply: sent.append(reply))
    return sent


@pytest.fixture
def client():
    return TestClient(app)


def _post(client, message, message_id=None):
    message.setdefault("from", PHONE_DIGITS)
    message.setdefault("id", message_id or f"wamid.{next(_message_ids)}")
    body = {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}
    response = client.post("/webhook/whatsapp", json=body)
    assert response.status_code == 200
    return message["id"]


def send_text(client, text, message_id=None):
    return _post(client, {"type": "text", "text": {"body": text}}, message_id)


def press(client, button_id, title="כפתור"):
    return _post(client, {"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": button_id, "title": title}}})


def transactions(db):
    db.expire_all()
    return db.query(Transaction).order_by(Transaction.id).all()


# ===============================
# מסלול מהיר
# ===============================

def test_fast_add_single(client, replies, db, family_user):
    send_text(client, "ארומה 20")

    txs = transactions(db)
    assert [(t.description, t.amount, t.category) for t in txs] == [("ארומה", 20, "אוכל בחוץ וקפה")]
    assert "ארומה" in replies[-1].text
    button_ids = [b[0] for b in replies[-1].buttons]
    assert button_ids[0].startswith("undo:")
    assert button_ids[1] == f"cat:{txs[0].id}"


def test_fast_add_multiple_with_date(client, replies, db, family_user):
    send_text(client, "סופר 340, דלק 250 אתמול")

    txs = transactions(db)
    assert [(t.description, t.amount) for t in txs] == [("סופר", 340), ("דלק", 250)]
    assert txs[1].created_at.date() < datetime.utcnow().date() or txs[1].created_at.hour == 12
    assert "נוספו 2 רשומות" in replies[-1].text


def test_fishmonger_is_not_cancel(client, replies, db, family_user):
    send_text(client, "דייג 80")
    assert [(t.description, t.amount) for t in transactions(db)] == [("דייג", 80)]


def test_duplicate_webhook_is_ignored(client, replies, db, family_user):
    send_text(client, "ארומה 20", message_id="wamid.same")
    send_text(client, "ארומה 20", message_id="wamid.same")
    assert len(transactions(db)) == 1


def test_undo_by_text_and_button(client, replies, db, family_user):
    send_text(client, "ארומה 20")
    send_text(client, "בטל")
    assert transactions(db) == []
    assert "בוטלה" in replies[-1].text

    send_text(client, "קפה 15")
    undo_button = replies[-1].buttons[0][0]
    press(client, undo_button)
    assert transactions(db) == []

    # לחיצה שנייה על אותו כפתור – אין מה לבטל
    press(client, undo_button)
    assert "אין פעולה" in replies[-1].text


def test_change_category_via_buttons(client, replies, db, family_user):
    send_text(client, "גליץ 70")
    tx = transactions(db)[0]

    press(client, f"cat:{tx.id}")
    rows = replies[-1].list_rows
    assert rows and rows[-1][0] == f"catmore:{tx.id}"

    pick = next(r for r in rows if r[1] == "ביגוד והנעלה")
    press(client, pick[0])
    assert transactions(db)[0].category == "ביגוד והנעלה"

    # הזיכרון למד – בפעם הבאה אותו עסק מקבל את אותה קטגוריה
    send_text(client, "גליץ 40")
    assert transactions(db)[-1].category == "ביגוד והנעלה"


def test_cannot_touch_other_family_via_buttons(client, replies, db, family_user, other_family_user):
    other_family, other_user = other_family_user
    foreign = Transaction(description="סוד", amount=999, type="expense", category="אחר",
                          family_id=other_family.id, user_id=other_user.id)
    db.add(foreign)
    db.commit()

    press(client, f"setcat:{foreign.id}:0")
    db.refresh(foreign)
    assert foreign.category == "אחר"


def test_summary_button(client, replies, db, family_user):
    send_text(client, "סופר 340")
    press(client, "summary")
    assert "340" in replies[-1].text
    assert replies[-1].cta_url


# ===============================
# הסוכן (LLM מזויף)
# ===============================

def _tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)))


def _script(monkeypatch, steps):
    """
    steps: רשימה של תשובות מהמודל – או רשימת tool calls, או טקסט סופי.
    מחזיר את רשימת ה-messages שהמודל קיבל בכל סבב (לבדיקה).
    """
    seen = []
    queue = list(steps)

    def fake_chat(messages, tools):
        seen.append(list(messages))
        step = queue.pop(0)
        if isinstance(step, str):
            return SimpleNamespace(content=step, tool_calls=None), None
        return SimpleNamespace(content=None, tool_calls=step), None

    monkeypatch.setattr(llm, "chat", fake_chat)
    monkeypatch.setattr(whatsapp, "agent_enabled", lambda: True)
    return seen


def test_agent_answers_question_from_tools(client, replies, db, family_user, monkeypatch):
    send_text(client, "ארומה 20")
    send_text(client, "קפה 15")

    seen = _script(monkeypatch, [
        [_tool_call("search_transactions", {"category": "אוכל בחוץ וקפה"})],
        "הוצאתם 35 ₪ על אוכל בחוץ ☕",
    ])
    send_text(client, "כמה הוצאנו על אוכל בחוץ?")

    tool_result = json.loads(seen[1][-1]["content"])
    assert tool_result["count"] == 2 and tool_result["total_expenses"] == 35
    assert replies[-1].text == "הוצאתם 35 ₪ על אוכל בחוץ ☕"
    # ההיסטוריה כוללת את ההוספות הקודמות
    assert any("ארומה" in m["content"] for m in seen[0] if m["role"] != "system" and m.get("content"))


def test_agent_delete_requires_confirmation_and_can_be_restored(client, replies, db, family_user, monkeypatch):
    send_text(client, "ארומה 20")
    tx_id = transactions(db)[0].id

    _script(monkeypatch, [
        [_tool_call("delete_transactions", {"transaction_ids": [tx_id]})],
        "",
    ])
    send_text(client, "תמחק את הקפה של היום")

    assert len(transactions(db)) == 1, "לא מוחקים לפני אישור"
    assert [b[0] for b in replies[-1].buttons] == ["confirm:yes", "confirm:no"]

    press(client, "confirm:yes")
    assert transactions(db) == []
    restore_button = replies[-1].buttons[0][0]

    press(client, restore_button)
    assert [(t.description, t.amount) for t in transactions(db)] == [("ארומה", 20)]


def test_agent_confirmation_declined(client, replies, db, family_user, monkeypatch):
    send_text(client, "ארומה 20")
    tx_id = transactions(db)[0].id
    _script(monkeypatch, [[_tool_call("delete_transactions", {"transaction_ids": [tx_id]})], ""])
    send_text(client, "תמחק את הקפה")

    send_text(client, "לא")
    assert len(transactions(db)) == 1


def test_agent_cannot_delete_other_family(client, replies, db, family_user, other_family_user, monkeypatch):
    other_family, other_user = other_family_user
    foreign = Transaction(description="סוד", amount=999, type="expense", category="אחר",
                          family_id=other_family.id, user_id=other_user.id)
    db.add(foreign)
    db.commit()

    seen = _script(monkeypatch, [
        [_tool_call("delete_transactions", {"transaction_ids": [foreign.id]})],
        "לא מצאתי רשומה כזו",
    ])
    send_text(client, "תמחק את רשומה הסודית")

    assert "error" in json.loads(seen[1][-1]["content"])
    press(client, "confirm:yes")
    db.expire_all()
    assert db.get(Transaction, foreign.id) is not None


def test_agent_update_and_undo(client, replies, db, family_user, monkeypatch):
    send_text(client, "סופר 300")
    tx_id = transactions(db)[0].id

    _script(monkeypatch, [
        [_tool_call("update_transaction", {"transaction_id": tx_id, "amount": 320})],
        "עדכנתי ל-320 ₪",
    ])
    send_text(client, "תשנה את הסופר ל-320")
    assert transactions(db)[0].amount == 320

    press(client, replies[-1].buttons[0][0])
    assert transactions(db)[0].amount == 300


def test_agent_tool_error_is_returned_to_model(client, replies, db, family_user, monkeypatch):
    seen = _script(monkeypatch, [
        [_tool_call("add_transactions", {"items": [{"description": "קפה", "amount": 20, "category": "לא קיים"}]})],
        "סליחה",
    ])
    send_text(client, "תוסיף משהו מוזר")
    assert "error" in json.loads(seen[1][-1]["content"])
    assert transactions(db) == []


def test_agent_disabled_falls_back_to_legacy(client, replies, db, family_user, monkeypatch):
    monkeypatch.setattr(whatsapp, "agent_enabled", lambda: False)
    called = []
    monkeypatch.setattr(whatsapp, "classify_message_intent", lambda text: called.append(text) or "unknown")
    send_text(client, "מה המצב עם ההוצאות שלנו")
    assert called
