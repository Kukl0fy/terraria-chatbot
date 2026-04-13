import json
from pathlib import Path

import requests

API_URL = "https://terraria.wiki.gg/api.php"
OUTPUT_FILE = Path("categories_grouped.json")

EXCLUDED_KEYWORDS = [
    "images", "files", "translation", "templates", "archives",
    "teasers", "requests", "construction", "deletion", "redirection",
    "projects"
]

LANG_SUFFIXES = [
    "/ar", "/cs", "/da", "/el", "/es", "/fi", "/id", "/it", "/ja",
    "/lt", "/nl", "/no", "/ro", "/sk", "/th", "/tr", "/vi", "/yue"
]


def get_all_categories(limit: int = 1000) -> list[str]:
    params = {
        "action": "query",
        "list": "allcategories",
        "aclimit": limit,
        "format": "json"
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    categories = data["query"]["allcategories"]
    return [cat["*"] for cat in categories]


def is_useful_category(name: str) -> bool:
    lower_name = name.lower()

    for suffix in LANG_SUFFIXES:
        if lower_name.endswith(suffix):
            return False

    for keyword in EXCLUDED_KEYWORDS:
        if keyword in lower_name:
            return False

    return True


def classify_category(name: str) -> str:
    lower_name = name.lower()

    core_keywords = [
        "item", "items", "boss", "buff", "debuff", "crafting",
        "material", "station", "npc", "weapon", "armor", "armour",
        "ammo", "ammunition", "arrow", "arrows", "bullet", "bullets",
        "bow", "bows", "broadsword", "broadswords", "boomerang",
        "axe", "axes", "chainsaw", "crate", "loot", "bait", "coin", "coins"
    ]

    ignore_keywords = [
        "image", "images", "icon", "icons", "background", "backgrounds",
        "screenshot", "screenshots", "stub", "stubs", "template", "templates",
        "review", "redirect", "redirects", "gadget", "gadgets", "community",
        "concept art", "tracking", "dpl", "module", "modules", "cutscene",
        "cutscenes", "sprite", "sprites", "construction", "deletion"
    ]

    optional_keywords = [
        "console content", "3ds content", "crossover", "christmas",
        "ambient", "associated content", "data ids", "background object"
    ]

    ai_npc_keywords = [
        "ai npcs"
    ]

    for keyword in ignore_keywords:
        if keyword in lower_name:
            return "ignore"

    for keyword in ai_npc_keywords:
        if keyword in lower_name:
            return "optional"

    for keyword in optional_keywords:
        if keyword in lower_name:
            return "optional"

    for keyword in core_keywords:
        if keyword in lower_name:
            return "core"

    return "review"


def group_categories(categories: list[str]) -> dict[str, list[str]]:
    grouped = {
        "core": [],
        "optional": [],
        "ignore": [],
        "review": []
    }

    for category in categories:
        label = classify_category(category)
        grouped[label].append(category)

    return grouped


def save_grouped_categories(grouped: dict[str, list[str]], output_file: Path = OUTPUT_FILE) -> None:
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)


def main() -> None:
    categories = get_all_categories()
    filtered = [category for category in categories if is_useful_category(category)]
    grouped = group_categories(filtered)
    save_grouped_categories(grouped)

    print(f"Zapisano dane do: {OUTPUT_FILE.resolve()}")
    print(f"Core: {len(grouped['core'])}")
    print(f"Optional: {len(grouped['optional'])}")
    print(f"Ignore: {len(grouped['ignore'])}")
    print(f"Review: {len(grouped['review'])}")


if __name__ == "__main__":
    main()