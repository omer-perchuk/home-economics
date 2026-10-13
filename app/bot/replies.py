import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.services.whatsapp_client import (
    send_whatsapp_buttons,
    send_whatsapp_cta_button,
    send_whatsapp_list,
    send_whatsapp_message,
)


@dataclass
class Reply:
    """
    תשובה אחת למשתמש. הטקסט נשלח עם כפתורים / רשימה אם יש, ואחריו כפתור קישור אם יש.
    """
    text: str
    buttons: List[Tuple[str, str]] = field(default_factory=list)
    list_rows: List[Tuple[str, str, str]] = field(default_factory=list)
    list_button: str = "בחר"
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None


async def send_reply(phone: str, reply: Reply) -> None:
    if reply.list_rows:
        await send_whatsapp_list(phone, reply.text, reply.list_button, reply.list_rows)
    elif reply.buttons:
        await send_whatsapp_buttons(phone, reply.text, reply.buttons)
    elif reply.text:
        await send_whatsapp_message(phone, reply.text)

    if reply.cta_url:
        await send_whatsapp_cta_button(phone, reply.cta_text or "לחץ להיכנס לאתר 👇", reply.cta_url)


def send_reply_sync(phone: str, reply: Reply) -> None:
    # לשימוש מתוך thread רקע (כמו הסוכן), שבו אין event loop פעיל
    asyncio.run(send_reply(phone, reply))
