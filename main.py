# -*- coding: utf-8 -*-

import os
import shutil
import sqlite3

from datetime import date, datetime, timedelta
from pathlib import Path


# =========================================================
# KIVY CONFIG
# =========================================================

os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")
os.environ.setdefault("KIVY_GRAPHICS", "gles")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "0")


# =========================================================
# KIVY IMPORTS
# =========================================================

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import (
    Screen,
    ScreenManager,
    FadeTransition,
)
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from kivy.utils import platform


# =========================================================
# COLORS / THEME
# =========================================================

BG = (
    0.045,
    0.047,
    0.055,
    1,
)

CARD = (
    0.10,
    0.105,
    0.12,
    1,
)

CARD_DISABLED = (
    0.20,
    0.20,
    0.22,
    1,
)

TEXT = (
    0.96,
    0.96,
    0.97,
    1,
)

TEXT_SECONDARY = (
    0.67,
    0.68,
    0.72,
    1,
)

BUTTON_BG = (
    0.20,
    0.21,
    0.24,
    1,
)

BUTTON_BG_DOWN = (
    0.27,
    0.28,
    0.32,
    1,
)

YELLOW = (
    1.00,
    0.78,
    0.13,
    1,
)

YELLOW_TEXT = (
    0.10,
    0.08,
    0.03,
    1,
)

RED = (
    0.82,
    0.12,
    0.13,
    1,
)

RED_TEXT = (
    1,
    1,
    1,
    1,
)

GREEN = (
    0.13,
    0.57,
    0.27,
    1,
)

# Основной фирменный акцент из иконки приложения: #83121e
ACCENT_RED = (
    131 / 255,
    18 / 255,
    30 / 255,
    1,
)

# Чуть темнее при нажатии
ACCENT_RED_DOWN = (
    0.40,
    0.045,
    0.075,
    1,
)

Window.clearcolor = BG


# =========================================================
# ANDROID / PYJNIUS
# =========================================================

ANDROID = platform == "android"

PYJNIUS_AVAILABLE = False
PYJNIUS_ERROR = ""

autoclass = None
cast = None
activity_helper = None


if ANDROID:

    try:

        from jnius import autoclass, cast

        PYJNIUS_AVAILABLE = True

    except Exception as exc:

        PYJNIUS_ERROR = (
            type(exc).__name__
            +
            ": "
            +
            str(exc)
        )

    try:

        from android import activity

        activity_helper = activity

    except Exception:

        activity_helper = None


# =========================================================
# CONSTANTS
# =========================================================

APP_TITLE = "Сроки Годности"

HEADER_TITLE = "Pyton Detector"

LOGO_FILE = "logo1.png"

DB_NAME = "inventory.db"

DATE_DB_FORMAT = "%Y-%m-%d"
DATE_USER_FORMAT = "%d.%m.%y"

REQUEST_SCAN_BARCODE = 7001
REQUEST_IMPORT_DB = 4102


# =========================================================
# SAFE AREA
# =========================================================

if ANDROID:

    SAFE_TOP = dp(32)
    SAFE_BOTTOM = dp(34)

else:

    SAFE_TOP = 0
    SAFE_BOTTOM = 0


def safe_padding(
    horizontal=12,
    top=12,
    bottom=12
):

    return (
        dp(horizontal),
        dp(top) + SAFE_TOP,
        dp(horizontal),
        dp(bottom) + SAFE_BOTTOM,
    )


# =========================================================
# BARCODE
# =========================================================

def normalize_barcode(value):

    if value is None:

        return ""

    return str(value).strip()


def barcode_variants(barcode):

    barcode = normalize_barcode(
        barcode
    )

    if not barcode:

        return []

    result = [
        barcode
    ]

    if (
        barcode.startswith("0")
        and
        len(barcode) > 1
    ):

        result.append(
            barcode[1:]
        )

    if (
        len(barcode) == 12
        and
        barcode.isdigit()
    ):

        result.append(
            "0" + barcode
        )

    unique = []

    for item in result:

        if item not in unique:

            unique.append(
                item
            )

    return unique


# =========================================================
# DATE
# =========================================================

def parse_user_date(value):

    digits = "".join(
        char
        for char in str(value)
        if char.isdigit()
    )

    if len(digits) == 6:

        try:

            day = int(
                digits[0:2]
            )

            month = int(
                digits[2:4]
            )

            year = (
                2000
                +
                int(
                    digits[4:6]
                )
            )

            parsed = date(
                year,
                month,
                day
            )

            return parsed.strftime(
                DATE_DB_FORMAT
            )

        except ValueError:

            return None

    if len(digits) == 8:

        try:

            day = int(
                digits[0:2]
            )

            month = int(
                digits[2:4]
            )

            year = int(
                digits[4:8]
            )

            parsed = date(
                year,
                month,
                day
            )

            return parsed.strftime(
                DATE_DB_FORMAT
            )

        except ValueError:

            return None

    return None


def format_date(value):

    if not value:

        return "—"

    try:

        return datetime.strptime(
            value,
            DATE_DB_FORMAT
        ).strftime(
            DATE_USER_FORMAT
        )

    except ValueError:

        return value


# =========================================================
# CUSTOM BUTTON
# =========================================================

class RoundedButton(Button):

    normal_color = ListProperty(
        BUTTON_BG
    )

    down_color = ListProperty(
        BUTTON_BG_DOWN
    )

    radius = dp(14)

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(
            **kwargs
        )

        self.background_normal = ""
        self.background_down = ""

        self.background_color = (
            0,
            0,
            0,
            0,
        )

        self.color = TEXT

        with self.canvas.before:

            self._color = Color(
                *self.normal_color
            )

            self._rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[
                    self.radius,
                ],
            )

        self.bind(
            pos=self._update_canvas,
            size=self._update_canvas,
            state=self._update_state,
            normal_color=self._update_state,
            down_color=self._update_state,
        )

    def _update_canvas(
        self,
        *_
    ):

        self._rect.pos = (
            self.pos
        )

        self._rect.size = (
            self.size
        )

    def _update_state(
        self,
        *_
    ):

        if self.state == "down":

            color = (
                self.down_color
            )

        else:

            color = (
                self.normal_color
            )

        self._color.rgba = (
            color
        )


# =========================================================
# PRODUCT CARD
# =========================================================

class ProductCard(
    ButtonBehavior,
    BoxLayout
):

    background_color = ListProperty(
        CARD
    )

    foreground_color = ListProperty(
        TEXT
    )

    def __init__(
        self,
        product_name,
        barcode,
        exp_date,
        **kwargs
    ):

        super().__init__(
            **kwargs
        )

        self.orientation = (
            "horizontal"
        )

        self.size_hint_y = None

        self.height = dp(
            112
        )

        self.padding = (
            dp(17),
            dp(12),
        )

        self.spacing = dp(
            10
        )

        with self.canvas.before:

            self._bg_color = Color(
                *self.background_color
            )

            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[
                    dp(17),
                ],
            )

        self.bind(
            pos=self._update_card,
            size=self._update_card,
            background_color=self._update_color,
        )

        # -------------------------------------------------
        # LEFT SIDE
        # -------------------------------------------------

        left = BoxLayout(
            orientation="vertical"
        )

        self.name_label = Label(
            text=(
                product_name
                or
                "Без названия"
            ),
            color=self.foreground_color,
            bold=True,
            font_size="18sp",
            halign="left",
            valign="middle",
            size_hint_y=0.55,
        )

        self.name_label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        self.barcode_label = Label(
            text=(
                f"Штрихкод: {barcode}"
            ),
            color=self.foreground_color,
            font_size="13sp",
            halign="left",
            valign="middle",
            size_hint_y=0.45,
        )

        self.barcode_label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        left.add_widget(
            self.name_label
        )

        left.add_widget(
            self.barcode_label
        )

        # -------------------------------------------------
        # RIGHT SIDE
        # -------------------------------------------------

        right = BoxLayout(
            orientation="vertical",
            size_hint_x=0.38,
        )

        self.valid_label = Label(
            text="Годен до:",
            color=self.foreground_color,
            font_size="13sp",
            halign="right",
            valign="bottom",
            size_hint_y=0.42,
        )

        self.valid_label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        self.date_label = Label(
            text=exp_date,
            color=self.foreground_color,
            bold=True,
            font_size="21sp",
            halign="right",
            valign="top",
            size_hint_y=0.58,
        )

        self.date_label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        right.add_widget(
            self.valid_label
        )

        right.add_widget(
            self.date_label
        )

        self.add_widget(
            left
        )

        self.add_widget(
            right
        )

    def set_foreground(
        self,
        color
    ):

        self.foreground_color = (
            color
        )

        self.name_label.color = (
            color
        )

        self.barcode_label.color = (
            color
        )

        self.valid_label.color = (
            color
        )

        self.date_label.color = (
            color
        )

    def _update_card(
        self,
        *_
    ):

        self._bg_rect.pos = (
            self.pos
        )

        self._bg_rect.size = (
            self.size
        )

    def _update_color(
        self,
        *_
    ):

        self._bg_color.rgba = (
            self.background_color
        )


# =========================================================
# DATE INPUT
# =========================================================

class DateInput(TextInput):

    def _format_digits(
        self,
        digits
    ):

        digits = "".join(
            char
            for char in digits
            if char.isdigit()
        )[:6]

        if len(digits) <= 2:

            return digits

        if len(digits) <= 4:

            return (
                digits[:2]
                +
                "."
                +
                digits[2:]
            )

        return (
            digits[:2]
            +
            "."
            +
            digits[2:4]
            +
            "."
            +
            digits[4:6]
        )

    def _move_cursor_to_end(
        self,
        *_
    ):

        self.cursor = (
            len(self.text),
            0
        )

    def insert_text(
        self,
        substring,
        from_undo=False
    ):

        new_digits = "".join(
            char
            for char in substring
            if char.isdigit()
        )

        if not new_digits:

            return

        current_digits = "".join(
            char
            for char in self.text
            if char.isdigit()
        )

        free_space = (
            6
            -
            len(
                current_digits
            )
        )

        if free_space <= 0:

            return

        all_digits = (
            current_digits
            +
            new_digits[:free_space]
        )

        self.text = self._format_digits(
            all_digits
        )

        Clock.schedule_once(
            self._move_cursor_to_end,
            0
        )

    def do_backspace(
        self,
        from_undo=False,
        mode="bkspc"
    ):

        digits = "".join(
            char
            for char in self.text
            if char.isdigit()
        )

        if not digits:

            return

        self.text = self._format_digits(
            digits[:-1]
        )

        Clock.schedule_once(
            self._move_cursor_to_end,
            0
        )


# =========================================================
# DATABASE
# =========================================================

class Database:

    def __init__(
        self,
        path
    ):

        self.path = Path(
            path
        )

        self.conn = sqlite3.connect(
            str(
                self.path
            )
        )

        self.conn.row_factory = (
            sqlite3.Row
        )

        self.conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.create_schema()

    def create_schema(self):

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                barcode TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS expirations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,
                exp_date TEXT NOT NULL,
                written_off INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,

                FOREIGN KEY (barcode)
                    REFERENCES products(barcode)
                    ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_barcode_expiration
            ON expirations(
                barcode,
                exp_date
            );

            CREATE INDEX IF NOT EXISTS
            idx_active_expirations
            ON expirations(
                barcode,
                written_off,
                exp_date
            );
            """
        )

        self.conn.commit()

    def close(self):

        try:

            self.conn.close()

        except Exception:

            pass

    def clear_all(self):

        self.conn.execute(
            "DELETE FROM expirations"
        )

        self.conn.execute(
            "DELETE FROM products"
        )

        self.conn.commit()

    def get_product(
        self,
        barcode
    ):

        for candidate in barcode_variants(
            barcode
        ):

            row = self.conn.execute(
                """
                SELECT *
                FROM products
                WHERE barcode = ?
                """,
                (
                    candidate,
                ),
            ).fetchone()

            if row:

                return row

        return None

    def save_product(
        self,
        barcode,
        name
    ):

        barcode = normalize_barcode(
            barcode
        )

        name = name.strip()

        existing = self.get_product(
            barcode
        )

        if existing:

            self.conn.execute(
                """
                UPDATE products
                SET name = ?
                WHERE barcode = ?
                """,
                (
                    name,
                    existing["barcode"],
                ),
            )

        else:

            self.conn.execute(
                """
                INSERT INTO products(
                    barcode,
                    name,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

        self.conn.commit()

    def add_expiration(
        self,
        barcode,
        exp_date
    ):

        product = self.get_product(
            barcode
        )

        if product:

            barcode = (
                product[
                    "barcode"
                ]
            )

        try:

            self.conn.execute(
                """
                INSERT INTO expirations(
                    barcode,
                    exp_date,
                    written_off,
                    created_at
                )
                VALUES (?, ?, 0, ?)
                """,
                (
                    barcode,
                    exp_date,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            self.conn.commit()

            return True

        except sqlite3.IntegrityError:

            return False

    def get_active_expirations(
        self,
        barcode
    ):

        product = self.get_product(
            barcode
        )

        if product:

            barcode = (
                product[
                    "barcode"
                ]
            )

        return self.conn.execute(
            """
            SELECT *
            FROM expirations
            WHERE barcode = ?
              AND written_off = 0
            ORDER BY
                exp_date ASC,
                id ASC
            """,
            (
                barcode,
            ),
        ).fetchall()

    def get_all_expirations(
        self,
        barcode
    ):

        product = self.get_product(
            barcode
        )

        if product:

            barcode = (
                product[
                    "barcode"
                ]
            )

        return self.conn.execute(
            """
            SELECT *
            FROM expirations
            WHERE barcode = ?
            ORDER BY
                written_off ASC,
                exp_date ASC,
                id ASC
            """,
            (
                barcode,
            ),
        ).fetchall()

    def get_next_expiration(
        self,
        barcode
    ):

        product = self.get_product(
            barcode
        )

        if product:

            barcode = (
                product[
                    "barcode"
                ]
            )

        return self.conn.execute(
            """
            SELECT *
            FROM expirations
            WHERE barcode = ?
              AND written_off = 0
            ORDER BY
                exp_date ASC,
                id ASC
            LIMIT 1
            """,
            (
                barcode,
            ),
        ).fetchone()

    def write_off_next(
        self,
        barcode
    ):

        row = self.get_next_expiration(
            barcode
        )

        if not row:

            return False

        self.conn.execute(
            """
            UPDATE expirations
            SET written_off = 1
            WHERE id = ?
            """,
            (
                row["id"],
            ),
        )

        self.conn.commit()

        return True

    def get_product_list(self):

        return self.conn.execute(
            """
            SELECT
                p.barcode,
                p.name,

                (
                    SELECT e.exp_date
                    FROM expirations e
                    WHERE e.barcode = p.barcode
                      AND e.written_off = 0
                    ORDER BY
                        e.exp_date ASC,
                        e.id ASC
                    LIMIT 1
                ) AS next_exp

            FROM products p

            ORDER BY

                CASE
                    WHEN (
                        SELECT e2.exp_date
                        FROM expirations e2
                        WHERE e2.barcode = p.barcode
                          AND e2.written_off = 0
                        ORDER BY
                            e2.exp_date ASC,
                            e2.id ASC
                        LIMIT 1
                    ) IS NULL
                    THEN 1
                    ELSE 0
                END ASC,

                next_exp ASC,

                p.name COLLATE NOCASE ASC
            """
        ).fetchall()

    def backup_to(
        self,
        target
    ):

        target = Path(
            target
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if target.exists():

            target.unlink()

        target_conn = sqlite3.connect(
            str(
                target
            )
        )

        try:

            with target_conn:

                self.conn.backup(
                    target_conn
                )

        finally:

            target_conn.close()

    @staticmethod
    def validate(
        path
    ):

        try:

            con = sqlite3.connect(
                str(
                    path
                )
            )

            tables = {
                row[0]
                for row
                in con.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    """
                )
            }

            con.close()

            return (
                "products" in tables
                and
                "expirations" in tables
            )

        except Exception:

            return False


# =========================================================
# SCREENS
# =========================================================

class BaseScreen(Screen):

    def __init__(
        self,
        **kwargs
    ):

        super().__init__(
            **kwargs
        )

        self.app = (
            App.get_running_app()
        )


class HomeScreen(BaseScreen):

    def __init__(
        self,
        **kwargs
    ):
        super().__init__(
            **kwargs
        )
        self.filter_mode = "all"

    def on_pre_enter(
        self,
        *_
    ):

        self.refresh()

    def set_filter(
        self,
        mode
    ):
        self.filter_mode = mode
        self.refresh()

    def refresh(self):

        self.product_list.clear_widgets()

        today = date.today()

        yesterday = (
            today
            -
            timedelta(
                days=1
            )
        )

        active = []
        completed = []

        for product in (
            self.app.db.get_product_list()
        ):

            if not product[
                "next_exp"
            ]:

                completed.append(
                    product
                )

                continue

            try:

                exp_date = (
                    datetime.strptime(
                        product[
                            "next_exp"
                        ],
                        DATE_DB_FORMAT
                    ).date()
                )

            except ValueError:

                completed.append(
                    product
                )

                continue

            active.append(
                (
                    product,
                    exp_date,
                )
            )

        # Фильтр главного списка.
        # expired: дата раньше сегодняшней
        # expiring: срок сегодня
        # no_date: активного срока нет
        if self.filter_mode == "expired":
            active = [
                item
                for item in active
                if item[1] < today
            ]
            completed = []

        elif self.filter_mode == "expiring":
            active = [
                item
                for item in active
                if item[1] == today
            ]
            completed = []

        elif self.filter_mode == "no_date":
            active = []
            # completed уже содержит товары без активной даты

        for product, exp_date in active:

            self.product_list.add_widget(
                self.make_product_card(
                    product,
                    exp_date,
                    today,
                    yesterday
                )
            )

        if completed:

            separator = Label(
                text="Все сроки списаны",
                color=TEXT_SECONDARY,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
            )

            self.product_list.add_widget(
                separator
            )

            for product in completed:

                self.product_list.add_widget(
                    self.make_product_card(
                        product,
                        None,
                        today,
                        yesterday
                    )
                )

        if (
            not active
            and
            not completed
        ):

            empty = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(210),
                padding=dp(20),
            )

            empty.add_widget(
                Label(
                    text="Пока ничего нет",
                    color=TEXT,
                    bold=True,
                    font_size="20sp",
                )
            )

            empty.add_widget(
                Label(
                    text=(
                        "Отсканируй первый товар\n"
                        "и добавь его срок годности"
                    ),
                    color=TEXT_SECONDARY,
                    halign="center",
                    font_size="14sp",
                )
            )

            self.product_list.add_widget(
                empty
            )

    def make_product_card(
        self,
        product,
        exp_date,
        today,
        yesterday
    ):

        if exp_date is None:

            bg = CARD_DISABLED
            fg = TEXT_SECONDARY
            date_text = "—"

        elif exp_date == today:

            bg = YELLOW
            fg = YELLOW_TEXT

            date_text = format_date(
                product[
                    "next_exp"
                ]
            )

        elif exp_date == yesterday:

            bg = RED
            fg = RED_TEXT

            date_text = format_date(
                product[
                    "next_exp"
                ]
            )

        else:

            bg = CARD
            fg = TEXT

            date_text = format_date(
                product[
                    "next_exp"
                ]
            )

        card = ProductCard(
            product_name=(
                product[
                    "name"
                ]
                or
                "Без названия"
            ),
            barcode=(
                product[
                    "barcode"
                ]
            ),
            exp_date=date_text,
        )

        card.background_color = (
            bg
        )

        card.set_foreground(
            fg
        )

        card.bind(
            on_release=lambda *_:
            self.app.open_product(
                product[
                    "barcode"
                ]
            )
        )

        return card


class AddProductScreen(BaseScreen):

    def clear_form(self):

        self.barcode_input.text = ""
        self.name_input.text = ""
        self.date_input.text = ""

    def load_barcode(
        self,
        barcode
    ):

        barcode = normalize_barcode(
            barcode
        )

        self.barcode_input.text = (
            barcode
        )

        self.autofill_product(
            barcode
        )

        Clock.schedule_once(
            lambda *_:
            self.autofill_product(
                barcode
            ),
            0.1
        )

    def autofill_product(
        self,
        barcode=None
    ):

        if barcode is None:

            barcode = (
                self.barcode_input.text
            )

        barcode = normalize_barcode(
            barcode
        )

        if not barcode:

            return

        product = (
            self.app.db.get_product(
                barcode
            )
        )

        if not product:

            return

        name = (
            product[
                "name"
            ]
            or
            ""
        ).strip()

        if name:

            self.name_input.text = (
                name
            )

    def on_barcode_change(
        self,
        instance,
        value
    ):

        barcode = normalize_barcode(
            value
        )

        if not barcode:

            return

        Clock.schedule_once(
            lambda *_:
            self.autofill_product(
                barcode
            ),
            0.05
        )

    def save(self):

        barcode = normalize_barcode(
            self.barcode_input.text
        )

        name = (
            self.name_input.text
            .strip()
        )

        date_text = (
            self.date_input.text
            .strip()
        )

        if not barcode:

            self.app.message(
                "Введите штрихкод."
            )

            return

        if not name:

            product = (
                self.app.db.get_product(
                    barcode
                )
            )

            if product:

                name = (
                    product[
                        "name"
                    ]
                    or
                    ""
                ).strip()

                if name:

                    self.name_input.text = (
                        name
                    )

        if not name:

            self.app.message(
                "Введите название товара."
            )

            return

        exp_date = parse_user_date(
            date_text
        )

        if not exp_date:

            self.app.message(
                "Введите срок в формате ДД.ММ.ГГ.\n\n"
                "Например: 280826 → 28.08.26"
            )

            return

        existing_product = (
            self.app.db.get_product(
                barcode
            )
        )

        self.app.db.save_product(
            barcode,
            name
        )

        if existing_product:

            barcode_for_expiration = (
                existing_product[
                    "barcode"
                ]
            )

        else:

            barcode_for_expiration = (
                barcode
            )

        if not self.app.db.add_expiration(
            barcode_for_expiration,
            exp_date
        ):

            self.app.message(
                "Такой срок у этого товара уже существует."
            )

            return

        self.app.message(
            "Срок успешно добавлен."
        )

        self.app.open_home()


class ProductScreen(BaseScreen):

    barcode = StringProperty(
        ""
    )

    def load(
        self,
        barcode
    ):

        product = (
            self.app.db.get_product(
                barcode
            )
        )

        if not product:

            return

        self.barcode = (
            product[
                "barcode"
            ]
        )

        self.product_name_label.text = (
            product[
                "name"
            ]
            or
            "Без названия"
        )

        self.product_barcode_label.text = (
            "Штрихкод: "
            +
            self.barcode
        )

        active = (
            self.app.db.get_active_expirations(
                self.barcode
            )
        )

        if active:

            self.nearest_date_label.text = (
                "Годен до: "
                +
                format_date(
                    active[0][
                        "exp_date"
                    ]
                )
            )

        else:

            self.nearest_date_label.text = (
                "Активных сроков нет"
            )

        history = []

        for item in (
            self.app.db.get_all_expirations(
                self.barcode
            )
        ):

            if item[
                "written_off"
            ]:

                status = (
                    "СПИСАНО"
                )

            else:

                status = (
                    "АКТИВЕН"
                )

            history.append(
                format_date(
                    item[
                        "exp_date"
                    ]
                )
                +
                " — "
                +
                status
            )

        if history:

            self.history_label.text = (
                "\n".join(
                    history
                )
            )

        else:

            self.history_label.text = (
                "История пока пустая."
            )

        self.writeoff_button.disabled = (
            not bool(
                active
            )
        )

    def write_off(self):

        if not self.app.db.write_off_next(
            self.barcode
        ):

            self.app.message(
                "У товара нет активных сроков."
            )

            return

        next_item = (
            self.app.db.get_next_expiration(
                self.barcode
            )
        )

        if next_item:

            message = (
                "Срок списан.\n\n"
                "Следующий срок:\n"
                +
                format_date(
                    next_item[
                        "exp_date"
                    ]
                )
            )

        else:

            message = (
                "Срок списан.\n\n"
                "Активных сроков больше нет."
            )

        self.app.message(
            message
        )

        self.app.open_home()


class SettingsScreen(BaseScreen):

    pass


# =========================================================
# MAIN APP
# =========================================================

class MainApp(App):

    title = APP_TITLE

    def build(self):

        self.db_path = (
            Path(
                self.user_data_dir
            )
            /
            DB_NAME
        )

        self.db = Database(
            self.db_path
        )

        if (
            ANDROID
            and
            activity_helper is not None
        ):

            try:

                activity_helper.bind(
                    on_activity_result=
                    self._on_activity_result
                )

            except Exception as exc:

                print(
                    "activity.bind error:",
                    exc
                )

        Window.bind(
            on_keyboard=
            self._on_keyboard
        )

        manager = ScreenManager(
            transition=FadeTransition(
                duration=0.10
            )
        )

        manager.add_widget(
            self.create_home_screen()
        )

        manager.add_widget(
            self.create_add_screen()
        )

        manager.add_widget(
            self.create_product_screen()
        )

        manager.add_widget(
            self.create_settings_screen()
        )

        self.sm = manager

        return manager


    # =====================================================
    # BACK
    # =====================================================

    def _on_keyboard(
        self,
        _window,
        key,
        _scancode,
        _codepoint,
        _modifier
    ):

        if key != 27:

            return False

        if self.sm.current != "home":

            self.open_home()

            return True

        return False


    # =====================================================
    # HEADER
    # =====================================================

    def create_header(self):

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(72),
            spacing=dp(10),
            padding=(
                dp(8),
                dp(4),
            ),
        )

        logo = Image(
            source=LOGO_FILE,
            size_hint_x=None,
            width=dp(58),
            allow_stretch=True,
            keep_ratio=True,
        )

        header.add_widget(
            Widget()
        )

        header.add_widget(
            logo
        )

        title = Label(
            text=HEADER_TITLE,
            color=TEXT,
            bold=True,
            font_size="25sp",
            size_hint_x=None,
            width=dp(210),
            halign="left",
            valign="middle",
        )

        title.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        header.add_widget(
            title
        )

        header.add_widget(
            Widget()
        )

        return header


    # =====================================================
    # HOME UI
    # =====================================================

    def create_home_screen(self):

        screen = HomeScreen(
            name="home"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(
                horizontal=14,
                top=7,
                bottom=12
            ),
            spacing=dp(14),
        )

        root.add_widget(
            self.create_header()
        )

        actions = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(8),
        )

        add_button = RoundedButton(
            text="+  Добавить срок",
            font_size="16sp",
            normal_color=ACCENT_RED,
            down_color=ACCENT_RED_DOWN,
            size_hint_x=0.48,
        )

        add_button.bind(
            on_release=lambda *_:
            self.start_barcode_scanner()
        )

        settings_button = RoundedButton(
            text="Настройки",
            font_size="15sp",
            size_hint_x=0.38,
        )

        settings_button.bind(
            on_release=lambda *_:
            self.open_settings()
        )

        sort_button = RoundedButton(
            text="≡",
            font_size="25sp",
            size_hint_x=0.14,
        )

        sort_button.bind(
            on_release=lambda *_:
            self.open_sort_popup()
        )

        actions.add_widget(
            add_button
        )

        actions.add_widget(
            settings_button
        )

        actions.add_widget(
            sort_button
        )

        root.add_widget(
            actions
        )

        scroll = ScrollView(
            do_scroll_x=False,
        )

        product_list = BoxLayout(
            orientation="vertical",
            spacing=dp(11),
            padding=(
                0,
                dp(4),
                0,
                dp(10),
            ),
            size_hint_y=None,
        )

        product_list.bind(
            minimum_height=
            product_list.setter(
                "height"
            )
        )

        scroll.add_widget(
            product_list
        )

        root.add_widget(
            scroll
        )

        screen.product_list = (
            product_list
        )

        screen.add_widget(
            root
        )

        return screen


    # =====================================================
    # ADD SCREEN
    # =====================================================

    def create_add_screen(self):

        screen = AddProductScreen(
            name="add"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(
                horizontal=14,
                top=8,
                bottom=12
            ),
            spacing=dp(12),
        )

        back = RoundedButton(
            text="< Назад",
            size_hint_y=None,
            height=dp(50),
            font_size="15sp",
        )

        back.bind(
            on_release=lambda *_:
            self.open_home()
        )

        root.add_widget(
            back
        )

        root.add_widget(
            Label(
                text="Добавить срок",
                color=TEXT,
                font_size="25sp",
                bold=True,
                size_hint_y=None,
                height=dp(58),
            )
        )

        info = Label(
            text=(
                "Отсканируй штрихкод или введи его вручную.\n"
                "Для известного товара название заполнится автоматически."
            ),
            color=TEXT_SECONDARY,
            font_size="13sp",
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(74),
        )

        info.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                (
                    value[0] - dp(20),
                    None
                )
            )
        )

        root.add_widget(
            info
        )

        barcode = TextInput(
            hint_text="Штрихкод",
            multiline=False,
            size_hint_y=None,
            height=dp(56),
            font_size="18sp",
            padding=(
                dp(12),
                dp(12),
            ),
        )

        barcode.bind(
            text=
            screen.on_barcode_change
        )

        name = TextInput(
            hint_text="Наименование товара",
            multiline=False,
            size_hint_y=None,
            height=dp(56),
            font_size="18sp",
            padding=(
                dp(12),
                dp(12),
            ),
        )

        date_input = DateInput(
            hint_text="ДД.ММ.ГГ",
            multiline=False,
            input_type="number",
            size_hint_y=None,
            height=dp(56),
            font_size="18sp",
            padding=(
                dp(12),
                dp(12),
            ),
        )

        root.add_widget(
            barcode
        )

        root.add_widget(
            name
        )

        root.add_widget(
            date_input
        )

        root.add_widget(
            Widget()
        )

        save = RoundedButton(
            text="Сохранить срок",
            size_hint_y=None,
            height=dp(60),
            font_size="17sp",
            normal_color=ACCENT_RED,
            down_color=ACCENT_RED_DOWN,
        )

        save.bind(
            on_release=lambda *_:
            screen.save()
        )

        root.add_widget(
            save
        )

        screen.barcode_input = (
            barcode
        )

        screen.name_input = (
            name
        )

        screen.date_input = (
            date_input
        )

        screen.add_widget(
            root
        )

        return screen


    # =====================================================
    # PRODUCT SCREEN
    # =====================================================

    def create_product_screen(self):

        screen = ProductScreen(
            name="product"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(
                horizontal=14,
                top=8,
                bottom=12
            ),
            spacing=dp(12),
        )

        back = RoundedButton(
            text="< Назад",
            size_hint_y=None,
            height=dp(50),
        )

        back.bind(
            on_release=lambda *_:
            self.open_home()
        )

        root.add_widget(
            back
        )

        product_name = Label(
            text="Товар",
            color=TEXT,
            font_size="26sp",
            bold=True,
            size_hint_y=None,
            height=dp(58),
        )

        product_barcode = Label(
            text="Штрихкод: —",
            color=TEXT_SECONDARY,
            size_hint_y=None,
            height=dp(32),
        )

        nearest_date = Label(
            text="Годен до: —",
            color=TEXT,
            font_size="20sp",
            bold=True,
            size_hint_y=None,
            height=dp(44),
        )

        root.add_widget(
            product_name
        )

        root.add_widget(
            product_barcode
        )

        root.add_widget(
            nearest_date
        )

        root.add_widget(
            Label(
                text="История сроков",
                color=TEXT_SECONDARY,
                font_size="14sp",
                size_hint_y=None,
                height=dp(34),
            )
        )

        history_scroll = ScrollView(
            do_scroll_x=False,
        )

        history = Label(
            text="История пока пустая.",
            color=TEXT,
            halign="left",
            valign="top",
            size_hint_y=None,
        )

        history.bind(
            texture_size=lambda instance, value:
            setattr(
                instance,
                "height",
                max(
                    dp(90),
                    value[1]
                )
            )
        )

        history_scroll.add_widget(
            history
        )

        root.add_widget(
            history_scroll
        )

        writeoff = RoundedButton(
            text="Списано",
            size_hint_y=None,
            height=dp(60),
            font_size="17sp",
            normal_color=RED,
            down_color=(
                0.65,
                0.08,
                0.10,
                1,
            ),
        )

        writeoff.bind(
            on_release=lambda *_:
            screen.write_off()
        )

        root.add_widget(
            writeoff
        )

        screen.product_name_label = (
            product_name
        )

        screen.product_barcode_label = (
            product_barcode
        )

        screen.nearest_date_label = (
            nearest_date
        )

        screen.history_label = (
            history
        )

        screen.writeoff_button = (
            writeoff
        )

        screen.add_widget(
            root
        )

        return screen


    # =====================================================
    # SETTINGS
    # =====================================================

    def create_settings_screen(self):

        screen = SettingsScreen(
            name="settings"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(
                horizontal=14,
                top=8,
                bottom=12
            ),
            spacing=dp(12),
        )

        back = RoundedButton(
            text="< Назад",
            size_hint_y=None,
            height=dp(50),
        )

        back.bind(
            on_release=lambda *_:
            self.open_home()
        )

        root.add_widget(
            back
        )

        root.add_widget(
            Label(
                text="Настройки",
                color=TEXT,
                font_size="26sp",
                bold=True,
                size_hint_y=None,
                height=dp(58),
            )
        )

        root.add_widget(
            Label(
                text=(
                    "База хранится на телефоне.\n"
                    "Экспорт сохраняется в Downloads."
                ),
                color=TEXT_SECONDARY,
                font_size="14sp",
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(80),
            )
        )

        export_button = RoundedButton(
            text="Экспортировать БД",
            size_hint_y=None,
            height=dp(58),
        )

        export_button.bind(
            on_release=lambda *_:
            self.export_database()
        )

        root.add_widget(
            export_button
        )

        import_button = RoundedButton(
            text="Импортировать БД",
            size_hint_y=None,
            height=dp(58),
        )

        import_button.bind(
            on_release=lambda *_:
            self.import_database()
        )

        root.add_widget(
            import_button
        )

        clear_button = RoundedButton(
            text="Очистить БД",
            size_hint_y=None,
            height=dp(58),
            normal_color=RED,
            down_color=(
                0.65,
                0.08,
                0.10,
                1,
            ),
        )

        clear_button.bind(
            on_release=lambda *_:
            self.confirm_clear_database()
        )

        root.add_widget(
            clear_button
        )

        root.add_widget(
            Widget()
        )

        screen.add_widget(
            root
        )

        return screen


    # =====================================================
    # SORT / FILTER
    # =====================================================

    def open_sort_popup(self):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(9),
        )

        popup = Popup(
            title="Сортировка",
            content=content,
            size_hint=(
                0.88,
                0.52,
            ),
            auto_dismiss=True,
        )

        options = (
            ("Все товары", "all"),
            ("Просроченный товар", "expired"),
            ("Истекающий товар", "expiring"),
            ("Без даты", "no_date"),
        )

        home = self.sm.get_screen(
            "home"
        )

        for title, mode in options:

            button = RoundedButton(
                text=title,
                size_hint_y=None,
                height=dp(52),
                font_size="15sp",
                normal_color=(
                    ACCENT_RED
                    if home.filter_mode == mode
                    else BUTTON_BG
                ),
                down_color=(
                    ACCENT_RED_DOWN
                    if home.filter_mode == mode
                    else BUTTON_BG_DOWN
                ),
            )

            def choose(
                _button,
                selected_mode=mode
            ):
                home.set_filter(
                    selected_mode
                )
                popup.dismiss()

            button.bind(
                on_release=choose
            )

            content.add_widget(
                button
            )

        popup.open()


    # =====================================================
    # NAVIGATION
    # =====================================================

    def open_home(self):

        self.sm.current = (
            "home"
        )

        self.sm.get_screen(
            "home"
        ).refresh()

    def open_add(
        self,
        barcode=""
    ):

        self.sm.current = (
            "add"
        )

        screen = self.sm.get_screen(
            "add"
        )

        screen.clear_form()

        if barcode:

            screen.load_barcode(
                barcode
            )

        else:

            Clock.schedule_once(
                lambda *_:
                setattr(
                    screen.barcode_input,
                    "focus",
                    True
                ),
                0.1
            )

    def open_product(
        self,
        barcode
    ):

        self.sm.current = (
            "product"
        )

        self.sm.get_screen(
            "product"
        ).load(
            barcode
        )

    def open_settings(self):

        self.sm.current = (
            "settings"
        )


    # =====================================================
    # SCANNER
    # =====================================================

    def start_barcode_scanner(self):

        if not ANDROID:

            self.message(
                "Сканер доступен только на Android."
            )

            return

        if not PYJNIUS_AVAILABLE:

            self.message(
                "PyJNIus не загрузился.\n\n"
                +
                PYJNIUS_ERROR
            )

            return

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            ScannerActivity = autoclass(
                "org.example.expiringgoods."
                "BarcodeScannerActivity"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            intent = Intent(
                current_activity,
                ScannerActivity
            )

            current_activity.startActivityForResult(
                intent,
                REQUEST_SCAN_BARCODE
            )

        except Exception as exc:

            self.message(
                "Ошибка запуска сканера:\n\n"
                +
                type(exc).__name__
                +
                "\n\n"
                +
                str(exc)
            )


    # =====================================================
    # ACTIVITY RESULT
    # =====================================================

    def _on_activity_result(
        self,
        request_code,
        result_code,
        intent
    ):

        if (
            request_code
            ==
            REQUEST_SCAN_BARCODE
        ):

            self.handle_scanner_result(
                result_code,
                intent
            )

            return

        if (
            request_code
            ==
            REQUEST_IMPORT_DB
        ):

            self.handle_import_result(
                result_code,
                intent
            )

    @mainthread
    def handle_scanner_result(
        self,
        result_code,
        intent
    ):

        if result_code != -1:

            self.open_home()

            return

        if intent is None:

            self.open_home()

            return

        try:

            manual = bool(
                intent.getBooleanExtra(
                    "manual",
                    False
                )
            )

        except Exception:

            manual = False

        if manual:

            self.open_add(
                ""
            )

            return

        try:

            barcode = (
                intent.getStringExtra(
                    "barcode"
                )
            )

        except Exception:

            barcode = None

        if barcode:

            self.open_add(
                normalize_barcode(
                    barcode
                )
            )

        else:

            self.open_home()

    @mainthread
    def handle_import_result(
        self,
        result_code,
        intent
    ):

        if result_code != -1:

            return

        if intent is None:

            return

        try:

            uri = (
                intent.getData()
            )

            if uri is not None:

                self._read_database_from_uri(
                    uri
                )

        except Exception as exc:

            self.message(
                "Ошибка импорта:\n"
                +
                str(exc)
            )


    # =====================================================
    # EXPORT
    # =====================================================

    def export_database(self):

        if not ANDROID:

            self._desktop_export()

            return

        try:

            temp_db = (
                Path(
                    self.user_data_dir
                )
                /
                "inventory_export.db"
            )

            self.db.backup_to(
                temp_db
            )

            filename = (
                "pyton_date_detect_"
                +
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                +
                ".db"
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            DatabaseExportHelper = autoclass(
                "org.example.expiringgoods."
                "DatabaseExportHelper"
            )

            result = (
                DatabaseExportHelper
                .exportToDownloads(
                    current_activity,
                    str(temp_db),
                    filename
                )
            )

            try:

                temp_db.unlink()

            except OSError:

                pass

            self.message(
                "База экспортирована.\n\n"
                +
                str(result)
                +
                "\n\n"
                +
                "Папка: Downloads"
            )

        except Exception as exc:

            self.message(
                "Не удалось экспортировать БД:\n\n"
                +
                type(exc).__name__
                +
                ": "
                +
                str(exc)
            )


    # =====================================================
    # IMPORT
    # =====================================================

    def import_database(self):

        if not ANDROID:

            self.message(
                "Импорт доступен на Android."
            )

            return

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            intent = Intent(
                Intent.ACTION_OPEN_DOCUMENT
            )

            intent.addCategory(
                Intent.CATEGORY_OPENABLE
            )

            intent.setType(
                "*/*"
            )

            current_activity.startActivityForResult(
                intent,
                REQUEST_IMPORT_DB
            )

        except Exception as exc:

            self.message(
                "Ошибка открытия файла:\n\n"
                +
                str(exc)
            )

    def _read_database_from_uri(
        self,
        uri
    ):

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            resolver = (
                current_activity
                .getContentResolver()
            )

            input_stream = (
                resolver.openInputStream(
                    uri
                )
            )

            if input_stream is None:

                raise RuntimeError(
                    "Android не смог открыть файл."
                )

            temp = (
                Path(
                    self.user_data_dir
                )
                /
                "imported_inventory.db"
            )

            try:

                if temp.exists():

                    temp.unlink()

            except OSError:

                pass

            output = temp.open(
                "wb"
            )

            try:

                while True:

                    value = (
                        input_stream.read()
                    )

                    if value == -1:

                        break

                    output.write(
                        bytes(
                            (
                                value
                                &
                                0xFF,
                            )
                        )
                    )

            finally:

                output.close()
                input_stream.close()

            self._replace_database(
                temp
            )

        except Exception as exc:

            self.message(
                "Ошибка импорта:\n"
                +
                str(exc)
            )

    def _remove_sqlite_sidecars(
        self,
        db_path
    ):

        db_path = Path(
            db_path
        )

        for suffix in (
            "-wal",
            "-shm",
            "-journal",
        ):

            sidecar = Path(
                str(db_path)
                +
                suffix
            )

            try:

                if sidecar.exists():

                    sidecar.unlink()

            except OSError:

                pass

    def _replace_database(
        self,
        source
    ):

        source = Path(
            source
        )

        if not source.exists():

            self.message(
                "Файл БД не найден."
            )

            return

        if not Database.validate(
            source
        ):

            self.message(
                "Файл не является базой приложения."
            )

            return

        destination = (
            self.db_path
        )

        app_dir = (
            destination.parent
        )

        backup = (
            app_dir
            /
            "inventory_before_import.db"
        )

        replacement = (
            app_dir
            /
            "inventory_replacement.db"
        )

        try:

            self.db.backup_to(
                backup
            )

            self.db.close()

            self._remove_sqlite_sidecars(
                destination
            )

            if replacement.exists():

                replacement.unlink()

            shutil.copyfile(
                str(source),
                str(replacement)
            )

            if not Database.validate(
                replacement
            ):

                raise RuntimeError(
                    "Импортированная база повреждена."
                )

            os.replace(
                str(replacement),
                str(destination)
            )

            self._remove_sqlite_sidecars(
                destination
            )

            self.db = Database(
                destination
            )

            try:

                source.unlink()

            except OSError:

                pass

            try:

                backup.unlink()

            except OSError:

                pass

            self.message(
                "База успешно импортирована."
            )

            self.open_home()

        except Exception as exc:

            try:

                if backup.exists():

                    self._remove_sqlite_sidecars(
                        destination
                    )

                    restore_temp = (
                        app_dir
                        /
                        "inventory_restore.db"
                    )

                    try:

                        if restore_temp.exists():

                            restore_temp.unlink()

                    except OSError:

                        pass

                    shutil.copyfile(
                        str(backup),
                        str(restore_temp)
                    )

                    os.replace(
                        str(restore_temp),
                        str(destination)
                    )

                self.db = Database(
                    destination
                )

            except Exception:

                pass

            self.message(
                "Ошибка импорта:\n"
                +
                str(exc)
            )


    # =====================================================
    # CLEAR
    # =====================================================

    def confirm_clear_database(self):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
        )

        label = Label(
            text=(
                "Удалить всю базу?\n\n"
                "Будут удалены все товары и сроки.\n"
                "Это действие нельзя отменить."
            ),
            halign="center",
            valign="middle",
        )

        label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(8),
        )

        cancel = Button(
            text="Отмена"
        )

        clear = Button(
            text="Удалить всё",
            background_normal="",
            background_color=RED,
        )

        buttons.add_widget(
            cancel
        )

        buttons.add_widget(
            clear
        )

        content.add_widget(
            label
        )

        content.add_widget(
            buttons
        )

        popup = Popup(
            title=APP_TITLE,
            content=content,
            size_hint=(
                0.90,
                0.50,
            ),
            auto_dismiss=False,
        )

        cancel.bind(
            on_release=
            popup.dismiss
        )

        def do_clear(*_):

            popup.dismiss()

            self.db.clear_all()

            self.message(
                "База полностью очищена."
            )

            self.open_home()

        clear.bind(
            on_release=
            do_clear
        )

        popup.open()


    # =====================================================
    # MESSAGE
    # =====================================================

    def message(
        self,
        text
    ):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
        )

        label = Label(
            text=text,
            halign="left",
            valign="middle",
        )

        label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        ok = Button(
            text="OK",
            size_hint_y=None,
            height=dp(48),
        )

        content.add_widget(
            label
        )

        content.add_widget(
            ok
        )

        popup = Popup(
            title=APP_TITLE,
            content=content,
            size_hint=(
                0.90,
                0.55,
            ),
            auto_dismiss=False,
        )

        ok.bind(
            on_release=
            popup.dismiss
        )

        popup.open()


    # =====================================================
    # DESKTOP
    # =====================================================

    def _desktop_export(self):

        destination = (
            Path.cwd()
            /
            (
                "pyton_date_detect_"
                +
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                +
                ".db"
            )
        )

        try:

            self.db.backup_to(
                destination
            )

            self.message(
                "База сохранена:\n"
                +
                str(
                    destination
                )
            )

        except Exception as exc:

            self.message(
                "Ошибка экспорта:\n"
                +
                str(exc)
            )


    # =====================================================
    # STOP
    # =====================================================

    def on_stop(self):

        if (
            ANDROID
            and
            activity_helper is not None
        ):

            try:

                activity_helper.unbind(
                    on_activity_result=
                    self._on_activity_result
                )

            except Exception:

                pass

        try:

            Window.unbind(
                on_keyboard=
                self._on_keyboard
            )

        except Exception:

            pass

        if hasattr(
            self,
            "db"
        ):

            self.db.close()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    MainApp().run()
