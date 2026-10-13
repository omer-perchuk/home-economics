import os
from typing import List, Tuple

import httpx

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")

# מגבלות של WhatsApp Cloud API להודעות אינטראקטיביות
MAX_BUTTONS = 3
MAX_BUTTON_TITLE = 20
MAX_LIST_ROWS = 10
MAX_ROW_TITLE = 24
MAX_ROW_DESCRIPTION = 72


def _digits(to_number: str) -> str:
    return "".join(ch for ch in to_number if ch.isdigit())


async def _post(to_number: str, payload: dict, label: str) -> None:
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print(f"Meta credentials are missing. {label} was not sent.")
        return

    digits = _digits(to_number)
    if not digits:
        print(f"Invalid destination number: {to_number}")
        return

    url = f"https://graph.facebook.com/v22.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {"messaging_product": "whatsapp", "to": digits, **payload}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=body)
            print(f"=== META {label.upper()} STATUS ===", response.status_code)
            if response.status_code >= 400:
                print(f"=== META {label.upper()} BODY ===", response.text)
            response.raise_for_status()
        print(f"Sent {label} to {digits}")
    except Exception as e:
        print(f"Failed to send {label} to {digits}: {e}")


async def send_whatsapp_message(to_number: str, message: str) -> None:
    await _post(to_number, {"type": "text", "text": {"body": message}}, "message")


async def send_whatsapp_cta_button(to_number: str, body_text: str, url: str) -> None:
    payload = {
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "Home Economics",
                    "url": url,
                },
            },
        },
    }
    await _post(to_number, payload, "cta button")


async def send_whatsapp_buttons(to_number: str, body_text: str, buttons: List[Tuple[str, str]]) -> None:
    """
    buttons: רשימת (id, title). עד 3 כפתורים, כותרת עד 20 תווים.
    הלחיצה חוזרת ל-webhook כהודעת interactive עם ה-id.
    """
    payload = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": button_id, "title": title[:MAX_BUTTON_TITLE]}}
                    for button_id, title in buttons[:MAX_BUTTONS]
                ]
            },
        },
    }
    await _post(to_number, payload, "buttons")


async def send_whatsapp_list(
    to_number: str,
    body_text: str,
    button_text: str,
    rows: List[Tuple[str, str, str]],
) -> None:
    """
    rows: רשימת (id, title, description). עד 10 שורות.
    """
    payload = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text[:MAX_BUTTON_TITLE],
                "sections": [
                    {
                        "title": "בחירה",
                        "rows": [
                            {
                                "id": row_id,
                                "title": title[:MAX_ROW_TITLE],
                                **({"description": description[:MAX_ROW_DESCRIPTION]} if description else {}),
                            }
                            for row_id, title, description in rows[:MAX_LIST_ROWS]
                        ],
                    }
                ],
            },
        },
    }
    await _post(to_number, payload, "list")
