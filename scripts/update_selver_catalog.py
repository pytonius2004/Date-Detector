"""Download the public Selver search index into the bundled offline catalog."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
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
    "juustud": "Сыры",
    "kinkekaardid": "Товары для досуга",
}

# Selver publishes the hierarchy in ``klevu_category``.  Keep the same
# grouping in the offline database, but show the leaf names in Russian.
# Names are intentionally unique because older application databases used a
# global UNIQUE constraint for categories.
SUBCATEGORY_MAP = {
    "puu- ja köögiviljad": {
        "köögiviljad, juurviljad": "Овощи и корнеплоды",
        "maitsetaimed, värsked salatid, piprad, idud": "Зелень, салаты, перцы и проростки",
        "marjad": "Ягоды",
        "seened": "Грибы",
        "smuutid, värsked mahlad": "Смузи и свежие соки",
        "troopilised, eksootilised viljad": "Тропические и экзотические фрукты",
        "õunad, pirnid": "Яблоки и груши",
    },
    "liha- ja kalatooted": {
        "grillvorstid, verivorstid": "Колбаски для гриля и кровяные колбасы",
        "gurmee lihatooted": "Мясные деликатесы",
        "hakkliha": "Фарш",
        "keedu- ja suitsuvorstid, viinerid": "Варёные и копчёные колбасы, сосиски",
        "linnuliha": "Мясо птицы",
        "muud kalatooted": "Другие рыбные продукты",
        "muud lihatooted": "Другие мясные продукты",
        "sealiha": "Свинина",
        "singid, rulaadid": "Ветчина и рулеты",
        "soolatud ja suitsutatud kalatooted": "Солёная и копчёная рыба",
        "töödeldud mereannid": "Обработанные морепродукты",
        "veise-, lamba- ja ulukiliha": "Говядина, баранина и дичь",
        "värske kala, mereannid": "Свежая рыба и морепродукты",
    },
    "piimatooted, munad, võid": {
        "jogurtid, jogurtijoogid": "Йогурты и йогуртные напитки",
        "kohukesed": "Творожные сырки",
        "kohupiimad, kodujuustud": "Творог и зернёный творог",
        "munad": "Яйца",
        "muud magustoidud": "Молочные десерты",
        "piimad, koored": "Молоко и сливки",
        "võid, margariinid": "Сливочное масло и маргарин",
    },
    "juustud": {
        "juustud": "Классические сыры",
        "määrdejuustud": "Сыры, которые можно намазывать",
        "delikatessjuustud": "Деликатесные сыры",
    },
    "leivad, saiad, kondiitritooted": {
        "koogid, rullbiskviidid, tainad": "Пироги, рулеты и тесто",
        "leivad": "Хлеб",
        "näkileivad": "Хлебцы",
        "saiad": "Белый хлеб и батоны",
        "saiakesed, stritslid, kringlid": "Булочки, плетёнки и крендели",
        "selveri pagarid": "Выпечка Selver",
        "sepikud, kuklid, lavašid": "Зерновой хлеб, булочки и лаваш",
        "tordid": "Торты",
    },
    "valmistoidud": {
        "jahutatud valmistoidud": "Охлаждённые готовые блюда",
        "magustoidud": "Готовые десерты",
        "salatid": "Готовые салаты",
        "sushi": "Суши",
    },
    "selver gurmee": {
        "hoidised": "Консервы Selver Gurmee",
        "kuivained": "Бакалея Selver Gurmee",
        "lihatooted": "Мясо Selver Gurmee",
    },
    "kuivained, hommikusöögid, hoidised": {
        "hoidised": "Консервы",
        "kuivained, hommikusöögid": "Бакалея и завтраки",
    },
    "maailma köök, maitseained, puljongid": {
        "maailma köök": "Продукты мировой кухни",
        "maitseained": "Приправы",
        "puljongid": "Бульоны",
    },
    "kastmed, õlid": {
        "ketšupid, tomatipastad, kastmed": "Кетчупы, томатные пасты и соусы",
        "majoneesid, sinepid": "Майонезы и горчица",
        "õlid, äädikad": "Растительные масла и уксусы",
    },
    "maiustused, küpsised, näksid": {
        "kommikarbid": "Коробки конфет",
        "kommipakid": "Пакеты конфет",
        "küpsised": "Печенье",
        "muud maiustused": "Другие сладости",
        "näkileivad": "Сладкие хлебцы",
        "nätsud, pastillid": "Жевательная резинка и пастилки",
        "pähklid ja kuivatatud puuviljad": "Орехи и сухофрукты",
        "sipsid": "Чипсы и снеки",
        "šokolaadid": "Шоколад",
    },
    "külmutatud toidukaubad": {
        "jäätised": "Мороженое",
        "külmutatud köögiviljad, marjad, puuviljad": "Замороженные овощи, ягоды и фрукты",
        "külmutatud liha- ja kalatooted": "Замороженное мясо и рыба",
        "külmutatud tainad ja kondiitritooted": "Замороженное тесто и выпечка",
        "külmutatud valmistooted": "Замороженные готовые продукты",
    },
    "joogid": {
        "kange alkohol": "Крепкий алкоголь",
        "karastus- ja energiajoogid, toonikud": "Газированные, энергетические напитки и тоники",
        "kohv, tee, kakao": "Кофе, чай и какао",
        "lahja alkohol": "Слабоалкогольные напитки",
        "spordijoogid, pulbrid, batoonid": "Спортивные напитки, смеси и батончики",
        "veed, mahlad, siirupid, smuutid": "Вода, соки, сиропы и смузи",
        "välgumihklid ja tikud": "Зажигалки и спички",
    },
    "lastekaubad": {
        "beebi hooldusvahendid": "Уход за младенцами",
        "laste sokid, sukad, pesu": "Детские носки, колготки и бельё",
        "lastetoidud": "Детское питание",
        "mähkmed": "Подгузники",
        "tarvikud": "Детские принадлежности",
    },
    "lemmikloomakaubad": {
        "kala- ja linnutoidud": "Корм для рыб и птиц",
        "kassitoidud": "Корм для кошек",
        "koeratoidud": "Корм для собак",
        "lemmikloomatarbed": "Принадлежности для питомцев",
        "väikeloomatoidud": "Корм для мелких животных",
    },
    "enesehooldustarbed": {
        "dekoratiivkosmeetika tooted": "Декоративная косметика",
        "juuksehooldus": "Уход за волосами",
        "kehahooldus": "Уход за телом",
        "näohooldus": "Уход за лицом",
        "suuhooldus": "Уход за полостью рта",
        "tervisekaubad": "Товары для здоровья",
    },
    "majapidamis- ja kodukaubad": {
        "aiakaubad": "Товары для сада",
        "kodutehnika": "Бытовая техника",
        "köögitarbed": "Кухонные принадлежности",
        "muud majapidamise kaubad": "Другие хозяйственные товары",
        "paberitooted": "Бумажные товары",
        "puhastus-ja koristusvahendid": "Средства для уборки",
        "rõivaste ja jalatsite hooldus": "Уход за одеждой и обувью",
        "sisustuskaubad": "Предметы интерьера",
        "tekid, padjad, tekstiil": "Одеяла, подушки и текстиль",
        "vannitoa- ja saunatarvikud": "Принадлежности для ванной и сауны",
    },
    "vabaajakaubad": {
        "autokaubad": "Автотовары",
        "garderoobikaubad": "Одежда и аксессуары",
        "kontori- ja koolitarbed": "Офисные и школьные принадлежности",
        "meedia": "Медиа",
        "mänguasjad": "Игрушки",
        "raamatud, ajalehed, ajakirjad, kinkekaardid ja kõnekaardid": "Книги, пресса и подарочные карты",
        "reisi- ja matkatarbed": "Товары для путешествий и туризма",
        "sportimisevahendid": "Спортивные товары",
    },
    "pühade- ja tähtpäevakaubad": {
        "jõulukaubad": "Новогодние товары",
        "kingiideed": "Идеи для подарков",
    },
    "selveri köögi peolaud": {
        "eelroad": "Праздничные закуски",
        "kondiitritooted": "Праздничные кондитерские изделия",
        "pagaritooted": "Праздничная выпечка",
        "põhiroad": "Праздничные основные блюда",
        "suupisted": "Закуски для праздника",
        "valikud": "Праздничные наборы",
    },
    "suurpakendid": {"lihatooted": "Мясные продукты большими упаковками"},
}

CATEGORY_ORDER = [
    "Фрукты и овощи",
    "Мясные и рыбные продукты",
    "Молочные продукты, яйца, сливочное масло",
    "Сыры",
    "Хлеб, булка, кондитерские изделия",
    "Готовые продукты",
    "Большие упаковки",
    "Бакалея и консервы",
    "Мировая кухня, приправы и бульоны",
    "Соусы, масло",
    "Сладости, печенье, чипсы",
    "Замороженные продтовары",
    "Напитки",
    "Детские товары",
    "Товары для домашних питомцев",
    "Личная гигиена",
    "Хозяйственные и бытовые товары",
    "Товары для досуга",
    "Товары для праздников",
]


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


def russian_category(record: dict) -> tuple[str, str, str]:
    top, sub = category_parts(record)
    name = str(record.get("name") or "").casefold()
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

    leaf = SUBCATEGORY_MAP.get(top.casefold(), {}).get(sub.casefold())
    if not leaf:
        leaf = f"Прочее — {mapped}"
    return mapped, leaf, f"{top} / {sub}".strip(" /")


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
    hierarchy: dict[str, str] = {}
    missing = 0
    for record in records:
        barcode = extract_barcode(record)
        if not barcode:
            missing += 1
            continue
        parent_category, department, source_category = russian_category(record)
        hierarchy[department] = parent_category
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

            -- The same file can be selected in the application's Import dialog.
            CREATE TABLE products (
                barcode TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL DEFAULT '',
                photo_path TEXT NOT NULL DEFAULT '',
                photo_url TEXT NOT NULL DEFAULT '',
                product_url TEXT NOT NULL DEFAULT '',
                manual_no_date INTEGER NOT NULL DEFAULT 1,
                hidden_from_list INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE expirations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,
                exp_date TEXT NOT NULL,
                written_off INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (barcode) REFERENCES products(barcode) ON DELETE CASCADE
            );
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER DEFAULT NULL,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE RESTRICT
            );
            CREATE INDEX idx_products_department ON products(department);
            CREATE INDEX idx_products_name ON products(name COLLATE NOCASE);
            CREATE INDEX idx_products_created_at ON products(created_at DESC);
            CREATE INDEX idx_categories_sort_order ON categories(sort_order, id);
            CREATE INDEX idx_categories_parent ON categories(parent_id, sort_order, id);
            CREATE UNIQUE INDEX idx_barcode_expiration ON expirations(barcode, exp_date);
            CREATE INDEX idx_active_expirations ON expirations(barcode, written_off, exp_date);
            """
        )
        connection.executemany(
            "INSERT INTO catalog_products VALUES (?, ?, ?, ?, ?, ?)",
            rows.values(),
        )
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        inventory_rows = []
        for index, row in enumerate(rows.values()):
            barcode, name, department, photo_url, product_url, _source = row
            created_at = (generated_at + timedelta(microseconds=index)).isoformat(
                timespec="microseconds"
            )
            inventory_rows.append(
                (
                    barcode,
                    name,
                    department,
                    "",
                    photo_url,
                    product_url,
                    1,
                    0,
                    created_at,
                )
            )
        connection.executemany(
            """
            INSERT INTO products(
                barcode, name, department, photo_path, photo_url, product_url,
                manual_no_date, hidden_from_list, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            inventory_rows,
        )

        available_parents = set(hierarchy.values())
        ordered_parents = [c for c in CATEGORY_ORDER if c in available_parents]
        ordered_parents.extend(sorted(available_parents - set(ordered_parents), key=str.casefold))
        parent_ids: dict[str, int] = {}
        timestamp = generated_at.isoformat(timespec="microseconds")
        for index, category in enumerate(ordered_parents):
            cursor = connection.execute(
                "INSERT INTO categories(parent_id, name, sort_order, created_at) VALUES (NULL, ?, ?, ?)",
                (category, index, timestamp),
            )
            parent_ids[category] = int(cursor.lastrowid)

        for parent in ordered_parents:
            children = sorted(
                (leaf for leaf, owner in hierarchy.items() if owner == parent),
                key=str.casefold,
            )
            connection.executemany(
                "INSERT INTO categories(parent_id, name, sort_order, created_at) VALUES (?, ?, ?, ?)",
                [
                    (parent_ids[parent], child, index, timestamp)
                    for index, child in enumerate(children)
                ],
            )
        connection.executemany(
            "INSERT INTO catalog_meta(key, value) VALUES (?, ?)",
            [
                ("source", "Selver / Klevu public search index"),
                ("updated_at", datetime.now(timezone.utc).isoformat()),
                ("source_total", str(expected_total)),
                ("catalog_rows", str(len(rows))),
                ("missing_barcode", str(missing)),
                ("category_levels", "2"),
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
