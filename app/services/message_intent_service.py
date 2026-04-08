import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


def classify_message_intent(user_text: str) -> str:
    if client is None:
        return "unknown"

    prompt = f"""
סווג את ההודעה של המשתמש לאחת מהאפשרויות:

- add_transaction_incomplete
- summary
- list
- site
- help
- delete
- update
- unknown

אם נראה שהמשתמש מנסה להזין רשומה אבל חסר מחיר, החזר:
add_transaction_incomplete

החזר רק מילה אחת.

טקסט:
{user_text}
""".strip()

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        return response.output_text.strip().lower()
    except Exception:
        return "unknown"