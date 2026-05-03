import time

from terraria_bot.api.wiki_api import api_get


CARGO_LIMIT = 250
CARGO_DELAY = 1.5


def get_cargo_tables():
    data = api_get(
        {
            "action": "cargotables",
            "format": "json",
        },
        "lista tabel Cargo",
    )

    if not data:
        return []

    raw = data.get("cargotables", {})
    tables = []

    if isinstance(raw, dict):
        return sorted(raw.keys())

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                tables.append(item)

            elif isinstance(item, dict):
                name = (
                    item.get("name")
                    or item.get("table")
                    or item.get("_tableName")
                    or item.get("title")
                )

                if isinstance(name, str):
                    tables.append(name)

    return sorted(set(tables))


def get_cargo_fields(table_name):
    data = api_get(
        {
            "action": "cargofields",
            "table": table_name,
            "format": "json",
        },
        f"pola tabeli Cargo: {table_name}",
    )

    if not data:
        return []

    raw = data.get("cargofields", {})

    if isinstance(raw, dict):
        return list(raw.keys())

    return []


def cargo_query_table(table_name, fields):
    rows = []
    offset = 0

    fields_param = "_pageName=page," + ",".join(fields)

    while True:
        data = api_get(
            {
                "action": "cargoquery",
                "tables": table_name,
                "fields": fields_param,
                "limit": CARGO_LIMIT,
                "offset": offset,
                "format": "json",
            },
            f"cargoquery {table_name}, offset={offset}",
        )

        if not data:
            break

        if "error" in data:
            print(f"API error dla tabeli {table_name}: {data['error']}")
            break

        batch = [
            row.get("title", {})
            for row in data.get("cargoquery", [])
        ]

        if not batch:
            break

        rows.extend(batch)

        print(f"{table_name}: {len(rows)} rekordów")

        if len(batch) < CARGO_LIMIT:
            break

        offset += CARGO_LIMIT
        time.sleep(CARGO_DELAY)

    return rows