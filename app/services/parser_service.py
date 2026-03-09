import re

from app.services.category_service import detect_category


def extract_amount(text: str):

    numbers = re.findall(r"\d+(?:\.\d+)?", text)

    if not numbers:
        return None

    return float(numbers[0])


def clean_description(text: str, amount):

    if amount is None:
        return text.strip()

    text = text.replace(str(int(amount)), "")
    text = text.replace(str(amount), "")

    text = text.replace("ב", " ")
    text = text.replace("על", " ")
    text = text.replace("שילמתי", " ")
    text = text.replace("קניתי", " ")
    text = text.replace("שילמנו", " ")

    text = text.strip()

    return text


def detect_transaction_type(text: str):

    income_keywords = [
        "משכורת",
        "הכנסה",
        "קיבלתי",
        "נכנס",
        "בונוס",
        "הפקדה",
        "זיכוי",
        "החזר"
    ]

    for word in income_keywords:
        if word in text:
            return "income"

    return "expense"


def parse_expense_text(text: str):

    original_text = text
    text = text.lower()

    amount = extract_amount(text)

    if amount is None:
        return {
            "original_text": original_text,
            "description": text,
            "amount": None,
            "type": None,
            "category": None
        }

    description = clean_description(text, amount)

    if description == "":
        description = "ללא תיאור"

    transaction_type = detect_transaction_type(text)

    category = detect_category(description)

    return {
        "original_text": original_text,
        "description": description,
        "amount": amount,
        "type": transaction_type,
        "category": category
    }