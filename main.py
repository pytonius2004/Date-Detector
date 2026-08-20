# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

# ============================================================
# НАСТРОЙКИ KIVY / ANDROID
# ============================================================

# Эти настройки уже использовались в рабочей тестовой сборке.
os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")
os.environ.setdefault("KIVY_GRAPHICS", "gles")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "0")

# ============================================================
# KIVY
# ============================================================

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
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


# ============================================================
# КОНСТАНТЫ
# ============================================================

APP_TITLE = "Сроки товаров"

DATE_DB_FORMAT = "%Y-%m-%d"
DATE_USER_FORMAT = "%d.%m.%Y"


# ============================================================
# РАБОТА С ДАТАМИ
# ============================================================

def parse_user_date(value: str):
    """
    Преобразует дату пользователя в формат SQLite:

    ДД.ММ.ГГГГ
        ↓
    YYYY-MM-DD
    """

    value = value.strip()

    possible_formats = (
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    )

    for fmt in possible_formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).strftime(DATE_DB_FORMAT)

        except ValueError:
            continue

    return None


def format_date(value):
    """
    Преобразует дату из базы:

    YYYY-MM-DD
        ↓
    ДД.ММ.ГГГГ
    """

    if not value:
        return "—"

    try:
        return datetime.strptime(
            value,
            DATE_DB_FORMAT,
        ).strftime(DATE_USER_FORMAT)

    except ValueError:
        return value


# ============================================================
# SQLITE
# ============================================================

class Database:
    """
    База состоит из двух таблиц.

    products
    --------
    barcode
    name
    created_at

    expirations
    -----------
    id
    barcode
    exp_date
    written_off
    created_at

    У одного товара может быть много сроков:

    Молоко
        20.08.2026
        25.08.2026
        30.08.2026

    В главном списке показывается только:

        20.08.2026

    После списания 20.08 автоматически появляется:

        25.08.2026
    """

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

    # --------------------------------------------------------
    # СОЗДАНИЕ ТАБЛИЦ
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ЗАКРЫТИЕ БД
    # --------------------------------------------------------

    def close(self):

        self.conn.close()

    # ========================================================
    # ТОВАРЫ
    # ========================================================

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
        name,
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

    # ========================================================
    # СРОКИ
    # ========================================================

    def add_expiration(
        self,
        barcode,
        exp_date,
    ):
        """
        Добавляет новую активную дату.

        Если такая дата для данного товара
        уже существует — не добавляем её повторно.
        """

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
        barcode,
    ):
        """
        Все активные даты товара,
        начиная от ближайшей.
        """

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

    def get_all_expirations(
        self,
        barcode,
    ):
        """
        Полная история сроков.
        """

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

    def get_next_expiration(
        self,
        barcode,
    ):
        """
        Ближайший активный срок.
        """

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

    def write_off_next(
        self,
        barcode,
    ):
        """
        Списывает только ближайший активный срок.
        """

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

    # ========================================================
    # СПИСОК ТОВАРОВ
    # ========================================================

    def get_product_list(self):
        """
        Каждый товар возвращается один раз.

        next_exp:
            ближайший активный срок.

        Если активных сроков нет:
            next_exp = NULL
        """

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


# ============================================================
# БАЗОВЫЙ SCREEN
# ============================================================

class BaseScreen(Screen):

    def __init__(
        self,
        **kwargs,
    ):

        super().__init__(
            **kwargs
        )

        self.app = App.get_running_app()


# ============================================================
# ГЛАВНЫЙ ЭКРАН
# ============================================================

class HomeScreen(BaseScreen):
    """
    Главный экран.

    Сегодня:
        Жёлтый.

    Вчера:
        Красный.

    Остальные:
        Обычный.

    Нет активных сроков:
        Серый и внизу.
    """

    def on_pre_enter(
        self,
        *_args,
    ):

        self.refresh()

    def refresh(self):

        container = (
            self.ids.product_list
        )

        container.clear_widgets()

        today = date.today()

        yesterday = (
            today - timedelta(days=1)
        )

        active_products = []
        empty_products = []

        products = (
            self.app.db.get_product_list()
        )

        for product in products:

            next_exp = product["next_exp"]

            if next_exp:

                try:

                    exp_date = datetime.strptime(
                        next_exp,
                        DATE_DB_FORMAT,
                    ).date()

                except ValueError:

                    exp_date = None

                if exp_date:

                    active_products.append(
                        (
                            product,
                            exp_date,
                        )
                    )

                else:

                    empty_products.append(
                        product
                    )

            else:

                empty_products.append(
                    product
                )

        # ----------------------------------------------------
        # АКТИВНЫЕ ТОВАРЫ
        # ----------------------------------------------------

        for (
            product,
            exp_date,
        ) in active_products:

            container.add_widget(
                self.create_product_button(
                    product,
                    exp_date,
                    today,
                    yesterday,
                )
            )

        # ----------------------------------------------------
        # СЕРЫЙ БЛОК
        # ----------------------------------------------------

        if empty_products:

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
                size=lambda instance, value:
                setattr(
                    instance,
                    "text_size",
                    value,
                )
            )

            container.add_widget(
                separator
            )

            for product in empty_products:

                container.add_widget(
                    self.create_product_button(
                        product,
                        None,
                        today,
                        yesterday,
                    )
                )

        # ----------------------------------------------------
        # ПУСТАЯ БАЗА
        # ----------------------------------------------------

        if (
            not active_products
            and not empty_products
        ):

            empty_label = Label(
                text=(
                    "База пока пустая.\n\n"
                    "Нажми «+ Добавить срок»."
                ),
                size_hint_y=None,
                height=dp(130),
                halign="center",
                valign="middle",
            )

            empty_label.bind(
                size=lambda instance, value:
                setattr(
                    instance,
                    "text_size",
                    value,
                )
            )

            container.add_widget(
                empty_label
            )

    # --------------------------------------------------------
    # КНОПКА ТОВАРА
    # --------------------------------------------------------

    def create_product_button(
        self,
        product,
        exp_date,
        today,
        yesterday,
    ):

        # ----------------------------------------------------
        # СЕРЫЙ
        # ----------------------------------------------------

        if exp_date is None:

            background = (
                0.75,
                0.75,
                0.75,
                1,
            )

            foreground = (
                0.25,
                0.25,
                0.25,
                1,
            )

            status = (
                "ВСЕ СРОКИ СПИСАНЫ"
            )

        # ----------------------------------------------------
        # ЖЁЛТЫЙ — СЕГОДНЯ
        # ----------------------------------------------------

        elif exp_date == today:

            background = (
                1.0,
                0.86,
                0.20,
                1,
            )

            foreground = (
                0.10,
                0.10,
                0.10,
                1,
            )

            status = (
                "УЦЕНКА СЕГОДНЯ"
            )

        # ----------------------------------------------------
        # КРАСНЫЙ — ВЧЕРА
        # ----------------------------------------------------

        elif exp_date == yesterday:

            background = (
                0.92,
                0.20,
                0.17,
                1,
            )

            foreground = (
                1.0,
                1.0,
                1.0,
                1,
            )

            status = (
                "ИСТЁК ВЧЕРА — СПИСАНИЕ"
            )

        # ----------------------------------------------------
        # ОБЫЧНЫЙ
        # ----------------------------------------------------

        else:

            background = (
                0.94,
                0.94,
                0.94,
                1,
            )

            foreground = (
                0.12,
                0.12,
                0.12,
                1,
            )

            status = ""

        name = (
            product["name"]
            if product["name"]
            else "Без названия"
        )

        barcode = product[
            "barcode"
        ]

        shown_date = format_date(
            product["next_exp"]
        )

        text = (
            f"{name}\n"
            f"Штрихкод: {barcode}\n"
            f"Срок: {shown_date}\n"
            f"{status}"
        ).strip()

        button = Button(

            text=text,

            size_hint_y=None,

            height=dp(92),

            background_normal="",

            background_color=background,

            color=foreground,

            halign="left",

            valign="middle",

            padding=(
                dp(14),
                dp(8),
            ),
        )

        button.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                (
                    value[0] - dp(25),
                    value[1],
                ),
            )
        )

        button.bind(
            on_release=lambda *_args:
            self.app.open_product(
                barcode
            )
        )

        return button


# ============================================================
# ЭКРАН ДОБАВЛЕНИЯ
# ============================================================

class AddProductScreen(
    BaseScreen
):
    """
    Пока ручное добавление.

    Позже сюда будет передаваться
    штрихкод от камеры.
    """

    def on_enter(
        self,
        *_args,
    ):

        self.clear_form()

    def clear_form(self):

        self.ids.barcode_input.text = ""
        self.ids.name_input.text = ""
        self.ids.date_input.text = ""

    def load_barcode(
        self,
        barcode,
    ):

        self.ids.barcode_input.text = (
            barcode
        )

        product = (
            self.app.db.get_product(
                barcode
            )
        )

        if product:

            self.ids.name_input.text = (
                product["name"] or ""
            )

    def save(self):

        barcode = (
            self.ids.barcode_input.text.strip()
        )

        name = (
            self.ids.name_input.text.strip()
        )

        date_text = (
            self.ids.date_input.text.strip()
        )

        # ----------------------------------------------------
        # ПРОВЕРКИ
        # ----------------------------------------------------

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
                "Введите дату в формате "
                "ДД.ММ.ГГГГ."
            )

            return

        # ----------------------------------------------------
        # ТОВАР
        # ----------------------------------------------------

        self.app.db.save_product(
            barcode,
            name,
        )

        # ----------------------------------------------------
        # СРОК
        # ----------------------------------------------------

        added = (
            self.app.db.add_expiration(
                barcode,
                exp_date,
            )
        )

        if not added:

            self.app.message(
                "У этого товара уже есть "
                f"срок {format_date(exp_date)}."
            )

            return

        self.app.message(
            "Срок успешно добавлен."
        )

        self.app.open_home()


# ============================================================
# ЭКРАН ТОВАРА
# ============================================================

class ProductScreen(
    BaseScreen
):

    barcode = StringProperty("")

    def load(
        self,
        barcode,
    ):

        self.barcode = barcode

        product = (
            self.app.db.get_product(
                barcode
            )
        )

        if not product:
            return

        name = (
            product["name"]
            if product["name"]
            else "Без названия"
        )

        self.ids.product_name.text = (
            name
        )

        self.ids.product_barcode.text = (
            f"Штрихкод: {barcode}"
        )

        # ----------------------------------------------------
        # АКТИВНЫЕ ДАТЫ
        # ----------------------------------------------------

        active_dates = (
            self.app.db.get_active_expirations(
                barcode
            )
        )

        if active_dates:

            nearest = (
                active_dates[0]["exp_date"]
            )

            self.ids.nearest_date.text = (
                "Ближайший срок: "
                f"{format_date(nearest)}"
            )

        else:

            self.ids.nearest_date.text = (
                "Активных сроков нет"
            )

        # ----------------------------------------------------
        # ИСТОРИЯ
        # ----------------------------------------------------

        history_lines = []

        all_dates = (
            self.app.db.get_all_expirations(
                barcode
            )
        )

        for item in all_dates:

            if item["written_off"]:

                state = "СПИСАНО"

            else:

                state = "АКТИВЕН"

            history_lines.append(
                f"{format_date(item['exp_date'])}"
                f" — {state}"
            )

        if history_lines:

            self.ids.history.text = (
                "\n".join(
                    history_lines
                )
            )

        else:

            self.ids.history.text = (
                "История пока пустая."
            )

        # ----------------------------------------------------
        # КНОПКА СПИСАНИЯ
        # ----------------------------------------------------

        self.ids.writeoff_button.disabled = (
            not bool(active_dates)
        )

    # --------------------------------------------------------
    # СПИСАНИЕ
    # --------------------------------------------------------

    def write_off(self):

        success = (
            self.app.db.write_off_next(
                self.barcode
            )
        )

        if not success:

            self.app.message(
                "У товара нет активных сроков."
            )

            return

        # После списания получаем новую ближайшую дату.
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
                "Товар перейдёт "
                "в серый список."
            )

        self.app.message(
            message
        )

        self.app.open_home()


# ============================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================

class MainApp(App):

    title = APP_TITLE

    def build(self):

        # ----------------------------------------------------
        # SQLite
        # ----------------------------------------------------

        database_path = (
            Path(self.user_data_dir)
            / "inventory.db"
        )

        self.db = Database(
            database_path
        )

        # ----------------------------------------------------
        # SCREEN MANAGER
        # ----------------------------------------------------

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

        self.sm = manager

        return manager

    # ========================================================
    # ГЛАВНЫЙ ЭКРАН
    # ========================================================

    def create_home_screen(self):

        screen = HomeScreen(
            name="home"
        )

        root = BoxLayout(

            orientation="vertical",

            padding=dp(10),

            spacing=dp(8),
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = BoxLayout(

            size_hint_y=None,

            height=dp(58),

            spacing=dp(8),
        )

        title = Label(

            text=APP_TITLE,

            font_size="22sp",

            bold=True,

            halign="left",

            valign="middle",
        )

        title.bind(

            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value,
            )
        )

        add_button = Button(

            text="+ Добавить срок",

            size_hint_x=None,

            width=dp(180),
        )

        add_button.bind(

            on_release=lambda *_args:
            self.open_add("")
        )

        header.add_widget(
            title
        )

        header.add_widget(
            add_button
        )

        root.add_widget(
            header
        )

        # ----------------------------------------------------
        # СПИСОК
        # ----------------------------------------------------

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

        screen.ids = {
            "product_list": product_list
        }

        screen.add_widget(
            root
        )

        return screen

    # ========================================================
    # ЭКРАН ДОБАВЛЕНИЯ
    # ========================================================

    def create_add_screen(self):

        screen = AddProductScreen(
            name="add"
        )

        root = BoxLayout(

            orientation="vertical",

            padding=dp(12),

            spacing=dp(8),
        )

        # ----------------------------------------------------
        # НАЗАД
        # ----------------------------------------------------

        back_button = Button(

            text="← Назад",

            size_hint_y=None,

            height=dp(45),
        )

        back_button.bind(

            on_release=lambda *_args:
            self.open_home()
        )

        root.add_widget(
            back_button
        )

        # ----------------------------------------------------
        # ЗАГОЛОВОК
        # ----------------------------------------------------

        root.add_widget(

            Label(

                text="Добавить срок",

                font_size="23sp",

                bold=True,

                size_hint_y=None,

                height=dp(45),
            )
        )

        # ----------------------------------------------------
        # ПОДСКАЗКА
        # ----------------------------------------------------

        root.add_widget(

            Label(

                text=(
                    "Пока ввод вручную.\n"
                    "Камеру подключим следующим этапом."
                ),

                size_hint_y=None,

                height=dp(55),

                halign="center",

                valign="middle",
            )
        )

        # ----------------------------------------------------
        # ШТРИХКОД
        # ----------------------------------------------------

        barcode_input = TextInput(

            hint_text="Штрихкод",

            multiline=False,

            input_filter="int",

            size_hint_y=None,

            height=dp(52),
        )

        root.add_widget(
            barcode_input
        )

        # ----------------------------------------------------
        # НАЗВАНИЕ
        # ----------------------------------------------------

        name_input = TextInput(

            hint_text="Наименование товара",

            multiline=False,

            size_hint_y=None,

            height=dp(52),
        )

        root.add_widget(
            name_input
        )

        # ----------------------------------------------------
        # ДАТА
        # ----------------------------------------------------

        date_input = TextInput(

            hint_text=(
                "Срок годности ДД.ММ.ГГГГ"
            ),

            multiline=False,

            size_hint_y=None,

            height=dp(52),
        )

        root.add_widget(
            date_input
        )

        # ----------------------------------------------------
        # РАСТЯЖКА
        # ----------------------------------------------------

        root.add_widget(
            Widget()
        )

        # ----------------------------------------------------
        # СОХРАНЕНИЕ
        # ----------------------------------------------------

        save_button = Button(

            text="Сохранить срок",

            size_hint_y=None,

            height=dp(58),

            background_normal="",

            background_color=(
                0.15,
                0.58,
                0.26,
                1,
            ),
        )

        save_button.bind(

            on_release=lambda *_args:
            screen.save()
        )

        root.add_widget(
            save_button
        )

        screen.ids = {

            "barcode_input":
                barcode_input,

            "name_input":
                name_input,

            "date_input":
                date_input,
        }

        screen.add_widget(
            root
        )

        return screen

    # ========================================================
    # ЭКРАН ТОВАРА
    # ========================================================

    def create_product_screen(self):

        screen = ProductScreen(
            name="product"
        )

        root = BoxLayout(

            orientation="vertical",

            padding=dp(12),

            spacing=dp(8),
        )

        # ----------------------------------------------------
        # НАЗАД
        # ----------------------------------------------------

        back_button = Button(

            text="← Назад",

            size_hint_y=None,

            height=dp(45),
        )

        back_button.bind(

            on_release=lambda *_args:
            self.open_home()
        )

        root.add_widget(
            back_button
        )

        # ----------------------------------------------------
        # НАЗВАНИЕ
        # ----------------------------------------------------

        product_name = Label(

            text="Товар",

            font_size="24sp",

            bold=True,

            size_hint_y=None,

            height=dp(50),
        )

        root.add_widget(
            product_name
        )

        # ----------------------------------------------------
        # ШТРИХКОД
        # ----------------------------------------------------

        product_barcode = Label(

            text="Штрихкод: —",

            size_hint_y=None,

            height=dp(30),
        )

        root.add_widget(
            product_barcode
        )

        # ----------------------------------------------------
        # БЛИЖАЙШАЯ ДАТА
        # ----------------------------------------------------

        nearest_date = Label(

            text="Ближайший срок: —",

            font_size="19sp",

            bold=True,

            size_hint_y=None,

            height=dp(40),
        )

        root.add_widget(
            nearest_date
        )

        # ----------------------------------------------------
        # ИСТОРИЯ
        # ----------------------------------------------------

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

            texture_size=lambda instance, value:
            setattr(
                instance,
                "height",
                max(
                    dp(90),
                    value[1],
                ),
            )
        )

        history_scroll.add_widget(
            history
        )

        root.add_widget(
            history_scroll
        )

        # ----------------------------------------------------
        # СПИСАНО
        # ----------------------------------------------------

        writeoff_button = Button(

            text="Списано",

            size_hint_y=None,

            height=dp(60),

            background_normal="",

            background_color=(
                0.86,
                0.18,
                0.16,
                1,
            ),
        )

        writeoff_button.bind(

            on_release=lambda *_args:
            screen.write_off()
        )

        root.add_widget(
            writeoff_button
        )

        screen.ids = {

            "product_name":
                product_name,

            "product_barcode":
                product_barcode,

            "nearest_date":
                nearest_date,

            "history":
                history,

            "writeoff_button":
                writeoff_button,
        }

        screen.add_widget(
            root
        )

        return screen

    # ========================================================
    # НАВИГАЦИЯ
    # ========================================================

    def open_home(self):

        self.sm.current = "home"

        self.sm.get_screen(
            "home"
        ).refresh()

    def open_add(
        self,
        barcode="",
    ):

        self.sm.current = "add"

        screen = (
            self.sm.get_screen(
                "add"
            )
        )

        screen.clear_form()

        if barcode:

            screen.load_barcode(
                barcode
            )

    def open_product(
        self,
        barcode,
    ):

        self.sm.current = "product"

        self.sm.get_screen(
            "product"
        ).load(
            barcode
        )

    # ========================================================
    # ОКНО СООБЩЕНИЯ
    # ========================================================

    def message(
        self,
        text,
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
                value,
            )
        )

        ok_button = Button(

            text="OK",

            size_hint_y=None,

            height=dp(48),
        )

        content.add_widget(
            label
        )

        content.add_widget(
            ok_button
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

        ok_button.bind(
            on_release=popup.dismiss
        )

        popup.open()

    # ========================================================
    # ЗАКРЫТИЕ
    # ========================================================

    def on_stop(self):

        if hasattr(
            self,
            "db",
        ):

            self.db.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    MainApp().run()
