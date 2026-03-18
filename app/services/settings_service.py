import json
import os

SETTINGS_FILE = "data/app_settings.json"
DEFAULT_TITLE = "כלכלת הבית"


def _ensure_file():
    if not os.path.exists(SETTINGS_FILE):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def _load_settings():
    _ensure_file()

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except json.JSONDecodeError:
            return {}


def _save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_settings(family_id: int):
    settings = _load_settings()
    family_key = str(family_id)

    family_settings = settings.get(family_key, {})

    return {
        "dashboard_title": family_settings.get("dashboard_title", DEFAULT_TITLE)
    }


def update_dashboard_title(family_id: int, new_title: str):
    settings = _load_settings()
    family_key = str(family_id)

    if family_key not in settings:
        settings[family_key] = {}

    settings[family_key]["dashboard_title"] = new_title.strip() or DEFAULT_TITLE

    _save_settings(settings)

    return {
        "dashboard_title": settings[family_key]["dashboard_title"]
    }