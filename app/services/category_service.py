import json
from pathlib import Path


def load_categories() -> dict:
    project_root = Path(__file__).resolve().parents[2]
    categories_file = project_root / "data" / "categories.json"

    with open(categories_file, "r", encoding="utf-8") as file:
        return json.load(file)


def detect_category(description: str) -> str:
    if not description:
        return "אחר"

    categories = load_categories()
    description_lower = description.lower()

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in description_lower:
                return category

    return "אחר"