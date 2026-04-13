from categories_store import get_categories_by_label, load_grouped_categories
import requests
API_URL = "https://terraria.wiki.gg/api.php"


def search_category(category) -> list[str]:
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:" + category,
        "format": "json"
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data

def main() -> None:
   data = search_category("Axes")
   print(data["query"]["categorymembers"])


if __name__ == "__main__":
    main()