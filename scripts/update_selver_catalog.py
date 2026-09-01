"""Download the public Selver search index into the bundled offline catalog."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ENDPOINT = "https://eucs3v2.ksearchnet.com/cs/v2/search"
API_KEY = "klevu-14410928010151845"
BATCH_SIZE = 500
BARCODE_RE = re.compile(r"(?<!\d)(\d{8,14})(?!\d)")

TOP_LEVEL_MAP = {
    "puu- ja köögiviljad": "Фрукты и овощи",
    "puu- ja juurviljad": "Фрукты и овощи",
    "liha- ja kalatooted": "Мясные и рыбные продукты",
    "piimatooted, munad, võid": "Молочные продукты, яйца, сливочное масло",
    "leib, sai, kondiitritooted": "Хлеб, булка, кондитерские изделия",
    "valmistoidud": "Готовые продукты",
    "valmistoit": "Готовые продукты",
    "toidukaubad": "Бакалея и консервы",
    "kuivained, hommikusöögid, hoidised": "Бакалея и консервы",
    "maailmaköök": "Мировая кухня, приправы и бульоны",
    "maailma köök, maitseained, puljongid": "Мировая кухня, приправы и бульоны",
    "kastmed ja õlid": "Соусы, масло",
    "kastmed, õlid": "Соусы, масло",
    "maiustused ja snäkid": "Сладости, печенье, чипсы",
    "maiustused, küpsised, näksid": "Сладости, печенье, чипсы",
    "külmutatud tooted": "Замороженные продтовары",
    "külmutatud toidukaubad": "Замороженные продтовары",
    "joogid": "Напитки",
    "lastekaubad": "Детские товары",
    "lemmikloomakaubad": "Товары для домашних питомцев",
    "ilu ja hügieen": "Личная гигиена",
    "enesehooldustarbed": "Личная гигиена",
    "majapidamiskaubad": "Хозяйственные и бытовые товары",
    "majapidamis- ja kodukaubad": "Хозяйственные и бытовые товары",
    "vaba aeg": "Товары для досуга",
    "vabaajakaubad": "Товары для досуга",
    "peokaubad": "Товары для праздников",
    "hooajakaubad": "Товары для праздников",
    "pühade- ja tähtpäevakaubad": "Товары для праздников",
    "selveri köögi peolaud": "Товары для праздников",
    "leivad, saiad, kondiitritooted": "Хлеб, булка, кондитерские изделия",
    "hulgipakkumised": "Большие упаковки",
    "suurpakendid": "Большие упаковки",
    "selver gurmee": "Готовые продукты",
}


def post_search(offset: int) -> dict:
    payload = {
        "recordQueries": [
            {
                "id": "productSearch",
                "settings": {
                    "query": {"term": "*"},
                    "typeOfRecords": ["KLEVU_PRODUCT"],
                    "fields": [],
                    "limit": BATCH_SIZE,
                    "offset": offset,
                },
            }
        ],
        "context": {"apiKeys": [API_KEY]},
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Date-Detector catalog updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def extract_barcode(record: dict) -> str:
    for key in ("barcode", "ean", "gtin", "imageUrl", "image"):
        value = str(record.get(key) or "")
        path = urlparse(value).path
        candidates = BARCODE_RE.findall(Path(path).stem or value)
        if candidates:
            return max(candidates, key=len)
    return ""


def category_parts(record: dict) -> tuple[str, str]:
    raw = str(record.get("klevu_category") or "")
    paths = raw.split(" @ku@kuCategory@ku@")[0].split(";;")
    for path in paths:
        parts = [part.strip() for part in path.split(";") if part.strip()]
        if parts and parts[0].casefold() == "e-selver" and len(parts) >= 2:
            return parts[1], (parts[2] if len(parts) >= 3 else "")
    return "", str(record.get("category") or "").split(";;", 1)[0].strip()


def russian_category(record: dict) -> tuple[str, str]:
    top, sub = category_parts(record)
    combined = f"{top} {sub}".casefold()
    name = str(record.get("name") or "").casefold()
    if "juust" in combined:
        return "Сыры", f"{top} / {sub}".strip(" /")

    mapped = TOP_LEVEL_MAP.get(top.casefold())
    if not mapped:
        if any(word in name for word in ("salvrät", "vatipad", "vatitik")):
            mapped = "Личная гигиена"
        elif "kombucha" in name:
            mapped = "Напитки"
        elif "sai" in name:
            mapped = "Хлеб, булка, кондитерские изделия"
        else:
            mapped = "Товары для досуга"
    return mapped, f"{top} / {sub}".strip(" /")


def download_all() -> tuple[list[dict], int]:
    records: list[dict] = []
    total = 0
    offset = 0
    while offset < total or offset == 0:
        data = post_search(offset)
        result = data["queryResults"][0]
        total = int(result["meta"]["totalResultsFound"])
        batch = result.get("records", [])
        if not batch:
            break
        records.extend(batch)
        offset += len(batch)
        print(f"Downloaded {offset}/{total}", flush=True)
    return records, total


def write_database(path: Path, records: list[dict], expected_total: int) -> None:
    rows: dict[str, tuple[str, str, str, str, str, str]] = {}
    missing = 0
    for record in records:
        barcode = extract_barcode(record)
        if not barcode:
            missing += 1
            continue
        department, source_category = russian_category(record)
        rows[barcode] = (
            barcode,
            str(record.get("name") or "").strip(),
            department,
            str(record.get("imageUrl") or record.get("image") or "").strip(),
            str(record.get("url") or "").strip(),
            source_category,
        )

    if len(rows) < expected_total * 0.90:
        raise RuntimeError(
            f"Only {len(rows)} of {expected_total} records have a barcode; refusing to replace catalog"
        )

    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE catalog_products (
                barcode TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                photo_url TEXT NOT NULL,
                product_url TEXT NOT NULL,
                source_category TEXT NOT NULL
            );
            CREATE INDEX idx_catalog_department ON catalog_products(department);
            CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        connection.executemany(
            "INSERT INTO catalog_products VALUES (?, ?, ?, ?, ?, ?)",
            rows.values(),
        )
        connection.executemany(
            "INSERT INTO catalog_meta(key, value) VALUES (?, ?)",
            [
                ("source", "Selver / Klevu public search index"),
                ("updated_at", datetime.now(timezone.utc).isoformat()),
                ("source_total", str(expected_total)),
                ("catalog_rows", str(len(rows))),
                ("missing_barcode", str(missing)),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    print(f"Wrote {len(rows)} products to {path} ({missing} without extractable barcode)")


def main() -> int:
    destination = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "selver_base.db"
    )
    records, total = download_all()
    write_database(destination, records, total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
