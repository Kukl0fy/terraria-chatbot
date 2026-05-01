import re

from config import MIN_TEXT_LENGTH


SKIP_CATEGORY_EXACT = {
    # Historia wersji / changelogi
    "Version history",
    "Desktop version history",
    "Console version history",
    "Mobile version history",
    "Old-gen console version history",
    "Nintendo 3DS version history",
    "Windows Phone version history",

    # Legacy / platform-specific content
    "Old-gen console content",
    "Nintendo 3DS content",
    "Windows Phone content",
    "Chinese content",
    "Google Stadia content",
    "Console content",
    "Mobile content",

    # Techniczne kategorie wiki
    "Pages with broken file links",
    "Pages using DynamicPageList3 parser function",
    "Pages with script errors",
    "Pages with too many expensive parser function calls",
    "Pages with missing files",
    "Hidden categories",
    "Maintenance",
    "Candidates for deletion",
    "Disambiguations",
    "Redirects",
    "Templates",
    "Template documentation",
    "Images",
    "Files",
    "Categories",
    "Pages",
    "Wiki maintenance",
    "Tracking categories",
    "Pages with syntax highlighting errors",
    "Pages with ignored display titles",
    "Pages using duplicate arguments in template calls",

    # Społeczność / organizacja wiki
    "Terraria Wiki",
    "Community",
    "Administrators",
    "Policies",
    "Guidelines",
    "Help",
    "User pages",
    "Talk pages",

    # Języki / tłumaczenia
    "Translations",
    "Translation pages",
    "Language pages",

    # Pliki/grafiki
    "Icons",
    "Item icons",
    "NPC icons",
    "Images by license",
    "Sprites",
    "Screenshots",
    "Background images",
    "Maps",

    # Dokumentacja i testy
    "Documentation",
    "Sandboxes",
    "Testcases",
}


SKIP_CATEGORY_CONTAINS = [
    # wersje / changelogi
    "version history",
    "patch notes",
    "changelog",
    "versions",
    "update history",
    "release history",

    # techniczne wiki
    "maintenance",
    "template",
    "templates",
    "module",
    "modules",
    "file",
    "files",
    "image",
    "images",
    "icon",
    "icons",
    "sprite",
    "sprites",
    "screenshot",
    "screenshots",
    "redirect",
    "redirects",
    "broken file",
    "script error",
    "documentation",
    "deletion",
    "disambiguation",
    "wiki maintenance",
    "tracking",
    "hidden category",
    "parser function",
    "expensive parser",
    "duplicate arguments",
    "syntax highlighting",
    "display title",

    # user/community/help
    "user page",
    "user pages",
    "talk page",
    "talk pages",
    "community",
    "administrator",
    "administrators",
    "policy",
    "policies",
    "guideline",
    "guidelines",
    "help",
    "project",

    # tłumaczenia
    "translation",
    "translations",
    "language",

    # testy/sandboxy
    "sandbox",
    "testcase",
    "testcases",
    "doc",

    # galerie / obrazy
    "gallery",
    "galleries",
    "license",
    "licenses",
]


SKIP_PAGE_EXACT = {
    # wersje
    "Desktop version history",
    "Console version history",
    "Mobile version history",
    "Old-gen console version history",
    "Nintendo 3DS version history",
    "Windows Phone version history",
    "Version history",
    "Upcoming features",
    "Future features",

    # wiki/meta
    "Terraria Wiki",
    "Terraria Wiki:About",
    "Terraria Wiki:General disclaimer",
    "Terraria Wiki:Privacy policy",
    "Terraria Wiki:Copyrights",
    "Terraria Wiki:Administrators",
    "Terraria Wiki:Rules",
    "Terraria Wiki:Community portal",
    "Terraria Wiki:Projects",

    # pomoc / techniczne
    "Help",
    "Help:Contents",
    "Sandbox",
    "Template documentation",
}


SKIP_PAGE_PREFIXES = (
    "Category:",
    "File:",
    "Image:",
    "Template:",
    "Module:",
    "User:",
    "User talk:",
    "Talk:",
    "Terraria Wiki:",
    "MediaWiki:",
    "Help:",
    "Special:",
    "Widget:",
    "Gadget:",
    "Gadget definition:",
)


SKIP_PAGE_CONTAINS = [
    # archiwa / historia / changelogi
    "archive",
    "archives",
    "version history",
    "patch notes",
    "changelog",
    "old-gen",
    "legacy",
    "removed features",
    "upcoming features",
    "future features",

    # techniczne
    "template",
    "documentation",
    "sandbox",
    "testcase",
    "testcases",
    "module",
    "redirect",
    "disambiguation",
    "candidate for deletion",
    "maintenance",
    "broken file",
    "script error",

    # pliki / grafiki
    "gallery",
    "galleries",
    "icon",
    "icons",
    "sprite",
    "sprites",
    "screenshot",
    "screenshots",
    "map image",
    "background image",

    # wiki/community
    "admin noticeboard",
    "community portal",
    "style guide",
    "manual of style",
    "rules",
    "policy",
    "policies",
    "guideline",
    "guidelines",
    "copyright",
    "privacy policy",
    "general disclaimer",

    # tłumaczenia / języki
    "translation",
    "translations",
    "language",
]


SKIP_TITLE_SUFFIXES = (
    "/Archive",
    "/Archives",
    "/Doc",
    "/Documentation",
    "/Sandbox",
    "/Test",
    "/Tests",
    "/Testcases",
    "/Editnotice",
)


VERSION_PAGE_RE = re.compile(
    r"^\d+(?:\.\d+){1,5}[a-z]?$",
    re.IGNORECASE,
)

PLATFORM_VERSION_PAGE_RE = re.compile(
    r"^(Desktop|Mobile|Console|Old-gen console|Nintendo 3DS|Windows Phone)\s+\d+(?:\.\d+){1,5}[a-z]?$",
    re.IGNORECASE,
)

VERSION_HISTORY_PAGE_RE = re.compile(
    r"^(Desktop|Console|Mobile|Old-gen console|Nintendo 3DS|Windows Phone)\s+version history",
    re.IGNORECASE,
)


def should_skip_category(category_name):
    normalized = category_name.strip()
    lowered = normalized.lower()

    if normalized in SKIP_CATEGORY_EXACT:
        return True

    for fragment in SKIP_CATEGORY_CONTAINS:
        if fragment in lowered:
            return True

    return False


def should_skip_page(title):
    normalized = title.strip()
    lowered = normalized.lower()

    if normalized in SKIP_PAGE_EXACT:
        return True

    for prefix in SKIP_PAGE_PREFIXES:
        if normalized.startswith(prefix):
            return True

    for suffix in SKIP_TITLE_SUFFIXES:
        if normalized.endswith(suffix):
            return True

    for fragment in SKIP_PAGE_CONTAINS:
        if fragment in lowered:
            return True

    if VERSION_PAGE_RE.match(normalized):
        return True

    if PLATFORM_VERSION_PAGE_RE.match(normalized):
        return True

    if VERSION_HISTORY_PAGE_RE.match(normalized):
        return True

    # Strony typu "1.4.4/Notes" albo "1.3.0.1/Images"
    if "/" in normalized:
        first_part = normalized.split("/", 1)[0]

        if VERSION_PAGE_RE.match(first_part):
            return True

    return False


def is_bad_text(text):
    if not text:
        return True

    cleaned = text.strip()

    if len(cleaned) < MIN_TEXT_LENGTH:
        return True

    lowered = cleaned.lower()

    bad_fragments = [
        "this category contains",
        "this page is a candidate for deletion",
        "redirect page",
        "this page is a redirect",
        "template documentation",
        "module documentation",
        "this is an archive",
        "archive of past discussions",
        "please do not edit this archive",
    ]

    for fragment in bad_fragments:
        if fragment in lowered:
            return True

    return False