import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

ALLOWED_CATEGORIES = [
    "סופר וקניות לבית",
    "אוכל בחוץ וקפה",
    "תחבורה",
    "בריאות ופארם",
    "דיור וחשבונות",
    "בילויים ופנאי",
    "ביגוד והנעלה",
    "ילדים ומשפחה",
    "לימודים",
    "חופשות ונסיעות",
    "מתנות ותרומות",
    "ביטוחים",
    "חיות מחמד",
    "משכורת",
    "החזרים",
    "הכנסות",
    "אחר",
]


def _normalize_result(data, original_text):
    description = str(data.get("description", "")).strip() or original_text.strip()
    amount = data.get("amount", 0)
    tx_type = str(data.get("type", "expense")).strip().lower()
    category = str(data.get("category", "אחר")).strip()

    try:
        amount = float(amount)
    except Exception:
        amount = 0.0

    if tx_type not in ["expense", "income"]:
        tx_type = "expense"

    if category not in ALLOWED_CATEGORIES:
        category = "אחר"

    # 🔥 ברירת מחדל
    confidence = float(data.get("confidence", 0.7))
    suggestions = data.get("suggestions", [])

    if not isinstance(suggestions, list):
        suggestions = []

    return {
        "description": description,
        "amount": amount,
        "type": tx_type,
        "category": category,
        "original_text": original_text,
        "confidence": confidence,
        "suggestions": suggestions,
    }


def categorize_transaction_text(user_text):
    if client is None:
        return {
            "description": user_text.strip(),
            "amount": 0.0,
            "type": "expense",
            "category": "אחר",
            "original_text": user_text,
            "confidence": 0.0,
            "suggestions": [],
        }

    categories_text = ", ".join(ALLOWED_CATEGORIES)

    prompt = f"""
אתה מסווג הודעות של ניהול הוצאות והכנסות למשק בית.

החזר JSON בלבד.

מבנה חובה:
{{
  "description": "string",
  "amount": number,
  "type": "expense או income",
  "category": "אחת מהקטגוריות המותרות בלבד",
  "confidence": number בין 0 ל-1,
  "suggestions": ["קטגוריה1","קטגוריה2","קטגוריה3"]
}}

קטגוריות מותרות:
{categories_text}

חוקים:
- אם זו הוצאה → type = expense
- אם זו הכנסה → type = income
- category חייבת להיות מהרשימה בלבד
- אם לא בטוח → confidence נמוך (0.3-0.6)
- אם בטוח → confidence גבוה (0.8-1)
- suggestions = עד 3 קטגוריות אפשריות

⚡ דוגמאות:
- "ארומה 18" → אוכל בחוץ וקפה
- "שופרסל 150" → סופר וקניות לבית
- "פז 300" → תחבורה

טקסט:
{user_text}
""".strip()

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    content = response.output_text.strip()

    try:
        data = json.loads(content)
        return _normalize_result(data, user_text)
    except Exception:
        return {
            "description": user_text.strip(),
            "amount": 0.0,
            "type": "expense",
            "category": "אחר",
            "original_text": user_text,
            "confidence": 0.0,
            "suggestions": [],
        }