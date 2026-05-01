import json

from config import (
    OUTPUT_FILE,
    DOWNLOADED_FILE,
    SKIPPED_FILE,
    PENDING_FILE,
    VISITED_FILE,
)


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tmp_path.replace(path)


def save_state(downloaded_pages, skipped_pages, pending_categories, visited_categories):
    save_json(DOWNLOADED_FILE, sorted(downloaded_pages))
    save_json(SKIPPED_FILE, sorted(skipped_pages))
    save_json(PENDING_FILE, list(pending_categories))
    save_json(VISITED_FILE, sorted(visited_categories))


def get_saved_titles_from_jsonl():
    titles = set()

    if not OUTPUT_FILE.exists():
        return titles

    with OUTPUT_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                title = record.get("title")

                if title:
                    titles.add(title)

            except json.JSONDecodeError:
                continue

    return titles


def save_page(title, category, text):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "title": title,
        "source_category": category,
        "content": text,
    }

    with OUTPUT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")