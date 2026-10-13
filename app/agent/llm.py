"""
שכבת ספק ה-LLM של הסוכן. כל הקריאות למודל עוברות דרך כאן,
כך שהחלפת ספק/מודל היא שינוי בקובץ אחד.
"""
import os

from openai import OpenAI

AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


def is_available() -> bool:
    return _client is not None


def agent_enabled() -> bool:
    # kill switch: AGENT_ENABLED=false מחזיר את הבוט להתנהגות הישנה בלי deploy של קוד
    return os.getenv("AGENT_ENABLED", "true").strip().lower() == "true" and is_available()


def chat(messages: list, tools: list):
    """
    מחזיר את הודעת ה-assistant (עם tool_calls אם המודל ביקש להפעיל כלים) ואת ה-usage.
    """
    response = _client.chat.completions.create(
        model=AGENT_MODEL,
        messages=messages,
        tools=tools,
        temperature=0.2,
        timeout=30,
    )
    return response.choices[0].message, response.usage
