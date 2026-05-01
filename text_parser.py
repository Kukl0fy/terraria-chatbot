from bs4 import BeautifulSoup

from wiki_api import api_get


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
        ".metadata",
        ".ambox",
        ".hatnote",
        ".dablink",
        ".printfooter",
        ".catlinks",
    ]:
        for element in soup.select(selector):
            element.extract()

    return soup.get_text(separator=" ", strip=True)