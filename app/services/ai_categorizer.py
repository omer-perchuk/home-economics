import json
import os
import re
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


def _extract_amount_fallback(text: str) -> float:
    """
    ניסיון חילוץ סכום בסיסי מהטקסט במקרה שה-AI לא החזיר JSON תקין.
    לדוגמה:
    'ארומה 20' -> 20
    'שופרסל 150' -> 150
    """
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return 0.0
    return 0.0


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

    confidence = data.get("confidence", 0.7)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.7

    suggestions = data.get("suggestions", [])
    if not isinstance(suggestions, list):
        suggestions = []

    # מסננים רק קטגוריות חוקיות וללא כפילויות
    clean_suggestions = []
    for s in suggestions:
        s = str(s).strip()
        if s in ALLOWED_CATEGORIES and s not in clean_suggestions:
            clean_suggestions.append(s)

    return {
        "description": description,
        "amount": amount,
        "type": tx_type,
        "category": category,
        "original_text": original_text,
        "confidence": confidence,
        "suggestions": clean_suggestions,
    }


def categorize_transaction_text(user_text: str):
    """
    פונקציה שמקבלת טקסט חופשי מהמשתמש
    ומחזירה:
    - description
    - amount
    - type
    - category
    - confidence
    - suggestions
    """
    if client is None:
        return {
            "description": user_text.strip(),
            "amount": _extract_amount_fallback(user_text),
            "type": "expense",
            "category": "אחר",
            "original_text": user_text,
            "confidence": 0.0,
            "suggestions": [],
        }

    categories_text = ", ".join(ALLOWED_CATEGORIES)

    prompt = f"""
אתה מסווג הודעות של ניהול הוצאות והכנסות למשק בית.

החזר JSON בלבד, בלי markdown ובלי הסברים.

מבנה חובה:
{{
  "description": "string",
  "amount": number,
  "type": "expense או income",
  "category": "אחת מהקטגוריות המותרות בלבד",
  "confidence": number בין 0 ל-1,
  "suggestions": ["קטגוריה1", "קטגוריה2", "קטגוריה3"]
}}

קטגוריות מותרות:
{categories_text}

חוקים:
- אם זו הוצאה → type = expense
- אם זו הכנסה → type = income
- category חייבת להיות אחת מהרשימה בלבד
- amount חייב להיות מספר בלבד
- description צריך להיות קצר וברור
- suggestions צריכות להכיל עד 3 קטגוריות אפשריות
- אם יש שם עסק + מספר, המספר הוא בדרך כלל הסכום
- אם מופיע מספר בודד בטקסט, אל תחזיר amount = 0 אלא אם באמת אין דרך להבין
- גם אם אינך בטוח בקטגוריה, עדיין נסה לחלץ description ו-amount
- אם אינך בטוח בקטגוריה → category = "אחר" ו-confidence נמוך

חוקי ביטחון:
- confidence גבוה (0.8-1.0) אם אתה בטוח
- confidence בינוני (0.6-0.79) אם יש היגיון טוב אבל לא מושלם
- confidence נמוך (0.0-0.59) אם הקטגוריה לא ברורה
- אם category = "אחר", לרוב confidence צריך להיות נמוך

⚠️ חוקים חשובים לסיווג:
- בתי קפה, מסעדות, juice bar → "אוכל בחוץ וקפה"
- סופרמרקטים, מכולת → "סופר וקניות לבית"
- תחנות דלק → "תחבורה"
- פארם / בתי מרקחת → "בריאות ופארם"
- בגדים / מותגי אופנה → "ביגוד והנעלה"

⚡ דוגמאות אמיתיות:
- "ארומה 18" → אוכל בחוץ וקפה, amount 18
- "rebar 35" → אוכל בחוץ וקפה, amount 35
- "yellow 20" → תחבורה, amount 20
- "קפה לנדוור 40" → אוכל בחוץ וקפה, amount 40
- "רמי לוי 200" → סופר וקניות לבית, amount 200
- "שופרסל 150" → סופר וקניות לבית, amount 150
- "גולף קידס 120" → ביגוד והנעלה, amount 120
- "זארה 300" → ביגוד והנעלה, amount 300
- "פז 300" → תחבורה, amount 300
- "באבלטי 20" → אוכל בחוץ וקפה, amount 20
- "וולט 55" → אוכל בחוץ וקפה, amount 55
- "תן ביס 80" → אוכל בחוץ וקפה, amount 80
- "סופר פארם 90" → בריאות ופארם, amount 90
- "כללית 150" → בריאות ופארם, amount 150
- "סלקום 200" → דיור וחשבונות, amount 200
- "הוט 300" → דיור וחשבונות, amount 300
- "חניה 30" → תחבורה, amount 30
- "bolt 25" → תחבורה, amount 25
- "גט 60" → תחבורה, amount 60
- "קופיקס 8" → אוכל בחוץ וקפה, amount 8
- "מקדונלדס 45" → אוכל בחוץ וקפה, amount 45
- "h&m 200" → ביגוד והנעלה, amount 200
- "nike 350" → ביגוד והנעלה, amount 350
- "booking 1200" → חופשות ונסיעות, amount 1200
- "airbnb 800" → חופשות ונסיעות, amount 800
- "משכורת 10000" → משכורת, type income, amount 10000
- "קיבלתי 500" → הכנסות, type income, amount 500
- "החזר 200" → החזרים, type income, amount 200
- "גן 1500" → ילדים ומשפחה, amount 1500
- "חוג 300" → ילדים ומשפחה, amount 300
- "שכירות 4000" → דיור וחשבונות, amount 4000
- "ארנונה 600" → דיור וחשבונות, amount 600

טקסט המשתמש:
{user_text}
""".strip()

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        content = response.output_text.strip()
        data = json.loads(content)
        return _normalize_result(data, user_text)

    except Exception:
        return {
            "description": user_text.strip(),
            "amount": _extract_amount_fallback(user_text),
            "type": "expense",
            "category": "אחר",
            "original_text": user_text,
            "confidence": 0.0,
            "suggestions": [],
        }