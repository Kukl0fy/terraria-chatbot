import ast
import json
import re

from terraria_bot.config import DATA_DIR
from terraria_bot.api.cargo_api import (
    get_cargo_tables,
    get_cargo_fields,
    cargo_query_table,
)


OUT_DIR = DATA_DIR / "structured"
OUT_DIR.mkdir(exist_ok=True)

TABLES = {
    "Recipes": OUT_DIR / "recipes.jsonl",
    "Items": OUT_DIR / "items.jsonl",
}


def save_json(path, data):
    path.parent.mkdir(exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_jsonl(path, rows):
    path.parent.mkdir(exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean(value):
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("¦", "")
    text = text.replace("\xa0", " ")
    text = text.strip().strip("\"'")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        result = []

        for item in value:
            result.extend(split_list(item))

        return result

    text = str(value).strip()

    if not text:
        return []

    # np. ['¦Vicious Powder¦', '¦Vertebra¦']
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, list):
                result = []

                for item in parsed:
                    result.extend(split_list(item))

                return result

        except Exception:
            pass

    # np. ¦Wood¦^¦Torch¦
    bar_items = re.findall(r"¦([^¦]+)¦", text)

    if bar_items:
        return [clean(item) for item in bar_items if clean(item)]

    if "^" in text:
        parts = text.split("^")
    else:
        parts = [text]

    return [clean(part) for part in parts if clean(part)]


def normalize_row(table_name, row):
    result = {}

    for key, value in row.items():
        result[key] = clean(value)

    if table_name == "Recipes":
        result["ingredients_list"] = split_list(row.get("ingredients"))
        result["station_list"] = split_list(row.get("station"))

        try:
            result["amount"] = int(row.get("amount") or 1)
        except ValueError:
            result["amount"] = 1

    return result


def fetch_table(table_name, output_file):
    fields = get_cargo_fields(table_name)

    if not fields:
        print(f"Brak pól dla tabeli: {table_name}")
        return []

    save_json(OUT_DIR / f"{table_name.lower()}_fields.json", fields)

    raw_rows = cargo_query_table(table_name, fields)

    rows = [
        normalize_row(table_name, row)
        for row in raw_rows
    ]

    save_jsonl(output_file, rows)

    print(f"Zapisano {len(rows)} rekordów do: {output_file}")

    return rows


def build_item_names(recipes, items):
    names = set()

    for row in recipes:
        if row.get("result"):
            names.add(row["result"])

        for ingredient in row.get("ingredients_list", []):
            names.add(ingredient)

    for row in items:
        for field in ["page", "name", "item", "itemname"]:
            if row.get(field):
                names.add(row[field])

    names = {
        name
        for name in names
        if name and len(name) <= 100
    }

    return sorted(names)


def run_structured_data_crawler():
    print("Start structured crawler")

    cargo_tables = get_cargo_tables()
    save_json(OUT_DIR / "cargo_tables.json", cargo_tables)

    downloaded = {}

    for table_name, output_file in TABLES.items():
        print("\n" + "=" * 60)
        print(f"Pobieram: {table_name}")
        print("=" * 60)

        rows = fetch_table(table_name, output_file)
        downloaded[table_name] = rows

    recipes = downloaded.get("Recipes", [])
    items = downloaded.get("Items", [])

    item_names = build_item_names(recipes, items)
    save_json(OUT_DIR / "item_names.json", item_names)

    print("\nGotowe.")
    print(f"Recipes: {len(recipes)}")
    print(f"Items: {len(items)}")
    print(f"Item names: {len(item_names)}")


if __name__ == "__main__":
    run_structured_data_crawler()