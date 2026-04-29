import requests

API_URL = "https://terraria.wiki.gg/api.php"

HEADERS = {
    "User-Agent": "TerrariaStudentProject/1.0",
    "Api-User-Agent": "TerrariaStudentProject/1.0",
    "Accept": "application/json",
}

tests = [
    {
        "name": "siteinfo",
        "params": {
            "action": "query",
            "meta": "siteinfo",
            "format": "json",
        },
    },
    {
        "name": "categorymembers Terraria",
        "params": {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Terraria",
            "cmtype": "page|subcat",
            "cmprop": "title|type",
            "cmlimit": 50,
            "format": "json",
        },
    },
    {
        "name": "parse Terraria",
        "params": {
            "action": "parse",
            "page": "Terraria",
            "prop": "text",
            "format": "json",
            "redirects": 1,
        },
    },
]

for test in tests:
    print("\n" + "=" * 60)
    print(test["name"])

    response = requests.get(
        API_URL,
        headers=HEADERS,
        params=test["params"],
        timeout=30,
    )

    print("status:", response.status_code)
    print("url:", response.url)
    print("content-type:", response.headers.get("content-type"))
    print("first 300 chars:")
    print(response.text[:300])

    if "Just a second" in response.text:
        print("WYKRYTO OCHRONE ANTYBOTOWA")