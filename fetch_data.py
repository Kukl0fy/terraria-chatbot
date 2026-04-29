import json
import time
from collections import deque
from pathlib import Path

import requests
from bs4 import BeautifulSoup


API_URL = "https://terraria.wiki.gg/api.php"

HEADERS = {
    "User-Agent": "TerrariaStudentProject/1.0 (contact: hkukla@student.agh.edu.pl)",
    "Accept": "application/json",
}

BASE_DIR = Path(__file__).parent

START_CATEGORY = "Terraria"

OUTPUT_FILE = BASE_DIR / "wiki_data.jsonl"
DOWNLOADED_FILE = BASE_DIR / "downloaded_pages.json"
PENDING_FILE = BASE_DIR / "pending_categories.json"
VISITED_FILE = BASE_DIR / "visited_categories.json"

REQUEST_DELAY = 3
CATEGORY_DELAY = 1


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def save_json(path, data):
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tmp_path.replace(path)


def save_state(downloaded_pages, pending_categories, visited_categories):
    save_json(DOWNLOADED_FILE, sorted(downloaded_pages))
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


def make_category_title(category_name):
    if category_name.startswith("Category:"):
        return category_name

    return f"Category:{category_name}"


def clean_category_name(category_title):
    return category_title.removeprefix("Category:")


def api_get(params, label):
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            print(f"Blad HTTP {response.status_code}: {label}")
            return None

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Blad requestu: {label} | {e}")
        return None

    except json.JSONDecodeError:
        print(f"Blad JSON: {label}")
        return None


def get_category_members(category_name):
    pages = []
    subcategories = []

    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": make_category_title(category_name),
        "cmtype": "page|subcat",
        "cmprop": "title|type",
        "cmlimit": 500,
        "format": "json",
    }

    while True:
        data = api_get(params, f"kategoria {category_name}")

        if data is None:
            return None, None

        if "error" in data:
            print(f"API error dla kategorii {category_name}: {data['error']}")
            return None, None

        members = data.get("query", {}).get("categorymembers", [])

        for item in members:
            title = item.get("title")
            item_type = item.get("type")

            if not title:
                continue

            if item_type == "page":
                pages.append(title)

            elif item_type == "subcat":
                subcategories.append(clean_category_name(title))

        if "continue" not in data:
            break

        params.update(data["continue"])
        time.sleep(CATEGORY_DELAY)

    return pages, subcategories


def get_page_text(page_title):
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "format": "json",
        "redirects": 1,
    }

    data = api_get(params, f"strona {page_title}")

    if data is None:
        return ""

    if "error" in data:
        print(f"API error dla strony {page_title}: {data['error']}")
        return ""

    html = data.get("parse", {}).get("text", {}).get("*", "")

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    for selector in [
        ".navbox",
        ".toc",
        ".noprint",
        ".mw-editsection",
        ".box-bottom",
    ]:
        for element in soup.select(selector):
            element.extract()

    text = soup.get_text(separator=" ", strip=True)
    return text


def save_page(title, category, text):
    record = {
        "title": title,
        "source_category": category,
        "content": text,
    }

    with OUTPUT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    downloaded_pages = set(load_json(DOWNLOADED_FILE, []))
    downloaded_pages.update(get_saved_titles_from_jsonl())

    visited_categories = set(load_json(VISITED_FILE, []))
    pending_from_file = load_json(PENDING_FILE, None)

    if pending_from_file is None:
        pending_categories = deque([START_CATEGORY])
    else:
        pending_categories = deque(pending_from_file)

    if not pending_categories and START_CATEGORY not in visited_categories:
        pending_categories.append(START_CATEGORY)

    page_errors = 0
    category_errors = 0
    category_errors_in_row = 0

    print("Start crawlera Terraria Wiki")
    print(f"Pobrane strony: {len(downloaded_pages)}")
    print(f"Odwiedzone kategorie: {len(visited_categories)}")
    print(f"Kategorie w kolejce: {len(pending_categories)}")
    print(f"Plik wyjsciowy: {OUTPUT_FILE.resolve()}")

    try:
        while pending_categories:
            category = pending_categories[0]

            if category in visited_categories:
                pending_categories.popleft()
                save_state(downloaded_pages, pending_categories, visited_categories)
                continue

            print("\n" + "=" * 60)
            print(f"Kategoria: {category}")
            print(f"Zostalo kategorii w kolejce: {len(pending_categories)}")
            print("=" * 60)

            pages, subcategories = get_category_members(category)

            if pages is None or subcategories is None:
                category_errors += 1
                category_errors_in_row += 1

                print(f"Nie udalo sie pobrac kategorii: {category}")
                print("Przesuwam kategorie na koniec kolejki.")

                pending_categories.popleft()
                pending_categories.append(category)

                save_state(downloaded_pages, pending_categories, visited_categories)

                if category_errors_in_row >= len(pending_categories):
                    print("\nWszystkie pozostale kategorie zwracaja blad.")
                    print("Koncze, zeby nie zrobic nieskonczonej petli.")
                    print("Przy kolejnym uruchomieniu program sprobuje je znowu pobrac.")
                    break

                time.sleep(CATEGORY_DELAY)
                continue

            category_errors_in_row = 0

            print(f"Strony: {len(pages)}")
            print(f"Podkategorie: {len(subcategories)}")

            known_categories = set(pending_categories) | visited_categories

            for subcategory in subcategories:
                if subcategory not in known_categories:
                    pending_categories.append(subcategory)
                    known_categories.add(subcategory)

            save_state(downloaded_pages, pending_categories, visited_categories)

            for index, title in enumerate(pages, start=1):
                if title in downloaded_pages:
                    print(f"Pominieto [{index}/{len(pages)}]: {title}")
                    continue

                print(f"Pobieram [{index}/{len(pages)}]: {title}")

                text = get_page_text(title)

                if not text:
                    page_errors += 1
                    print(f"Nie udalo sie pobrac strony: {title}")
                    time.sleep(REQUEST_DELAY)
                    continue

                save_page(title, category, text)
                downloaded_pages.add(title)

                save_state(downloaded_pages, pending_categories, visited_categories)

                print(f"Zapisano: {title}")
                time.sleep(REQUEST_DELAY)

            visited_categories.add(category)
            pending_categories.popleft()

            save_state(downloaded_pages, pending_categories, visited_categories)

            print(f"Zakonczono kategorie: {category}")
            time.sleep(CATEGORY_DELAY)

    except KeyboardInterrupt:
        print("\nPrzerwano program recznie.")

    finally:
        save_state(downloaded_pages, pending_categories, visited_categories)

        print("\nKoniec / zapisano stan.")
        print(f"Pobrane strony: {len(downloaded_pages)}")
        print(f"Odwiedzone kategorie: {len(visited_categories)}")
        print(f"Zostalo kategorii: {len(pending_categories)}")
        print(f"Bledy stron w tym uruchomieniu: {page_errors}")
        print(f"Bledy kategorii w tym uruchomieniu: {category_errors}")
        print(f"Dane: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()