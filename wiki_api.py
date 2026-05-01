import json
import random
import time

import requests

from config import API_URL, USER_AGENTS, CATEGORY_DELAY


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def get_headers():
    return {
        "User-Agent": USER_AGENTS[0],
        "Accept": "application/json",
    }


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
            headers=get_headers(),
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
        "cmnamespace": "0|14",
        "cmprop": "title|type",
        "cmlimit": "max",
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