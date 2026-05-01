import time
from collections import deque

from config import (
    START_CATEGORY,
    OUTPUT_FILE,
    DOWNLOADED_FILE,
    SKIPPED_FILE,
    PENDING_FILE,
    VISITED_FILE,
    REQUEST_DELAY,
    CATEGORY_DELAY,
)

from filters import (
    should_skip_category,
    should_skip_page,
    is_bad_text,
)

from storage import (
    load_json,
    save_state,
    get_saved_titles_from_jsonl,
    save_page,
)

from wiki_api import get_category_members
from text_parser import get_page_text


def run_crawler():
    downloaded_pages = set(load_json(DOWNLOADED_FILE, []))
    downloaded_pages.update(get_saved_titles_from_jsonl())

    skipped_pages = set(load_json(SKIPPED_FILE, []))

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
    skipped_pages_this_run = 0
    skipped_categories_this_run = 0

    print("Start crawlera Terraria Wiki")
    print(f"Pobrane strony: {len(downloaded_pages)}")
    print(f"Pominiete strony: {len(skipped_pages)}")
    print(f"Odwiedzone kategorie: {len(visited_categories)}")
    print(f"Kategorie w kolejce: {len(pending_categories)}")
    print(f"Plik wyjsciowy: {OUTPUT_FILE.resolve()}")

    try:
        while pending_categories:
            category = pending_categories[0]

            if should_skip_category(category):
                print(f"Pominieto kategorie filtrem: {category}")
                skipped_categories_this_run += 1

                visited_categories.add(category)
                pending_categories.popleft()

                save_state(
                    downloaded_pages,
                    skipped_pages,
                    pending_categories,
                    visited_categories,
                )
                continue

            if category in visited_categories:
                pending_categories.popleft()

                save_state(
                    downloaded_pages,
                    skipped_pages,
                    pending_categories,
                    visited_categories,
                )
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

                save_state(
                    downloaded_pages,
                    skipped_pages,
                    pending_categories,
                    visited_categories,
                )

                if category_errors_in_row >= len(pending_categories):
                    print("\nWszystkie pozostale kategorie zwracaja blad.")
                    print("Koncze, zeby nie zrobic nieskonczonej petli.")
                    print("Przy kolejnym uruchomieniu program sprobuje je znowu pobrac.")
                    break

                time.sleep(CATEGORY_DELAY)
                continue

            category_errors_in_row = 0

            print(f"Strony przed filtrem: {len(pages)}")
            print(f"Podkategorie przed filtrem: {len(subcategories)}")

            known_categories = set(pending_categories) | visited_categories

            added_subcategories = 0
            skipped_subcategories = 0

            for subcategory in subcategories:
                if should_skip_category(subcategory):
                    print(f"Pominieto podkategorie filtrem: {subcategory}")
                    skipped_subcategories += 1
                    continue

                if subcategory not in known_categories:
                    pending_categories.append(subcategory)
                    known_categories.add(subcategory)
                    added_subcategories += 1

            print(f"Dodano podkategorie: {added_subcategories}")
            print(f"Pominieto podkategorie: {skipped_subcategories}")

            save_state(
                downloaded_pages,
                skipped_pages,
                pending_categories,
                visited_categories,
            )

            for index, title in enumerate(pages, start=1):
                if title in downloaded_pages:
                    print(f"Pominieto, juz pobrane [{index}/{len(pages)}]: {title}")
                    continue

                if title in skipped_pages:
                    print(f"Pominieto, juz bylo odfiltrowane [{index}/{len(pages)}]: {title}")
                    continue

                if should_skip_page(title):
                    print(f"Pominieto strone filtrem [{index}/{len(pages)}]: {title}")

                    skipped_pages.add(title)
                    skipped_pages_this_run += 1

                    save_state(
                        downloaded_pages,
                        skipped_pages,
                        pending_categories,
                        visited_categories,
                    )
                    continue

                print(f"Pobieram [{index}/{len(pages)}]: {title}")

                text = get_page_text(title)

                if is_bad_text(text):
                    page_errors += 1
                    skipped_pages.add(title)
                    skipped_pages_this_run += 1

                    print(f"Pominieto strone przez pusty/krotki/smieciowy tekst: {title}")

                    save_state(
                        downloaded_pages,
                        skipped_pages,
                        pending_categories,
                        visited_categories,
                    )

                    time.sleep(REQUEST_DELAY)
                    continue

                save_page(title, category, text)
                downloaded_pages.add(title)

                save_state(
                    downloaded_pages,
                    skipped_pages,
                    pending_categories,
                    visited_categories,
                )

                print(f"Zapisano: {title}")
                time.sleep(REQUEST_DELAY)

            visited_categories.add(category)
            pending_categories.popleft()

            save_state(
                downloaded_pages,
                skipped_pages,
                pending_categories,
                visited_categories,
            )

            print(f"Zakonczono kategorie: {category}")
            time.sleep(CATEGORY_DELAY)

    except KeyboardInterrupt:
        print("\nPrzerwano program recznie.")

    finally:
        save_state(
            downloaded_pages,
            skipped_pages,
            pending_categories,
            visited_categories,
        )

        print("\nKoniec / zapisano stan.")
        print(f"Pobrane strony: {len(downloaded_pages)}")
        print(f"Pominiete strony lacznie: {len(skipped_pages)}")
        print(f"Pominiete strony w tym uruchomieniu: {skipped_pages_this_run}")
        print(f"Odwiedzone kategorie: {len(visited_categories)}")
        print(f"Pominiete kategorie w tym uruchomieniu: {skipped_categories_this_run}")
        print(f"Zostalo kategorii: {len(pending_categories)}")
        print(f"Bledy stron w tym uruchomieniu: {page_errors}")
        print(f"Bledy kategorii w tym uruchomieniu: {category_errors}")
        print(f"Dane: {OUTPUT_FILE.resolve()}")