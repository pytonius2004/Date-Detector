# -*- coding: utf-8 -*-

import os
import shutil
import sqlite3

from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------
# Kivy configuration
# ---------------------------------------------------------

os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")
os.environ.setdefault("KIVY_GRAPHICS", "gles")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "0")

# ---------------------------------------------------------
# Kivy
# ---------------------------------------------------------

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

# ---------------------------------------------------------
# Android
# ---------------------------------------------------------

try:
    from android import activity
    from jnius import autoclass, jarray

    ANDROID_API_AVAILABLE = platform == "android"

except Exception:
    activity = None
    autoclass = None
    jarray = None

    ANDROID_API_AVAILABLE = False


# ---------------------------------------------------------
# Android permissions
# ---------------------------------------------------------

try:
    from android.permissions import (
        request_permissions,
        check_permission,
        Permission,
    )
except Exception:
    request_permissions = None
    check_permission = None
    Permission = None


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

APP_TITLE = "Сроки товаров"

DB_NAME = "inventory.db"

DATE_DB_FORMAT = "%Y-%m-%d"
DATE_USER_FORMAT = "%d.%m.%Y"

# Python-side request code.
# Java-side camera permission uses a different number.
REQUEST_SCAN_BARCODE = 7001

# Existing import/export request code.
REQUEST_IMPORT_DB = 4102


# =========================================================
# Date helpers
# =========================================================

def parse_user_date(value):
    value = value.strip()

    for fmt in (
        DATE_USER_FORMAT,
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(
                value,
                fmt
            ).strftime(DATE_DB_FORMAT)

        except ValueError:
            pass

    return None


def format_date(value):

    if not value:
        return "—"

    try:
        return datetime.strptime(
            value,
            DATE_DB_FORMAT
        ).strftime(DATE_USER_FORMAT)

    except ValueError:
        return value


# =========================================================
# Database
# =========================================================

class Database:

    def __init__(self, path):

        self.path = Path(path)

        self.conn = sqlite3.connect(
            str(self.path)
        )

        self.conn.row_factory = sqlite3.Row

        self.conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.create_schema()

    # -----------------------------------------------------
    # Schema
    # -----------------------------------------------------

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
            ON expirations(barcode, exp_date);

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

    # -----------------------------------------------------
    # Close
    # -----------------------------------------------------

    def close(self):

        try:
            self.conn.close()

        except Exception:
            pass

    # -----------------------------------------------------
    # Clear
    # -----------------------------------------------------

    def clear_all(self):

        self.conn.execute(
            "DELETE FROM expirations"
        )

        self.conn.execute(
            "DELETE FROM products"
        )

        self.conn.commit()

    # -----------------------------------------------------
    # Product
    # -----------------------------------------------------

    def get_product(self, barcode):

        return self.conn.execute(
            """
            SELECT *
            FROM products
            WHERE barcode = ?
            """,
            (barcode,),
        ).fetchone()

    def save_product(
        self,
        barcode,
        name
    ):

        barcode = barcode.strip()
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
                    barcode,
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

    # -----------------------------------------------------
    # Expiration
    # -----------------------------------------------------

    def add_expiration(
        self,
        barcode,
        exp_date
    ):

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

    # -----------------------------------------------------
    # Active dates
    # -----------------------------------------------------

    def get_active_expirations(
        self,
        barcode
    ):

        return self.conn.execute(
            """
            SELECT *
            FROM expirations
            WHERE barcode = ?
              AND written_off = 0
            ORDER BY exp_date ASC, id ASC
            """,
            (barcode,),
        ).fetchall()

    # -----------------------------------------------------
    # All dates
    # -----------------------------------------------------

    def get_all_expirations(
        self,
        barcode
    ):

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
            (barcode,),
        ).fetchall()

    # -----------------------------------------------------
    # Nearest
    # -----------------------------------------------------

    def get_next_expiration(
        self,
        barcode
    ):

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
            (barcode,),
        ).fetchone()

    # -----------------------------------------------------
    # Write off
    # -----------------------------------------------------

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
            (row["id"],),
        )

        self.conn.commit()

        return True

    # -----------------------------------------------------
    # Product list
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Backup
    # -----------------------------------------------------

    def backup_to(
        self,
        target
    ):

        target = Path(target)

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if target.exists():

            target.unlink()

        target_conn = sqlite3.connect(
            str(target)
        )

        try:

            with target_conn:

                self.conn.backup(
                    target_conn
                )

        finally:

            target_conn.close()

    # -----------------------------------------------------
    # Validate DB
    # -----------------------------------------------------

    @staticmethod
    def validate(path):

        try:

            con = sqlite3.connect(
                str(path)
            )

            tables = {
                row[0]

                for row in con.execute(
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
# Base Screen
# =========================================================

class BaseScreen(Screen):

    def __init__(self, **kwargs):

        super().__init__(
            **kwargs
        )

        self.app = App.get_running_app()


# =========================================================
# Home
# =========================================================

class HomeScreen(BaseScreen):

    def on_pre_enter(self, *_):

        self.refresh()

    def refresh(self):

        container = self.product_list

        container.clear_widgets()

        today = date.today()

        yesterday = (
            today -
            timedelta(days=1)
        )

        active = []
        empty = []

        for product in (
            self.app.db.get_product_list()
        ):

            next_exp = product["next_exp"]

            if not next_exp:

                empty.append(product)

                continue

            try:

                exp = datetime.strptime(
                    next_exp,
                    DATE_DB_FORMAT
                ).date()

            except ValueError:

                empty.append(product)

                continue

            active.append(
                (
                    product,
                    exp
                )
            )

        for product, exp in active:

            container.add_widget(
                self.make_product_button(
                    product,
                    exp,
                    today,
                    yesterday
                )
            )

        if empty:

            separator = Label(
                text=(
                    "[color=777777]"
                    "— ВСЕ СРОКИ СПИСАНЫ —"
                    "[/color]"
                ),
                markup=True,
                size_hint_y=None,
                height=dp(40),
                halign="center",
                valign="middle",
            )

            separator.bind(
                size=lambda i, v:
                setattr(
                    i,
                    "text_size",
                    v
                )
            )

            container.add_widget(
                separator
            )

            for product in empty:

                container.add_widget(
                    self.make_product_button(
                        product,
                        None,
                        today,
                        yesterday
                    )
                )

        if (
            not active
            and
            not empty
        ):

            label = Label(
                text=(
                    "База пока пустая.\n\n"
                    "Нажми «+ Добавить срок».\n\n"
                    "Настройки находятся в ⚙."
                ),
                size_hint_y=None,
                height=dp(140),
                halign="center",
                valign="middle",
            )

            label.bind(
                size=lambda i, v:
                setattr(
                    i,
                    "text_size",
                    v
                )
            )

            container.add_widget(
                label
            )

    def make_product_button(
        self,
        product,
        exp_date,
        today,
        yesterday
    ):

        if exp_date is None:

            bg = (
                0.75,
                0.75,
                0.75,
                1
            )

            fg = (
                0.25,
                0.25,
                0.25,
                1
            )

            status = (
                "ВСЕ СРОКИ СПИСАНЫ"
            )

        elif exp_date == today:

            bg = (
                1.0,
                0.86,
                0.20,
                1
            )

            fg = (
                0.10,
                0.10,
                0.10,
                1
            )

            status = (
                "УЦЕНКА СЕГОДНЯ"
            )

        elif exp_date == yesterday:

            bg = (
                0.92,
                0.20,
                0.17,
                1
            )

            fg = (
                1,
                1,
                1,
                1
            )

            status = (
                "ИСТЁК ВЧЕРА — СПИСАНИЕ"
            )

        else:

            bg = (
                0.94,
                0.94,
                0.94,
                1
            )

            fg = (
                0.12,
                0.12,
                0.12,
                1
            )

            status = ""

        text = (
            f"{product['name'] or 'Без названия'}\n"
            f"Штрихкод: {product['barcode']}\n"
            f"Срок: {format_date(product['next_exp'])}\n"
            f"{status}"
        ).strip()

        button = Button(
            text=text,
            size_hint_y=None,
            height=dp(92),
            background_normal="",
            background_color=bg,
            color=fg,
            halign="left",
            valign="middle",
            padding=(
                dp(14),
                dp(8)
            ),
        )

        button.bind(
            size=lambda i, v:
            setattr(
                i,
                "text_size",
                (
                    v[0] - dp(25),
                    v[1]
                )
            )
        )

        button.bind(
            on_release=lambda *_:
            self.app.open_product(
                product["barcode"]
            )
        )

        return button


# =========================================================
# Add product
# =========================================================

class AddProductScreen(BaseScreen):

    def on_pre_enter(self, *_):

        # The screen is cleared only when explicitly
        # opened without a barcode.
        pass

    def clear_form(self):

        self.barcode_input.text = ""
        self.name_input.text = ""
        self.date_input.text = ""

    def load_barcode(
        self,
        barcode
    ):

        barcode = barcode.strip()

        self.barcode_input.text = barcode

        self.autofill_product(
            barcode
        )

    def autofill_product(
        self,
        barcode=None
    ):

        if barcode is None:

            barcode = (
                self.barcode_input.text
            )

        barcode = barcode.strip()

        if not barcode:

            return

        product = self.app.db.get_product(
            barcode
        )

        if product:

            saved_name = (
                product["name"] or ""
            )

            if saved_name:

                self.name_input.text = (
                    saved_name
                )

    def save(self):

        barcode = (
            self.barcode_input.text
            .strip()
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

            self.app.message(
                "Введите название товара."
            )

            return

        exp_date = parse_user_date(
            date_text
        )

        if not exp_date:

            self.app.message(
                "Введите дату в формате ДД.ММ.ГГГГ."
            )

            return

        # This also updates the existing
        # product name when needed.
        self.app.db.save_product(
            barcode,
            name
        )

        if not self.app.db.add_expiration(
            barcode,
            exp_date
        ):

            self.app.message(
                "У этого товара уже есть "
                f"срок {format_date(exp_date)}."
            )

            return

        self.app.message(
            "Срок успешно добавлен.\n\n"
            "В списке показывается только "
            "ближайший активный срок."
        )

        self.app.open_home()


# =========================================================
# Product details
# =========================================================

class ProductScreen(BaseScreen):

    barcode = StringProperty("")

    def load(
        self,
        barcode
    ):

        self.barcode = barcode

        product = (
            self.app.db.get_product(
                barcode
            )
        )

        if not product:

            return

        self.product_name_label.text = (
            product["name"]
            or
            "Без названия"
        )

        self.product_barcode_label.text = (
            f"Штрихкод: {barcode}"
        )

        active = (
            self.app.db.get_active_expirations(
                barcode
            )
        )

        if active:

            self.nearest_date_label.text = (
                "Ближайший срок: "
                +
                format_date(
                    active[0]["exp_date"]
                )
            )

        else:

            self.nearest_date_label.text = (
                "Активных сроков нет"
            )

        history = []

        for item in (
            self.app.db.get_all_expirations(
                barcode
            )
        ):

            state = (
                "СПИСАНО"
                if item["written_off"]
                else
                "АКТИВЕН"
            )

            history.append(
                f"{format_date(item['exp_date'])}"
                f" — {state}"
            )

        self.history_label.text = (
            "\n".join(history)
            if history
            else
            "История пока пустая."
        )

        self.writeoff_button.disabled = (
            not bool(active)
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
                f"{format_date(next_item['exp_date'])}"
            )

        else:

            message = (
                "Срок списан.\n\n"
                "Активных сроков больше нет.\n\n"
                "Товар перейдёт в серый список."
            )

        self.app.message(
            message
        )

        self.app.open_home()


# =========================================================
# Settings
# =========================================================

class SettingsScreen(BaseScreen):

    pass


# =========================================================
# Application
# =========================================================

class MainApp(App):

    title = APP_TITLE

    def build(self):

        self.db_path = (
            Path(self.user_data_dir)
            /
            DB_NAME
        )

        self.db = Database(
            self.db_path
        )

        self._pending_import_path = None

        # Android activity-result callback.
        if (
            ANDROID_API_AVAILABLE
            and
            activity is not None
        ):

            try:

                activity.bind(
                    on_activity_result=
                    self._on_activity_result
                )

            except Exception:
                pass

        Window.bind(
            on_keyboard=self._on_keyboard
        )

        manager = ScreenManager(
            transition=FadeTransition(
                duration=0.08
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
    # Android back
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
    # HOME SCREEN
    # =====================================================

    def create_home_screen(self):

        screen = HomeScreen(
            name="home"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        header = BoxLayout(
            size_hint_y=None,
            height=dp(58),
            spacing=dp(7)
        )

        title = Label(
            text=APP_TITLE,
            font_size="22sp",
            bold=True,
            halign="left",
            valign="middle",
        )

        title.bind(
            size=lambda i, v:
            setattr(
                i,
                "text_size",
                v
            )
        )

        add_button = Button(
            text="+ Добавить срок",
            size_hint_x=None,
            width=dp(175),
        )

        add_button.bind(
            on_release=lambda *_:
            self.start_barcode_scanner()
        )

        settings_button = Button(
            text="⚙",
            font_size="24sp",
            size_hint_x=None,
            width=dp(58),
        )

        settings_button.bind(
            on_release=lambda *_:
            self.open_settings()
        )

        header.add_widget(
            title
        )

        header.add_widget(
            add_button
        )

        header.add_widget(
            settings_button
        )

        root.add_widget(
            header
        )

        scroll = ScrollView()

        product_list = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
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
            padding=dp(12),
            spacing=dp(8)
        )

        back = Button(
            text="← Назад",
            size_hint_y=None,
            height=dp(45)
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
                font_size="23sp",
                bold=True,
                size_hint_y=None,
                height=dp(45),
            )
        )

        barcode = TextInput(
            hint_text="Штрихкод",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            input_type="text",
        )

        barcode.bind(
            text=lambda instance, value:
            screen.autofill_product(
                value
            )
        )

        name = TextInput(
            hint_text="Наименование товара",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
        )

        exp_date = TextInput(
            hint_text="Срок годности ДД.ММ.ГГГГ",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            input_type="number",
        )

        root.add_widget(
            Label(
                text=(
                    "Штрихкод можно отсканировать "
                    "или изменить вручную.\n"
                    "Если товар уже есть в базе, "
                    "название заполнится автоматически."
                ),
                size_hint_y=None,
                height=dp(70),
                halign="center",
                valign="middle",
            )
        )

        root.add_widget(
            barcode
        )

        root.add_widget(
            name
        )

        root.add_widget(
            exp_date
        )

        root.add_widget(
            Widget()
        )

        save = Button(
            text="Сохранить срок",
            size_hint_y=None,
            height=dp(58),
            background_normal="",
            background_color=(
                0.15,
                0.58,
                0.26,
                1
            ),
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
            exp_date
        )

        screen.add_widget(
            root
        )

        return screen

    # =====================================================
    # PRODUCT
    # =====================================================

    def create_product_screen(self):

        screen = ProductScreen(
            name="product"
        )

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        back = Button(
            text="← Назад",
            size_hint_y=None,
            height=dp(45)
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
            font_size="24sp",
            bold=True,
            size_hint_y=None,
            height=dp(50),
        )

        product_barcode = Label(
            text="Штрихкод: —",
            size_hint_y=None,
            height=dp(30),
        )

        nearest_date = Label(
            text="Ближайший срок: —",
            font_size="19sp",
            bold=True,
            size_hint_y=None,
            height=dp(40),
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
                bold=True,
                size_hint_y=None,
                height=dp(32),
            )
        )

        history_scroll = ScrollView()

        history = Label(
            text="История пока пустая.",
            halign="left",
            valign="top",
            size_hint_y=None,
        )

        history.bind(
            texture_size=lambda i, v:
            setattr(
                i,
                "height",
                max(
                    dp(90),
                    v[1]
                )
            )
        )

        history_scroll.add_widget(
            history
        )

        root.add_widget(
            history_scroll
        )

        writeoff = Button(
            text="Списано",
            size_hint_y=None,
            height=dp(60),
            background_normal="",
            background_color=(
                0.86,
                0.18,
                0.16,
                1
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
            padding=dp(12),
            spacing=dp(10)
        )

        back = Button(
            text="← Назад",
            size_hint_y=None,
            height=dp(45)
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
                text="Настройки базы",
                font_size="23sp",
                bold=True,
                size_hint_y=None,
                height=dp(55),
            )
        )

        root.add_widget(
            Label(
                text=(
                    "База хранится локально на телефоне.\n\n"
                    "Экспорт будет сохраняться в папку Downloads."
                ),
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(90),
            )
        )

        export_btn = Button(
            text="Экспортировать БД",
            size_hint_y=None,
            height=dp(58),
        )

        export_btn.bind(
            on_release=lambda *_:
            self.export_database()
        )

        root.add_widget(
            export_btn
        )

        import_btn = Button(
            text="Импортировать БД",
            size_hint_y=None,
            height=dp(58),
        )

        import_btn.bind(
            on_release=lambda *_:
            self.import_database()
        )

        root.add_widget(
            import_btn
        )

        clear_btn = Button(
            text="Очистить БД",
            size_hint_y=None,
            height=dp(58),
            background_normal="",
            background_color=(
                0.86,
                0.18,
                0.16,
                1
            ),
        )

        clear_btn.bind(
            on_release=lambda *_:
            self.confirm_clear_database()
        )

        root.add_widget(
            clear_btn
        )

        root.add_widget(
            Widget()
        )

        screen.add_widget(
            root
        )

        return screen

    # =====================================================
    # Navigation
    # =====================================================

    def open_home(self):

        self.sm.current = "home"

        self.sm.get_screen(
            "home"
        ).refresh()

    def open_add(
        self,
        barcode=""
    ):

        self.sm.current = "add"

        screen = self.sm.get_screen(
            "add"
        )

        screen.clear_form()

        if barcode:

            screen.load_barcode(
                barcode
            )

    def open_product(
        self,
        barcode
    ):

        self.sm.current = "product"

        self.sm.get_screen(
            "product"
        ).load(
            barcode
        )

    def open_settings(self):

        self.sm.current = "settings"

    # =====================================================
    # NATIVE BARCODE SCANNER
    # =====================================================

    def start_barcode_scanner(self):

        if not ANDROID_API_AVAILABLE:

            self.message(
                "Сканер штрихкода доступен "
                "только на Android."
            )

            return

        try:

            BarcodeScannerActivity = (
                autoclass(
                    "org.example.expiringgoods."
                    "BarcodeScannerActivity"
                )
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            intent = Intent(
                activity,
                BarcodeScannerActivity
            )

            activity.startActivityForResult(
                intent,
                REQUEST_SCAN_BARCODE
            )

        except Exception as exc:

            self.message(
                "Не удалось открыть сканер:\n\n"
                + str(exc)
            )

    # =====================================================
    # Android activity result
    # =====================================================

    def _on_activity_result(
        self,
        request_code,
        result_code,
        intent
    ):

        # RESULT_OK == -1
        if (
            request_code
            ==
            REQUEST_SCAN_BARCODE
        ):

            if result_code != -1:

                return

            if intent is None:

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

                barcode = str(
                    barcode
                ).strip()

                self.open_add(
                    barcode
                )

            return

        if (
            request_code
            ==
            REQUEST_IMPORT_DB
        ):

            if result_code != -1:

                return

            if intent is None:

                return

            try:

                uri = intent.getData()

                if uri:

                    self._read_database_from_uri(
                        uri
                    )

            except Exception as exc:

                self.message(
                    "Ошибка импорта:\n"
                    + str(exc)
                )

    # =====================================================
    # EXPORT DATABASE TO DOWNLOADS
    # =====================================================

    def export_database(self):

        if not ANDROID_API_AVAILABLE:

            self._desktop_export()

            return

        try:

            Build = autoclass(
                "android.os.Build"
            )

            sdk_int = int(
                Build.VERSION.SDK_INT
            )

        except Exception:

            sdk_int = 30

        try:

            temp_db = (
                Path(self.user_data_dir)
                /
                "inventory_export.db"
            )

            self.db.backup_to(
                temp_db
            )

            filename = (
                "inventory_"
                +
                date.today().strftime(
                    "%Y%m%d"
                )
                +
                ".db"
            )

            # Android 10+:
            # MediaStore can create files directly
            # in public Downloads without asking for
            # broad storage permission.
            if sdk_int >= 29:

                self._export_to_downloads_media_store(
                    temp_db,
                    filename
                )

            else:

                self._export_to_legacy_downloads(
                    temp_db,
                    filename
                )

        except Exception as exc:

            self.message(
                "Не удалось экспортировать БД:\n\n"
                + str(exc)
            )

    def _export_to_downloads_media_store(
        self,
        source,
        filename
    ):

        ContentValues = autoclass(
            "android.content.ContentValues"
        )

        MediaStore = autoclass(
            "android.provider.MediaStore"
        )

        values = ContentValues()

        values.put(
            "_display_name",
            filename
        )

        values.put(
            "mime_type",
            "application/octet-stream"
        )

        values.put(
            "relative_path",
            "Download/"
        )

        values.put(
            "is_pending",
            1
        )

        resolver = (
            activity.getContentResolver()
        )

        collection = (
            MediaStore.Downloads
            .EXTERNAL_CONTENT_URI
        )

        uri = resolver.insert(
            collection,
            values
        )

        if uri is None:

            raise RuntimeError(
                "Android не смог создать файл "
                "в папке Downloads."
            )

        output_stream = (
            resolver.openOutputStream(
                uri
            )
        )

        if output_stream is None:

            raise RuntimeError(
                "Android не смог открыть "
                "файл для записи."
            )

        try:

            data = (
                Path(source).read_bytes()
            )

            output_stream.write(
                jarray("b")(data)
            )

            output_stream.flush()

        finally:

            output_stream.close()

        # Mark the file as ready/public.
        completed_values = (
            ContentValues()
        )

        completed_values.put(
            "is_pending",
            0
        )

        resolver.update(
            uri,
            completed_values,
            None,
            None
        )

        try:

            Path(source).unlink()

        except OSError:

            pass

        self.message(
            "База экспортирована.\n\n"
            f"Файл:\n{filename}\n\n"
            "Папка: Downloads"
        )

    def _export_to_legacy_downloads(
        self,
        source,
        filename
    ):

        Environment = autoclass(
            "android.os.Environment"
        )

        downloads_dir = (
            Environment
            .getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            )
        )

        downloads_path = Path(
            str(downloads_dir)
        )

        downloads_path.mkdir(
            parents=True,
            exist_ok=True
        )

        destination = (
            downloads_path
            /
            filename
        )

        shutil.copy2(
            source,
            destination
        )

        try:

            Path(source).unlink()

        except OSError:

            pass

        self.message(
            "База экспортирована.\n\n"
            "Папка: Downloads"
        )

    # =====================================================
    # IMPORT DATABASE
    # =====================================================

    def import_database(self):

        if not ANDROID_API_AVAILABLE:

            self._desktop_import_message()

            return

        try:

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
                "application/octet-stream"
            )

            activity.startActivityForResult(
                intent,
                REQUEST_IMPORT_DB
            )

        except Exception as exc:

            self.message(
                "Не удалось открыть "
                "выбор файла:\n"
                + str(exc)
            )

    def _read_database_from_uri(
        self,
        uri
    ):

        resolver = (
            activity.getContentResolver()
        )

        input_stream = (
            resolver.openInputStream(
                uri
            )
        )

        if input_stream is None:

            self.message(
                "Android не смог открыть "
                "выбранный файл."
            )

            return

        temp = (
            Path(self.user_data_dir)
            /
            "imported_inventory.db"
        )

        try:

            output = temp.open(
                "wb"
            )

            try:

                buffer = jarray(
                    "b"
                )(
                    [0] * 8192
                )

                while True:

                    count = (
                        input_stream.read(
                            buffer
                        )
                    )

                    if count <= 0:

                        break

                    output.write(
                        bytes(
                            (
                                x & 0xFF
                            )
                            for x
                            in buffer[:count]
                        )
                    )

            finally:

                output.close()
                input_stream.close()

            self._replace_database(
                temp
            )

        except Exception as exc:

            try:
                temp.unlink()
            except OSError:
                pass

            self.message(
                "Ошибка импорта:\n"
                + str(exc)
            )

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
                "Этот файл не похож "
                "на базу приложения."
            )

            try:
                source.unlink()
            except OSError:
                pass

            return

        destination = self.db_path

        backup = (
            Path(self.user_data_dir)
            /
            "inventory_before_import.db"
        )

        try:

            self.db.backup_to(
                backup
            )

            self.db.close()

            shutil.copy2(
                source,
                destination
            )

            self.db = Database(
                destination
            )

            try:
                backup.unlink()
            except OSError:
                pass

            try:
                source.unlink()
            except OSError:
                pass

            self.message(
                "База успешно импортирована."
            )

            self.open_home()

        except Exception as exc:

            try:

                if backup.exists():

                    shutil.copy2(
                        backup,
                        destination
                    )

                    self.db = Database(
                        destination
                    )

            except Exception:
                pass

            self.message(
                "Импорт не удался:\n"
                + str(exc)
            )

    # =====================================================
    # Desktop fallback
    # =====================================================

    def _desktop_export(self):

        destination = (
            Path.cwd()
            /
            (
                "inventory_"
                +
                date.today().strftime(
                    "%Y%m%d"
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
                str(destination)
            )

        except Exception as exc:

            self.message(
                "Ошибка экспорта:\n"
                + str(exc)
            )

    def _desktop_import_message(self):

        self.message(
            "Импорт через системный "
            "выбор файла настроен "
            "для Android."
        )

    # =====================================================
    # Clear database
    # =====================================================

    def confirm_clear_database(
        self
    ):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
        )

        label = Label(
            text=(
                "ВНИМАНИЕ!\n\n"
                "Будут удалены все товары "
                "и все сроки.\n\n"
                "Это действие нельзя отменить."
            ),
            halign="center",
            valign="middle",
        )

        label.bind(
            size=lambda i, v:
            setattr(
                i,
                "text_size",
                v
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
            background_color=(
                0.86,
                0.18,
                0.16,
                1
            ),
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
            title="Очистить БД",
            content=content,
            size_hint=(
                0.9,
                0.55
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
            on_release=do_clear
        )

        popup.open()

    # =====================================================
    # Message
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
            size=lambda i, v:
            setattr(
                i,
                "text_size",
                v
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
                0.9,
                0.55
            ),
            auto_dismiss=False,
        )

        ok.bind(
            on_release=
            popup.dismiss
        )

        popup.open()

    # =====================================================
    # Stop
    # =====================================================

    def on_stop(self):

        if (
            ANDROID_API_AVAILABLE
            and
            activity is not None
        ):

            try:

                activity.unbind(
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
# Start
# =========================================================

if __name__ == "__main__":

    MainApp().run()
