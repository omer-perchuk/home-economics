from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


def detect_intent_ai(user_text: str) -> str:
    if client is None:
        return "unknown"

    prompt = f"""
סווג את כוונת המשתמש.

אפשרויות:
- add_transaction
- summary
- list
- site
- help
- delete
- update
- unknown

החזר רק מילה אחת.

טקסט:
{user_text}
"""

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        return response.output_text.strip().lower()

    except Exception:
        return "unknown"