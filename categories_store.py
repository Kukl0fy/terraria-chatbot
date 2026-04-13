import json
from pathlib import Path

DATA_FILE = Path("categories_grouped.json")


def load_grouped_categories() -> dict[str, list[str]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Brak pliku {DATA_FILE}. Najpierw uruchom build_categories.py"
        )

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_categories_by_label(label: str) -> list[str]:
    grouped = load_grouped_categories()
    return grouped.get(label, [])