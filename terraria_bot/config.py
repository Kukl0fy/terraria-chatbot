from pathlib import Path


API_URL = "https://terraria.wiki.gg/api.php"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


DATA_DIR.mkdir(exist_ok=True)

START_CATEGORY = "Terraria"

OUTPUT_FILE = DATA_DIR / "wiki_data.jsonl"
DOWNLOADED_FILE = DATA_DIR / "downloaded_pages.json"
SKIPPED_FILE = DATA_DIR / "skipped_pages.json"
PENDING_FILE = DATA_DIR / "pending_categories.json"
VISITED_FILE = DATA_DIR / "visited_categories.json"

STRUCTURED_DIR = DATA_DIR / "structured"
STRUCTURED_DIR.mkdir(exist_ok=True)

STRUCTURED_REQUEST_DELAY = 2
STRUCTURED_LIMIT = 250

RECIPES_FIELDS_FILE = STRUCTURED_DIR / "recipes_fields.json"
RECIPES_RAW_FILE = STRUCTURED_DIR / "recipes_raw.jsonl"
ITEM_NAMES_FILE = STRUCTURED_DIR / "item_names.json"


REQUEST_DELAY = 12
CATEGORY_DELAY = 10

MIN_TEXT_LENGTH = 0
