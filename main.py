# -*- coding: utf-8 -*-

import os
import shutil
import sqlite3
import json

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
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
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

PURPLE = (
    0.46,
    0.25,
    0.68,
    1,
)

PURPLE_DOWN = (
    0.36,
    0.18,
    0.56,
    1,
)


# Настраиваемые цвета статусов товаров.
# Значения по умолчанию повторяют текущую цветовую схему приложения.
DEFAULT_STATUS_COLORS = {
    "expired": RED,        # просрочено / списать
    "today": YELLOW,       # истекает сегодня / уценить
    "tomorrow": GREEN,     # истекает завтра
    "no_date": PURPLE,     # без даты
    "normal": CARD,        # остальные товары
}

STATUS_COLOR_LABELS = {
    "expired": "Просрочено / списать",
    "today": "Истекает сегодня / уценить",
    "tomorrow": "Истекает завтра",
    "no_date": "Без даты",
    "normal": "Остальные товары",
}

# Палитра, из которой пользователь может выбрать цвет прямо в приложении.
# Это надёжнее системного Android color picker и не требует новых зависимостей.
STATUS_COLOR_PALETTE = [
    # Основные
    (0.82, 0.12, 0.13, 1),   # красный
    (1.00, 0.78, 0.13, 1),   # жёлтый
    (0.13, 0.57, 0.27, 1),   # зелёный
    (0.46, 0.25, 0.68, 1),   # фиолетовый
    (0.12, 0.45, 0.78, 1),   # синий
    (0.08, 0.63, 0.68, 1),   # бирюзовый
    (0.93, 0.39, 0.10, 1),   # оранжевый
    (0.72, 0.23, 0.55, 1),   # малиновый

    # Дополнительные / светлые
    (0.96, 0.38, 0.40, 1),   # светло-красный
    (1.00, 0.88, 0.42, 1),   # светло-жёлтый
    (0.39, 0.76, 0.49, 1),   # светло-зелёный
    (0.67, 0.48, 0.84, 1),   # светло-фиолетовый
    (0.42, 0.68, 0.92, 1),   # светло-синий
    (0.39, 0.79, 0.82, 1),   # светло-бирюзовый
    (1.00, 0.62, 0.30, 1),   # светло-оранжевый
    (0.88, 0.47, 0.72, 1),   # светло-розовый

    # Нейтральные
    (1.00, 1.00, 1.00, 1),   # белый
    (0.76, 0.77, 0.80, 1),   # светло-серый
    (0.30, 0.31, 0.35, 1),   # серый
    (0.10, 0.105, 0.12, 1),  # почти чёрный
]

DEFAULT_STATUS_TEXT_COLORS = {
    key: readable
    for key, readable in {
        "expired": TEXT,
        "today": (0.08, 0.08, 0.08, 1),
        "tomorrow": TEXT,
        "no_date": TEXT,
        "normal": TEXT,
    }.items()
}



def readable_text_color(background):
    """Возвращает белый или почти чёрный текст для выбранного фона."""
    try:
        r, g, b = background[:3]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return YELLOW_TEXT if luminance > 0.64 else TEXT
    except Exception:
        return TEXT

THUMBNAIL_BG = (
    0.28,
    0.29,
    0.32,
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
BUILD_MARKER = "polish_edit_multi_exp_purple_v12"

HEADER_TITLE = "Pyton Detector"

LOGO_FILE = "logo1.png"

DB_NAME = "inventory.db"

DATE_DB_FORMAT = "%Y-%m-%d"
DATE_USER_FORMAT = "%d.%m.%y"

REQUEST_SCAN_BARCODE = 7001
REQUEST_IMPORT_DB = 4102
REQUEST_PICK_PRODUCT_PHOTO = 7201
REQUEST_TAKE_PRODUCT_PHOTO = 7202

DEPARTMENTS = (
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
)


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

    def set_foreground(self, color):
        # Унифицированный метод для кнопок-предпросмотров цвета.
        self.color = list(color)


class ColorSwatch(ButtonBehavior, Widget):

    swatch_color = ListProperty((1, 1, 1, 1))
    selected = BooleanProperty(False)

    def __init__(self, swatch_color=(1, 1, 1, 1), selected=False, **kwargs):
        super().__init__(**kwargs)

        self.swatch_color = list(swatch_color)
        self.selected = bool(selected)

        with self.canvas.before:
            self._shadow_color = Color(0, 0, 0, 0.20)
            self._shadow = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(15)],
            )

            self._fill_color = Color(*self.swatch_color)
            self._fill = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(15)],
            )

        with self.canvas.after:
            # Белый круг выбора.
            self._selected_circle_color = Color(1, 1, 1, 0)
            self._selected_circle = Ellipse(
                pos=self.pos,
                size=(dp(25), dp(25)),
            )

            # Галочка рисуется линиями, поэтому не зависит от шрифтов Android.
            self._check_color = Color(0.08, 0.08, 0.08, 0)
            self._check_line = Line(
                points=[],
                width=dp(2.0),
                cap="round",
                joint="round",
            )

        self.bind(
            pos=self._update_swatch,
            size=self._update_swatch,
            swatch_color=self._update_swatch,
            selected=self._update_swatch,
        )

        self._update_swatch()

    def _update_swatch(self, *_):
        self._shadow.pos = (self.x, self.y - dp(1))
        self._shadow.size = self.size

        self._fill.pos = self.pos
        self._fill.size = self.size
        self._fill_color.rgba = tuple(self.swatch_color)

        indicator = min(dp(27), self.height * 0.42)
        ix = self.right - indicator - dp(6)
        iy = self.top - indicator - dp(6)

        self._selected_circle.pos = (ix, iy)
        self._selected_circle.size = (indicator, indicator)

        if self.selected:
            self._selected_circle_color.rgba = (1, 1, 1, 0.98)

            x0 = ix + indicator * 0.25
            y0 = iy + indicator * 0.50
            x1 = ix + indicator * 0.43
            y1 = iy + indicator * 0.31
            x2 = ix + indicator * 0.76
            y2 = iy + indicator * 0.70

            self._check_color.rgba = (0.08, 0.08, 0.08, 1)
            self._check_line.points = [x0, y0, x1, y1, x2, y2]
        else:
            self._selected_circle_color.rgba = (1, 1, 1, 0)
            self._check_color.rgba = (0.08, 0.08, 0.08, 0)
            self._check_line.points = []


class RoundedTextInput(TextInput):

    def __init__(self, **kwargs):

        requested_hint = kwargs.pop(
            "hint_text",
            ""
        )

        requested_hint_color = kwargs.pop(
            "hint_text_color",
            TEXT
        )

        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_active = ""
        self.background_color = (
            0,
            0,
            0,
            0,
        )

        self.foreground_color = TEXT
        self.cursor_color = TEXT
        self.write_tab = False

        # Не используем стандартный hint_text Kivy.
        # На некоторых Android-сборках он есть логически,
        # но визуально вообще не рисуется.
        self.hint_text = ""

        self._placeholder_text = str(
            requested_hint or ""
        )

        self._placeholder_color = tuple(
            requested_hint_color
        )

        self._placeholder_core = None

        with self.canvas.before:

            self._search_bg_color = Color(
                *CARD
            )

            self._search_bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[
                    dp(18)
                ],
            )

        # Рисуем placeholder ПОСЛЕ внутреннего canvas TextInput,
        # поэтому Android/Kivy уже не может закрыть его фоном поля.
        with self.canvas.after:

            self._placeholder_canvas_color = Color(
                1,
                1,
                1,
                0,
            )

            self._placeholder_rect = Rectangle(
                pos=self.pos,
                size=(0, 0),
            )

        self.bind(
            pos=self._update_search_visuals,
            size=self._update_search_visuals,
            padding=self._update_search_visuals,
            font_size=self._update_search_visuals,
            focus=self._update_search_visuals,
            text=self._update_search_visuals,
        )

        Clock.schedule_once(
            self._update_search_visuals,
            0,
        )

    def _update_search_visuals(
        self,
        *_
    ):

        self._search_bg.pos = self.pos
        self._search_bg.size = self.size

        # Как в обычных приложениях:
        # placeholder виден только когда поле ПУСТОЕ и НЕ в фокусе.
        visible = (
            (not self.focus)
            and
            (not self.text)
            and
            bool(self._placeholder_text)
        )

        if not visible:

            self._placeholder_canvas_color.rgba = (
                1,
                1,
                1,
                0,
            )

            self._placeholder_rect.texture = None
            self._placeholder_rect.size = (
                0,
                0,
            )

            return

        try:

            rgba = tuple(
                float(x)
                for x in self._placeholder_color[:4]
            )

        except Exception:

            rgba = TEXT

        # CoreLabel создаёт обычную текстуру текста.
        # Это намного надёжнее child-Label внутри TextInput на Android.
        self._placeholder_core = CoreLabel(
            text=self._placeholder_text,
            font_size=self.font_size,
            color=rgba,
        )

        self._placeholder_core.refresh()

        texture = (
            self._placeholder_core.texture
        )

        if texture is None:
            return

        try:

            pad = self.padding

            if isinstance(
                pad,
                (tuple, list)
            ):

                pad_x = (
                    float(pad[0])
                    if len(pad) >= 1
                    else dp(15)
                )

            else:

                pad_x = float(
                    pad or dp(15)
                )

        except Exception:

            pad_x = dp(15)

        tex_w, tex_h = texture.size

        x = (
            self.x
            +
            pad_x
        )

        y = (
            self.y
            +
            max(
                0,
                (
                    self.height
                    -
                    tex_h
                )
                /
                2
            )
        )

        self._placeholder_canvas_color.rgba = (
            1,
            1,
            1,
            1,
        )

        self._placeholder_rect.texture = (
            texture
        )

        self._placeholder_rect.pos = (
            x,
            y,
        )

        self._placeholder_rect.size = (
            tex_w,
            tex_h,
        )

    def set_placeholder(
        self,
        text
    ):

        self._placeholder_text = str(
            text or ""
        )

        self._update_search_visuals()


class RoundedPanel(BoxLayout):

    def __init__(
        self,
        bg_color=(0.12, 0.13, 0.15, 1),
        radius=24,
        **kwargs
    ):
        super().__init__(**kwargs)

        with self.canvas.before:
            self._panel_color = Color(*bg_color)
            self._panel_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(radius)],
            )

        self.bind(
            pos=self._update_panel_canvas,
            size=self._update_panel_canvas,
        )

    def _update_panel_canvas(self, *_):
        self._panel_rect.pos = self.pos
        self._panel_rect.size = self.size


# =========================================================
# PRODUCT CARD
# =========================================================

class RoundedImageButton(ButtonBehavior, BoxLayout):

    image_source = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(13)

        with self.canvas.before:
            self._bg_color = Color(*BUTTON_BG)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(18)]
            )

        self.bind(
            pos=self._update_bg,
            size=self._update_bg,
            state=self._update_state,
        )

        self._icon = Image(
            source=self.image_source,
            fit_mode="contain",
        )
        self.add_widget(self._icon)

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_state(self, *_):
        self._bg_color.rgba = (
            BUTTON_BG_DOWN
            if self.state == "down"
            else BUTTON_BG
        )


class ProductThumbnail(BoxLayout):

    def __init__(
        self,
        source="",
        remote_source="",
        thumb_width=84,
        thumb_height=92,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.size_hint = (None, None)
        self.width = dp(thumb_width)
        self.height = dp(thumb_height)
        self.padding = 0
        self._has_image = False

        with self.canvas.before:
            self._bg_color = Color(
                *THUMBNAIL_BG
            )
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(14)],
            )

        self.bind(
            pos=self._update_bg,
            size=self._update_bg,
        )

        local_source = str(
            source or ""
        ).strip()

        remote_source = str(
            remote_source or ""
        ).strip()

        if (
            local_source
            and
            Path(local_source).exists()
        ):
            self._has_image = True
            self._bg_color.rgba = (0, 0, 0, 0)
            self.add_widget(
                Image(
                    source=local_source,
                    fit_mode="contain",
                )
            )
            return

        if remote_source.startswith(
            ("http://", "https://")
        ):
            self._has_image = True
            self._bg_color.rgba = (0, 0, 0, 0)
            self.add_widget(
                AsyncImage(
                    source=remote_source,
                    fit_mode="contain",
                    nocache=False,
                )
            )
            return

        self.add_widget(
            Label(
                text="",
                color=TEXT_SECONDARY,
            )
        )

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class ProductCard(
    ButtonBehavior,
    BoxLayout
):

    background_color = ListProperty(CARD)
    foreground_color = ListProperty(TEXT)

    def __init__(
        self,
        product_name,
        barcode,
        exp_date,
        photo_path="",
        photo_url="",
        **kwargs
    ):
        super().__init__(**kwargs)

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(116)
        self.padding = (dp(12), dp(12))
        self.spacing = dp(11)

        with self.canvas.before:
            self._bg_color = Color(
                *self.background_color
            )
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(17)],
            )

        self.bind(
            pos=self._update_card,
            size=self._update_card,
            background_color=self._update_color,
        )

        thumb_holder = AnchorLayout(
            size_hint_x=None,
            width=dp(90),
            anchor_x="center",
            anchor_y="center",
        )

        self.thumbnail = ProductThumbnail(
            source=photo_path,
            remote_source=photo_url,
            thumb_width=84,
            thumb_height=92,
        )

        thumb_holder.add_widget(
            self.thumbnail
        )

        self.add_widget(
            thumb_holder
        )

        left = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
        )

        self.name_label = Label(
            text=product_name or "Без названия",
            color=self.foreground_color,
            bold=True,
            font_size="17sp",
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(52),
        )

        self.barcode_label = Label(
            text=f"Штрихкод: {barcode}",
            color=self.foreground_color,
            font_size="12sp",
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(30),
        )

        self.name_label.bind(
            width=self._sync_name_width,
            texture_size=self._update_dynamic_height,
        )

        self.barcode_label.bind(
            width=self._sync_barcode_width,
        )

        left.add_widget(
            self.name_label
        )
        left.add_widget(
            self.barcode_label
        )

        right = BoxLayout(
            orientation="vertical",
            size_hint_x=0.34,
        )

        self.valid_label = Label(
            text="Годен до:",
            color=self.foreground_color,
            font_size="12sp",
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
            font_size="19sp",
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

        Clock.schedule_once(
            lambda *_:
            self._refresh_text_layout(),
            0
        )

    def _sync_name_width(
        self,
        instance,
        width
    ):
        instance.text_size = (
            max(dp(20), width),
            None
        )

    def _sync_barcode_width(
        self,
        instance,
        width
    ):
        instance.text_size = (
            max(dp(20), width),
            instance.height
        )

    def _refresh_text_layout(self):
        self._sync_name_width(
            self.name_label,
            self.name_label.width
        )
        self._sync_barcode_width(
            self.barcode_label,
            self.barcode_label.width
        )
        self._update_dynamic_height(
            self.name_label,
            self.name_label.texture_size
        )

    def _update_dynamic_height(
        self,
        _instance,
        texture_size
    ):
        name_height = max(
            dp(48),
            texture_size[1] + dp(8)
        )

        self.name_label.height = (
            name_height
        )

        wanted = (
            dp(24)
            +
            name_height
            +
            self.barcode_label.height
        )

        self.height = max(
            dp(116),
            wanted
        )

    def set_foreground(
        self,
        color
    ):
        self.foreground_color = color
        self.name_label.color = color
        self.barcode_label.color = color
        self.valid_label.color = color
        self.date_label.color = color

    def _update_card(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_color(self, *_):
        self._bg_color.rgba = (
            self.background_color
        )


# =========================================================
# DATE INPUT
# =========================================================

class DateInput(TextInput):

    __events__ = ("on_date_complete",)

    def on_date_complete(self, value):
        pass

    def _digits_only(
        self,
        value
    ):

        return "".join(
            char
            for char in str(value)
            if char.isdigit()
        )[:6]

    def _format_digits(
        self,
        digits
    ):

        digits = self._digits_only(
            digits
        )

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

    def _digit_index_from_cursor(
        self,
        cursor_col=None
    ):

        if cursor_col is None:
            cursor_col = self.cursor_col

        cursor_col = max(
            0,
            min(
                int(cursor_col),
                len(self.text)
            )
        )

        return sum(
            1
            for char in self.text[:cursor_col]
            if char.isdigit()
        )

    def _cursor_col_from_digit_index(
        self,
        digit_index
    ):

        digit_index = max(
            0,
            int(digit_index)
        )

        if digit_index == 0:
            return 0

        seen = 0

        for index, char in enumerate(
            self.text
        ):

            if char.isdigit():
                seen += 1

                if seen >= digit_index:
                    return index + 1

        return len(
            self.text
        )

    def _set_cursor_for_digit_index(
        self,
        digit_index
    ):

        self.cursor = (
            self._cursor_col_from_digit_index(
                digit_index
            ),
            0
        )

    def insert_text(
        self,
        substring,
        from_undo=False
    ):

        incoming = self._digits_only(
            substring
        )

        if not incoming:
            return

        current_digits = self._digits_only(
            self.text
        )

        # Если пользователь выделил часть даты — заменяем именно её.
        if self.selection_text:

            selection_start = min(
                self.selection_from,
                self.selection_to
            )

            selection_end = max(
                self.selection_from,
                self.selection_to
            )

            start_digit = sum(
                1
                for char in self.text[:selection_start]
                if char.isdigit()
            )

            end_digit = sum(
                1
                for char in self.text[:selection_end]
                if char.isdigit()
            )

            current_digits = (
                current_digits[:start_digit]
                +
                current_digits[end_digit:]
            )

            digit_index = start_digit
            self.cancel_selection()

        else:

            digit_index = (
                self._digit_index_from_cursor()
            )

        free_space = (
            6
            -
            len(current_digits)
        )

        if free_space <= 0:
            return

        incoming = incoming[:free_space]

        new_digits = (
            current_digits[:digit_index]
            +
            incoming
            +
            current_digits[digit_index:]
        )

        new_digit_index = (
            digit_index
            +
            len(incoming)
        )

        self.text = self._format_digits(
            new_digits
        )

        self._dispatch_if_complete()

        self._set_cursor_for_digit_index(
            new_digit_index
        )

    def do_backspace(
        self,
        from_undo=False,
        mode="bkspc"
    ):

        if self.selection_text:

            selection_start = min(
                self.selection_from,
                self.selection_to
            )

            selection_end = max(
                self.selection_from,
                self.selection_to
            )

            digits = self._digits_only(
                self.text
            )

            start_digit = sum(
                1
                for char in self.text[:selection_start]
                if char.isdigit()
            )

            end_digit = sum(
                1
                for char in self.text[:selection_end]
                if char.isdigit()
            )

            new_digits = (
                digits[:start_digit]
                +
                digits[end_digit:]
            )

            self.cancel_selection()

            self.text = self._format_digits(
                new_digits
            )

            self._set_cursor_for_digit_index(
                start_digit
            )

            return

        digits = self._digits_only(
            self.text
        )

        if not digits:
            return

        digit_index = (
            self._digit_index_from_cursor()
        )

        # Курсор в самом начале — удалять нечего.
        if digit_index <= 0:
            return

        delete_index = (
            digit_index
            -
            1
        )

        new_digits = (
            digits[:delete_index]
            +
            digits[digit_index:]
        )

        self.text = self._format_digits(
            new_digits
        )

        self._dispatch_if_complete()

        self._set_cursor_for_digit_index(
            delete_index
        )

    def _dispatch_if_complete(self):

        digits = self._digits_only(
            self.text
        )

        if len(digits) == 6:
            self.dispatch(
                "on_date_complete",
                self.text
            )

    def keyboard_on_key_down(
        self,
        window,
        keycode,
        text_value,
        modifiers
    ):

        # Delete (вперёд), если физическая клавиатура его присылает.
        if keycode[1] == "delete":

            digits = self._digits_only(
                self.text
            )

            digit_index = (
                self._digit_index_from_cursor()
            )

            if digit_index < len(digits):

                self.text = self._format_digits(
                    digits[:digit_index]
                    +
                    digits[digit_index + 1:]
                )

                self._set_cursor_for_digit_index(
                    digit_index
                )

            return True

        return super().keyboard_on_key_down(
            window,
            keycode,
            text_value,
            modifiers
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
                department TEXT NOT NULL DEFAULT '',
                photo_path TEXT NOT NULL DEFAULT '',
                photo_url TEXT NOT NULL DEFAULT '',
                product_url TEXT NOT NULL DEFAULT '',
                manual_no_date INTEGER NOT NULL DEFAULT 0,
                hidden_from_list INTEGER NOT NULL DEFAULT 0,
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

            CREATE INDEX IF NOT EXISTS
            idx_products_department
            ON products(
                department
            );

            CREATE INDEX IF NOT EXISTS
            idx_products_name
            ON products(
                name COLLATE NOCASE
            );
            """
        )

        product_columns = {
            row["name"]
            for row in self.conn.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }

        if "department" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN department TEXT NOT NULL DEFAULT ''"
            )

        if "photo_path" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''"
            )

        if "photo_url" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN photo_url TEXT NOT NULL DEFAULT ''"
            )

        if "product_url" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN product_url TEXT NOT NULL DEFAULT ''"
            )

        if "manual_no_date" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN manual_no_date INTEGER NOT NULL DEFAULT 0"
            )

        if "hidden_from_list" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN hidden_from_list INTEGER NOT NULL DEFAULT 0"
            )


        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_products_department "
            "ON products(department)"
        )

        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_products_name "
            "ON products(name COLLATE NOCASE)"
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
        name,
        department=None,
        photo_path=None,
        photo_url=None
    ):

        barcode = normalize_barcode(
            barcode
        )

        name = str(name or "").strip()

        department = (
            str(department).strip()
            if department is not None
            else None
        )

        photo_path = (
            str(photo_path).strip()
            if photo_path is not None
            else None
        )

        photo_url = (
            str(photo_url).strip()
            if photo_url is not None
            else None
        )

        existing = self.get_product(
            barcode
        )

        if existing:

            final_department = (
                department
                if department is not None
                else (
                    existing["department"]
                    or
                    ""
                )
            )

            final_photo_path = (
                photo_path
                if photo_path is not None
                else (
                    existing["photo_path"]
                    or
                    ""
                )
            )

            existing_keys = existing.keys()

            final_photo_url = (
                photo_url
                if photo_url is not None
                else (
                    existing["photo_url"]
                    if "photo_url" in existing_keys
                    else ""
                )
            )

            self.conn.execute(
                """
                UPDATE products
                SET
                    name = ?,
                    department = ?,
                    photo_path = ?,
                    photo_url = ?,
                    hidden_from_list = 0
                WHERE barcode = ?
                """,
                (
                    name,
                    final_department,
                    final_photo_path,
                    final_photo_url,
                    existing["barcode"],
                ),
            )

        else:

            self.conn.execute(
                """
                INSERT INTO products(
                    barcode,
                    name,
                    department,
                    photo_path,
                    photo_url,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    department or "",
                    photo_path or "",
                    photo_url or "",
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

        remaining = self.conn.execute(
            """
            SELECT 1
            FROM expirations
            WHERE barcode = ?
              AND written_off = 0
            LIMIT 1
            """,
            (row["barcode"],),
        ).fetchone()

        self.conn.execute(
            """
            UPDATE products
            SET manual_no_date = ?
            WHERE barcode = ?
            """,
            (0 if remaining else 1, row["barcode"]),
        )

        self.conn.commit()

        return True

    def delete_next_expiration(
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
            DELETE FROM expirations
            WHERE id = ?
            """,
            (
                row["id"],
            ),
        )

        self.conn.execute(
            """
            UPDATE products
            SET manual_no_date = 1
            WHERE barcode = ?
            """,
            (row["barcode"],),
        )

        self.conn.commit()
        return True

    def remove_product_from_list(
        self,
        barcode
    ):
        product = self.get_product(barcode)
        if not product:
            return False

        real_barcode = product["barcode"]

        # Удаляем только активные сроки. История списанных сроков остаётся.
        self.conn.execute(
            """
            DELETE FROM expirations
            WHERE barcode = ?
              AND written_off = 0
            """,
            (real_barcode,),
        )
        self.conn.execute(
            """
            UPDATE products
            SET hidden_from_list = 1,
                manual_no_date = 0
            WHERE barcode = ?
            """,
            (real_barcode,),
        )
        self.conn.commit()
        return True

    def delete_product_completely(
        self,
        barcode
    ):
        product = self.get_product(barcode)

        if not product:
            return False

        real_barcode = product["barcode"]

        # Явно удаляем сроки, затем сам товар.
        # Это работает и со старыми БД, где foreign_keys могли быть выключены.
        with self.conn:
            self.conn.execute(
                "DELETE FROM expirations WHERE barcode = ?",
                (real_barcode,),
            )
            self.conn.execute(
                "DELETE FROM products WHERE barcode = ?",
                (real_barcode,),
            )

        return True

    def update_product_record(
        self,
        old_barcode,
        new_barcode,
        name,
        department=None,
        photo_path=None,
        photo_url=None,
        exp_date_marker=None
    ):
        old_product = self.get_product(old_barcode)
        if not old_product:
            return False, "Товар не найден."

        old_real = old_product["barcode"]
        new_barcode = normalize_barcode(new_barcode)
        name = str(name or "").strip()

        if not new_barcode:
            return False, "Введите штрихкод."
        if not name:
            return False, "Введите название товара."

        existing_new = self.get_product(new_barcode)
        if existing_new and existing_new["barcode"] != old_real:
            return False, "Товар с таким штрихкодом уже существует."

        final_department = (
            str(department).strip()
            if department is not None
            else (old_product["department"] or "")
        )
        final_photo_path = (
            str(photo_path or "").strip()
            if photo_path is not None
            else (old_product["photo_path"] or "")
        )
        final_photo_url = (
            str(photo_url or "").strip()
            if photo_url is not None
            else (old_product["photo_url"] or "")
        )
        product_url = (
            old_product["product_url"]
            if "product_url" in old_product.keys()
            else ""
        ) or ""
        manual_no_date = int(
            old_product["manual_no_date"]
            if "manual_no_date" in old_product.keys()
            else 0
        )
        hidden = int(
            old_product["hidden_from_list"]
            if "hidden_from_list" in old_product.keys()
            else 0
        )

        try:
            with self.conn:
                if new_barcode != old_real:
                    self.conn.execute(
                        """
                        INSERT INTO products(
                            barcode, name, department, photo_path, photo_url,
                            product_url, manual_no_date, hidden_from_list, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_barcode, name, final_department, final_photo_path,
                            final_photo_url, product_url, manual_no_date, hidden,
                            datetime.now().isoformat(timespec="seconds"),
                        ),
                    )
                    self.conn.execute(
                        "UPDATE expirations SET barcode = ? WHERE barcode = ?",
                        (new_barcode, old_real),
                    )
                    self.conn.execute(
                        "DELETE FROM products WHERE barcode = ?",
                        (old_real,),
                    )
                else:
                    self.conn.execute(
                        """
                        UPDATE products
                        SET name = ?, department = ?, photo_path = ?, photo_url = ?
                        WHERE barcode = ?
                        """,
                        (
                            name, final_department, final_photo_path,
                            final_photo_url, old_real,
                        ),
                    )

                active_row = self.conn.execute(
                    """
                    SELECT * FROM expirations
                    WHERE barcode = ? AND written_off = 0
                    ORDER BY exp_date ASC, id ASC
                    LIMIT 1
                    """,
                    (new_barcode,),
                ).fetchone()

                if exp_date_marker == "__REMOVE_NEAREST__":
                    if active_row:
                        self.conn.execute(
                            "DELETE FROM expirations WHERE id = ?",
                            (active_row["id"],),
                        )
                elif exp_date_marker:
                    if active_row:
                        self.conn.execute(
                            "UPDATE expirations SET exp_date = ? WHERE id = ?",
                            (exp_date_marker, active_row["id"]),
                        )
                    else:
                        self.conn.execute(
                            """
                            INSERT INTO expirations(barcode, exp_date, written_off, created_at)
                            VALUES (?, ?, 0, ?)
                            """,
                            (
                                new_barcode, exp_date_marker,
                                datetime.now().isoformat(timespec="seconds"),
                            ),
                        )

                remaining = self.conn.execute(
                    """
                    SELECT 1 FROM expirations
                    WHERE barcode = ? AND written_off = 0
                    LIMIT 1
                    """,
                    (new_barcode,),
                ).fetchone()
                self.conn.execute(
                    "UPDATE products SET manual_no_date = ? WHERE barcode = ?",
                    (0 if remaining else 1, new_barcode),
                )

            return True, new_barcode
        except sqlite3.IntegrityError:
            return False, "Такой срок уже существует у этого товара."

    def set_manual_no_date(
        self,
        barcode,
        enabled
    ):

        product = self.get_product(
            barcode
        )

        if product:
            barcode = product["barcode"]

        self.conn.execute(
            """
            UPDATE products
            SET manual_no_date = ?
            WHERE barcode = ?
            """,
            (
                1 if enabled else 0,
                barcode,
            ),
        )

        self.conn.commit()

    def has_written_off_history(
        self,
        barcode
    ):

        product = self.get_product(
            barcode
        )

        if product:
            barcode = product["barcode"]

        row = self.conn.execute(
            """
            SELECT 1
            FROM expirations
            WHERE barcode = ?
              AND written_off = 1
            LIMIT 1
            """,
            (barcode,),
        ).fetchone()

        return bool(row)

    def get_product_list(
        self,
        department=None,
        filter_mode="all",
        limit=40,
        offset=0,
        search_query="",
        sort_mode="expiry"
    ):
        department = str(department).strip() if department else ""
        filter_mode = str(filter_mode or "all")
        search_query = str(search_query or "").strip()
        sort_mode = str(sort_mode or "expiry").strip()
        search_like = "%" + search_query + "%"

        today_value = date.today().strftime(DATE_DB_FORMAT)
        where_filter = "1=1"
        filter_params = []

        if filter_mode == "expired":
            where_filter = "a.next_exp IS NOT NULL AND a.next_exp < ?"
            filter_params.append(today_value)

        elif filter_mode == "expiring":
            tomorrow_value = (
                date.today() + timedelta(days=1)
            ).strftime(DATE_DB_FORMAT)
            where_filter = (
                "a.next_exp IS NOT NULL "
                "AND a.next_exp >= ? AND a.next_exp <= ?"
            )
            filter_params.extend([today_value, tomorrow_value])

        elif filter_mode == "no_date":
            where_filter = "a.next_exp IS NULL"

        if sort_mode == "added":
            # Точный внутренний created_at хранится в БД, пользователю его
            # показывать не нужно. Ранние добавленные товары идут первыми.
            order_sql = (
                "p.created_at ASC, "
                "p.rowid ASC"
            )
        elif sort_mode == "alphabet":
            order_sql = (
                "p.name COLLATE NOCASE ASC, "
                "p.barcode ASC"
            )
        else:
            # Ближайший срок наверху, товары без даты — после дат.
            order_sql = (
                "CASE WHEN a.next_exp IS NULL THEN 1 ELSE 0 END ASC, "
                "a.next_exp ASC, "
                "p.name COLLATE NOCASE ASC"
            )

        # Один GROUP BY вместо коррелированного подзапроса для каждого товара.
        # На базе в сотни/тысячи товаров отдел открывается заметно быстрее.
        query = f"""
            WITH active_min AS (
                SELECT barcode, MIN(exp_date) AS next_exp
                FROM expirations
                WHERE written_off = 0
                GROUP BY barcode
            )
            SELECT
                p.barcode,
                p.name,
                p.department,
                p.photo_path,
                p.photo_url,
                p.manual_no_date,
                a.next_exp
            FROM products p
            LEFT JOIN active_min a
              ON a.barcode = p.barcode
            WHERE COALESCE(p.hidden_from_list, 0) = 0
              AND (? = '' OR p.department = ?)
              AND (
                    ? = ''
                    OR p.name LIKE ? COLLATE NOCASE
                    OR p.barcode LIKE ?
              )
              AND {where_filter}
            ORDER BY
                {order_sql}
            LIMIT ? OFFSET ?
        """

        params = [
            department,
            department,
            search_query,
            search_like,
            search_like,
            *filter_params,
            int(limit),
            int(offset),
        ]

        return self.conn.execute(query, params).fetchall()

    def count_product_list(
        self,
        department=None,
        filter_mode="all",
        search_query=""
    ):
        department = str(department).strip() if department else ""
        filter_mode = str(filter_mode or "all")
        search_query = str(search_query or "").strip()
        search_like = "%" + search_query + "%"

        today_value = date.today().strftime(DATE_DB_FORMAT)
        where_filter = "1=1"
        filter_params = []

        if filter_mode == "expired":
            where_filter = "a.next_exp IS NOT NULL AND a.next_exp < ?"
            filter_params.append(today_value)

        elif filter_mode == "expiring":
            tomorrow_value = (
                date.today() + timedelta(days=1)
            ).strftime(DATE_DB_FORMAT)
            where_filter = (
                "a.next_exp IS NOT NULL "
                "AND a.next_exp >= ? AND a.next_exp <= ?"
            )
            filter_params.extend([today_value, tomorrow_value])

        elif filter_mode == "no_date":
            where_filter = "a.next_exp IS NULL"

        query = f"""
            WITH active_min AS (
                SELECT barcode, MIN(exp_date) AS next_exp
                FROM expirations
                WHERE written_off = 0
                GROUP BY barcode
            )
            SELECT COUNT(*)
            FROM products p
            LEFT JOIN active_min a
              ON a.barcode = p.barcode
            WHERE COALESCE(p.hidden_from_list, 0) = 0
              AND (? = '' OR p.department = ?)
              AND (
                    ? = ''
                    OR p.name LIKE ? COLLATE NOCASE
                    OR p.barcode LIKE ?
              )
              AND {where_filter}
        """

        params = [
            department,
            department,
            search_query,
            search_like,
            search_like,
            *filter_params,
        ]

        return int(self.conn.execute(query, params).fetchone()[0])

    def search_products(
        self,
        query,
        limit=30
    ):

        query = str(query or "").strip()

        if not query:
            return []

        like = "%" + query + "%"

        return self.conn.execute(
            """
            SELECT
                p.barcode,
                p.name,
                p.department,
                p.photo_path,
                p.photo_url,
                p.manual_no_date,
                EXISTS(
                    SELECT 1
                    FROM expirations ew
                    WHERE ew.barcode = p.barcode
                      AND ew.written_off = 1
                ) AS has_written_off,
                (
                    SELECT e.exp_date
                    FROM expirations e
                    WHERE e.barcode = p.barcode
                      AND e.written_off = 0
                    ORDER BY e.exp_date ASC, e.id ASC
                    LIMIT 1
                ) AS next_exp
            FROM products p
            WHERE p.name LIKE ? COLLATE NOCASE
               OR p.barcode LIKE ?
            ORDER BY
                CASE
                    WHEN lower(p.name) = lower(?) THEN 0
                    WHEN lower(p.name) LIKE lower(?) THEN 1
                    ELSE 2
                END,
                p.name COLLATE NOCASE ASC
            LIMIT ?
            """,
            (
                like,
                like,
                query,
                query + "%",
                int(limit),
            ),
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


class DepartmentScreen(BaseScreen):

    def on_pre_enter(self, *_):
        if hasattr(self, "search_input"):
            self.search_input.text = ""
        self.refresh_search("")

    def refresh_search(self, value=None):

        if not hasattr(self, "search_results"):
            return

        if value is None and hasattr(self, "search_input"):
            value = self.search_input.text

        query = str(value or "").strip()
        self.search_results.clear_widgets()

        if not query:
            self.search_results.height = 0
            self.search_results.opacity = 0
            return

        rows = self.app.db.search_products(query)

        if not rows:
            label = Label(
                text="Ничего не найдено",
                color=TEXT_SECONDARY,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
            )
            self.search_results.add_widget(label)
        else:
            for product in rows:
                department = product["department"] or "Без отдела"
                button = RoundedButton(
                    text=(
                        f'{product["name"] or "Без названия"}\\n'
                        f'{department}  •  {product["barcode"]}'
                    ),
                    size_hint_y=None,
                    height=dp(62),
                    font_size="13sp",
                    halign="left",
                    valign="middle",
                    padding=(dp(14), dp(8)),
                    normal_color=CARD,
                    down_color=BUTTON_BG_DOWN,
                )
                button.bind(
                    size=lambda instance, size:
                    setattr(
                        instance,
                        "text_size",
                        (size[0] - dp(28), size[1])
                    )
                )
                button.bind(
                    on_release=lambda _btn, row=product:
                    self.app.open_search_result(row)
                )
                self.search_results.add_widget(button)

        target_height = min(
            dp(250),
            sum(
                getattr(child, "height", dp(50))
                for child in self.search_results.children
            )
        )
        self.search_results.height = max(dp(44), target_height)
        self.search_results.opacity = 1

    def submit_search(self):

        query = self.search_input.text.strip()

        if not query:
            return

        rows = self.app.db.search_products(query, limit=2)

        if rows:
            self.app.open_search_result(rows[0])


class HomeScreen(BaseScreen):

    PAGE_SIZE = 36

    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.filter_mode = "all"
        self.sort_mode = "expiry"
        self.search_query = ""
        self.loaded_count = 0
        self.total_count = 0
        self._load_generation = 0
        self._search_event = None

    def on_pre_enter(
        self,
        *_
    ):
        # При входе в отдел поиск начинается пустым.
        self.search_query = ""
        if hasattr(self, "search_input"):
            self.search_input.text = ""
        self.refresh()

    def set_filter(
        self,
        mode
    ):
        self.filter_mode = mode
        self.refresh()

    def set_sort(
        self,
        mode
    ):
        self.sort_mode = str(mode or "expiry")
        self.refresh()

    def set_search(
        self,
        value
    ):
        self.search_query = str(value or "").strip()
        self.refresh()

    def schedule_search(
        self,
        value
    ):
        # Не пересобираем весь список на каждый отдельный символ.
        # Короткая задержка делает ввод плавнее на телефоне.
        if self._search_event is not None:
            try:
                self._search_event.cancel()
            except Exception:
                pass

        self._search_event = Clock.schedule_once(
            lambda *_: self.set_search(value),
            0.16,
        )

    def refresh(self):

        self._load_generation += 1

        if hasattr(self, "department_button"):
            self.department_button.text = (
                self.app.current_department
                or
                "Выбрать отдел"
            )

        self.product_list.clear_widgets()
        self.loaded_count = 0

        self.total_count = self.app.db.count_product_list(
            self.app.current_department,
            self.filter_mode,
            search_query=self.search_query,
        )

        if self.total_count == 0:
            self._show_empty()
            return

        self.load_more()

    def _capture_scroll_offset(self):
        if not hasattr(self, "product_scroll"):
            return None

        scroll = self.product_scroll
        content_height = max(0, self.product_list.height - scroll.height)
        return (1.0 - scroll.scroll_y) * content_height

    def _restore_scroll_offset(self, offset):
        if offset is None or not hasattr(self, "product_scroll"):
            return

        scroll = self.product_scroll
        content_height = max(0, self.product_list.height - scroll.height)

        if content_height <= 0:
            scroll.scroll_y = 1
        else:
            scroll.scroll_y = max(
                0.0,
                min(1.0, 1.0 - (offset / content_height))
            )

    def load_more(self):

        if self.loaded_count >= self.total_count:
            return

        # Запоминаем точное положение в пикселях относительно верха.
        # После добавления карточек пользователь остаётся на том же товаре.
        old_offset = self._capture_scroll_offset()
        generation = self._load_generation

        rows = self.app.db.get_product_list(
            self.app.current_department,
            self.filter_mode,
            limit=self.PAGE_SIZE,
            offset=self.loaded_count,
            search_query=self.search_query,
            sort_mode=self.sort_mode,
        )

        if generation != self._load_generation:
            return

        if hasattr(self, "more_button") and self.more_button:
            try:
                self.product_list.remove_widget(self.more_button)
            except Exception:
                pass
            self.more_button = None

        today = date.today()
        tomorrow = today + timedelta(days=1)

        for product in rows:
            exp_date = None

            if product["next_exp"]:
                try:
                    exp_date = datetime.strptime(
                        product["next_exp"],
                        DATE_DB_FORMAT,
                    ).date()
                except ValueError:
                    exp_date = None

            self.product_list.add_widget(
                self.make_product_card(
                    product,
                    exp_date,
                    today,
                    tomorrow,
                )
            )

        self.loaded_count += len(rows)

        if self.loaded_count < self.total_count:
            self.more_button = RoundedButton(
                text=(
                    "Показать ещё"
                    f"  ({self.loaded_count}/{self.total_count})"
                ),
                size_hint_y=None,
                height=dp(52),
                font_size="14sp",
                normal_color=BUTTON_BG,
                down_color=BUTTON_BG_DOWN,
            )
            self.more_button.bind(
                on_release=lambda *_: self.load_more()
            )
            self.product_list.add_widget(self.more_button)

        # Kivy должен сначала пересчитать minimum_height.
        Clock.schedule_once(
            lambda *_: self._restore_scroll_offset(old_offset),
            0,
        )

    def _show_empty(self):

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
                    "В этом списке пока нет товаров"
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
        tomorrow
    ):

        if exp_date is None:

            status_key = "no_date"
            date_text = "Без даты"

        elif exp_date < today:

            status_key = "expired"
            date_text = format_date(
                product["next_exp"]
            )

        elif exp_date == today:

            status_key = "today"
            date_text = format_date(
                product["next_exp"]
            )

        elif exp_date == tomorrow:

            status_key = "tomorrow"
            date_text = format_date(
                product["next_exp"]
            )

        else:

            status_key = "normal"
            date_text = format_date(
                product["next_exp"]
            )

        bg = self.app.get_status_color(status_key)
        fg = self.app.get_status_text_color(status_key)

        keys = product.keys()

        cached_photo = (
            self.app.get_cached_photo_path(
                product["barcode"]
            )
        )

        local_photo = (
            product["photo_path"]
            if "photo_path" in keys
            else ""
        ) or ""

        card = ProductCard(
            product_name=(
                product["name"]
                or
                "Без названия"
            ),
            barcode=product["barcode"],
            exp_date=date_text,
            photo_path=(
                local_photo
                or
                cached_photo
            ),
            photo_url=(
                product["photo_url"]
                if "photo_url" in keys
                else ""
            ),
        )

        card.background_color = bg
        card.set_foreground(fg)

        card.bind(
            on_release=lambda *_:
            self.app.open_product(
                product["barcode"]
            )
        )

        return card


class AddProductScreen(BaseScreen):

    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._auto_save_event = None
        self._auto_save_signature = None
        self._save_in_progress = False
        self.pending_photo_url = ""
        self.editing_barcode = ""
        self.editing_original_date = ""

    def on_date_change(
        self,
        instance,
        value
    ):

        # В режиме редактирования не сохраняем автоматически:
        # пользователь должен иметь возможность спокойно поменять дату.
        if self.editing_barcode:
            return

        digits = "".join(
            char
            for char in str(value or "")
            if char.isdigit()
        )

        if len(digits) != 6:
            return

        if self._auto_save_event is not None:
            try:
                self._auto_save_event.cancel()
            except Exception:
                pass

        self._auto_save_event = Clock.schedule_once(
            self._try_auto_save,
            0.03
        )

    def _try_auto_save(
        self,
        *_
    ):

        self._auto_save_event = None

        if self._save_in_progress:
            return

        if self.editing_barcode:
            return

        barcode = normalize_barcode(
            self.barcode_input.text
        )

        name = self.name_input.text.strip()
        date_text = self.date_input.text.strip()

        # Ещё раз пробуем автозаполнение названия,
        # если товар уже известен базе.
        if barcode and not name:
            self.autofill_product(
                barcode
            )
            name = self.name_input.text.strip()

        parsed = parse_user_date(
            date_text
        )

        if (
            not barcode
            or
            not name
            or
            not parsed
        ):
            return

        signature = (
            barcode,
            name,
            parsed,
        )

        if signature == self._auto_save_signature:
            return

        self._auto_save_signature = signature
        self.save(
            automatic=True
        )

    def clear_form(self):

        self._auto_save_signature = None
        self._save_in_progress = False
        self.editing_barcode = ""
        self.editing_original_date = ""

        if hasattr(self, "title_label"):
            self.title_label.text = "Добавить срок"
        if hasattr(self, "save_button"):
            self.save_button.text = "Сохранить срок"

        self.barcode_input.text = ""
        self.name_input.text = ""
        self.date_input.text = ""

        self.pending_photo_path = ""
        self.pending_photo_url = ""

        if hasattr(
            self,
            "photo_preview"
        ):
            self.photo_preview.source = ""
            self.photo_preview.opacity = 0

        if hasattr(
            self,
            "photo_status"
        ):
            self.photo_status.text = (
                "Фото не добавлено"
            )

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

        photo_path = (
            product["photo_path"]
            or
            ""
        )

        photo_url = (
            product["photo_url"]
            if "photo_url" in product.keys()
            else ""
        ) or ""

        self.pending_photo_url = (
            photo_url
        )

        if photo_path:

            self.set_photo(
                photo_path
            )

        elif photo_url and hasattr(
            self,
            "photo_preview"
        ):

            self.photo_preview.source = (
                photo_url
            )

            self.photo_preview.opacity = 1

            if hasattr(
                self,
                "photo_status"
            ):
                self.photo_status.text = (
                    "URL картинки добавлен"
                )

        if not self.editing_barcode and hasattr(self, "date_input"):
            Clock.schedule_once(
                lambda *_: setattr(self.date_input, "focus", True),
                0.08
            )

    def load_for_edit(self, barcode):
        self.clear_form()
        product = self.app.db.get_product(barcode)
        if not product:
            return False

        self.editing_barcode = product["barcode"]
        self.barcode_input.text = product["barcode"]
        self.name_input.text = (product["name"] or "")

        photo_path = (product["photo_path"] or "")
        photo_url = (
            product["photo_url"]
            if "photo_url" in product.keys()
            else ""
        ) or ""

        self.pending_photo_path = photo_path
        self.pending_photo_url = photo_url

        if photo_path and Path(photo_path).exists():
            self.set_photo(photo_path)
        elif photo_url:
            self.photo_preview.source = photo_url
            self.photo_preview.opacity = 1
            self.photo_status.text = "URL картинки добавлен"

        active = self.app.db.get_active_expirations(product["barcode"])
        if active:
            self.editing_original_date = active[0]["exp_date"]
            self.date_input.text = format_date(active[0]["exp_date"])
        else:
            self.editing_original_date = ""
            self.date_input.text = ""

        if hasattr(self, "title_label"):
            self.title_label.text = "Редактировать товар"
        if hasattr(self, "save_button"):
            self.save_button.text = "Сохранить изменения"

        return True

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

    def set_photo(
        self,
        photo_path
    ):

        self.pending_photo_path = (
            str(photo_path or "")
        )

        if not hasattr(
            self,
            "photo_preview"
        ):
            return

        if (
            self.pending_photo_path
            and
            Path(
                self.pending_photo_path
            ).exists()
        ):

            self.photo_preview.source = (
                self.pending_photo_path
            )

            self.photo_preview.reload()
            self.photo_preview.opacity = 1

            if hasattr(
                self,
                "photo_status"
            ):
                self.photo_status.text = (
                    "Фото добавлено"
                )

        else:

            self.photo_preview.source = ""
            self.photo_preview.opacity = 0

            if hasattr(
                self,
                "photo_status"
            ):
                self.photo_status.text = (
                    "Фото не добавлено"
                )

    def add_image_url(
        self
    ):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(12),
        )

        url_input = RoundedTextInput(
            text=(
                getattr(
                    self,
                    "pending_photo_url",
                    ""
                )
                or
                ""
            ),
            hint_text="https://...",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size="14sp",
            padding=(
                dp(12),
                dp(13),
            ),
        )

        info = Label(
            text=(
                "Вставь прямую ссылку на картинку товара."
            ),
            color=TEXT_SECONDARY,
            font_size="12sp",
            size_hint_y=None,
            height=dp(38),
            halign="center",
            valign="middle",
        )

        info.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        buttons = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            spacing=dp(8),
        )

        cancel_button = RoundedButton(
            text="Отмена",
            font_size="14sp",
        )

        save_button = RoundedButton(
            text="Сохранить URL",
            font_size="14sp",
            normal_color=ACCENT_RED,
            down_color=ACCENT_RED_DOWN,
        )

        buttons.add_widget(
            cancel_button
        )

        buttons.add_widget(
            save_button
        )

        content.add_widget(
            info
        )

        content.add_widget(
            url_input
        )

        content.add_widget(
            buttons
        )

        popup = Popup(
            title="URL картинки",
            content=content,
            size_hint=(0.92, None),
            height=dp(235),
            auto_dismiss=False,
        )

        cancel_button.bind(
            on_release=lambda *_:
            popup.dismiss()
        )

        def save_url(*_):

            url = (
                url_input.text
                .strip()
            )

            if (
                url
                and
                not url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                )
            ):
                self.app.message(
                    "URL должен начинаться с http:// или https://"
                )
                return

            self.pending_photo_url = (
                url
            )

            if url:
                self.photo_preview.source = (
                    url
                )
                self.photo_preview.opacity = 1
                self.photo_status.text = (
                    "URL картинки добавлен"
                )
            else:
                self.photo_preview.source = ""
                self.photo_preview.opacity = 0
                self.photo_status.text = (
                    "Фото не добавлено"
                )

            popup.dismiss()

        save_button.bind(
            on_release=save_url
        )

        popup.open()

        Clock.schedule_once(
            lambda *_:
            setattr(
                url_input,
                "focus",
                True
            ),
            0.15
        )

    def choose_photo(
        self
    ):

        self.app.choose_product_photo(
            self
        )

    def take_photo(
        self
    ):

        self.app.take_product_photo(
            self
        )

    def save(self, automatic=False):

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

        if self._save_in_progress:
            return


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

        exp_date = None

        if date_text:
            exp_date = parse_user_date(
                date_text
            )

            if not exp_date:
                self.app.message(
                    "Введите срок в формате ДД.ММ.ГГ.\n\n"
                    "Например: 280826 → 28.08.26"
                )
                return

        if self.editing_barcode:
            marker = exp_date if exp_date else "__REMOVE_NEAREST__"
            ok, result = self.app.db.update_product_record(
                old_barcode=self.editing_barcode,
                new_barcode=barcode,
                name=name,
                department=self.app.current_department,
                photo_path=getattr(self, "pending_photo_path", ""),
                photo_url=getattr(self, "pending_photo_url", ""),
                exp_date_marker=marker,
            )
            if not ok:
                self.app.message(result)
                return

            self.editing_barcode = result
            self.app.message("Изменения сохранены.")
            self.app.open_product(result)
            return

        existing_product = (
            self.app.db.get_product(
                barcode
            )
        )

        self._save_in_progress = True

        self.app.db.save_product(
            barcode=barcode,
            name=name,
            department=self.app.current_department,
            photo_path=getattr(
                self,
                "pending_photo_path",
                ""
            ),
            photo_url=getattr(
                self,
                "pending_photo_url",
                ""
            ),
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

        if exp_date:
            if not self.app.db.add_expiration(
                barcode_for_expiration,
                exp_date
            ):
                self._save_in_progress = False
                self.app.message(
                    "Такой срок у этого товара уже существует."
                )
                return

            if not automatic:
                self.app.message(
                    "Срок успешно добавлен."
                )
        else:
            self.app.db.set_manual_no_date(
                barcode_for_expiration,
                True
            )

            if not automatic:
                self.app.message(
                    "Товар сохранён без срока.\n"
                    "Он будет показан фиолетовым."
                )

        self._save_in_progress = False
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

        keys = product.keys()

        photo_path = (
            product["photo_path"]
            if "photo_path" in keys
            else ""
        ) or ""

        photo_url = (
            product["photo_url"]
            if "photo_url" in keys
            else ""
        ) or ""

        if (
            photo_path
            and
            Path(photo_path).exists()
        ):
            self.product_image.texture = None
            self.product_image.source = (
                photo_path
            )
            self.product_image.opacity = 1
            if hasattr(self, "product_image_bg_color"):
                self.product_image_bg_color.rgba = (0, 0, 0, 0)

        elif photo_url.startswith(
            ("http://", "https://")
        ):
            self.product_image.texture = None
            self.product_image.source = (
                photo_url
            )
            self.product_image.opacity = 1
            if hasattr(self, "product_image_bg_color"):
                self.product_image_bg_color.rgba = (0, 0, 0, 0)

        else:
            self.product_image.texture = None
            self.product_image.source = ""
            self.product_image.opacity = 0
            if hasattr(self, "product_image_bg_color"):
                self.product_image_bg_color.rgba = THUMBNAIL_BG

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
                status = "СПИСАНО"
            else:
                status = "АКТИВЕН"

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

        has_active = bool(active)

        self.writeoff_button.disabled = (
            not has_active
        )

        if hasattr(self, "delete_product_button"):
            self.delete_product_button.disabled = False

    def write_off(self):

        if not self.app.db.write_off_next(self.barcode):
            self.app.message("У товара нет активных сроков.")
            return

        # Сразу возвращаемся в отдел. Карточка автоматически покажет
        # следующий ближайший срок, а если сроков больше нет — попадёт
        # в фиолетовый список «Без даты».
        self.app.open_home()

    def delete_product(self):
        self.app.confirm_delete_product(self.barcode)



class SettingsScreen(BaseScreen):

    def refresh_color_previews(self):
        previews = getattr(self, "color_previews", {})

        for key, widget in previews.items():
            try:
                color = self.app.get_status_color(key)
                text_color = self.app.get_status_text_color(key)
                widget.normal_color = list(color)
                widget.down_color = list(
                    tuple(max(0.0, c * 0.82) for c in color[:3]) + (1,)
                )
                widget.set_foreground(text_color)
            except Exception as exc:
                print("color preview refresh error:", exc)



# =========================================================
# MAIN APP
# =========================================================

class MainApp(App):

    title = APP_TITLE

    def get_photo_cache_dir(self):

        cache_dir = (
            Path(self.user_data_dir)
            /
            "product_images"
        )

        cache_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        return cache_dir

    def get_cached_photo_path(
        self,
        barcode
    ):

        barcode = normalize_barcode(
            barcode
        )

        for suffix in (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".img",
        ):
            path = (
                self.get_photo_cache_dir()
                /
                f"{barcode}{suffix}"
            )

            if path.exists():
                return str(path)

        return ""

    def _load_status_colors(self):

        backgrounds = {
            key: list(value)
            for key, value in DEFAULT_STATUS_COLORS.items()
        }

        text_colors = {
            key: list(value)
            for key, value in DEFAULT_STATUS_TEXT_COLORS.items()
        }

        try:
            if self.status_colors_path.exists():
                saved = json.loads(
                    self.status_colors_path.read_text(
                        encoding="utf-8"
                    )
                )

                if isinstance(saved, dict):
                    # Новый формат:
                    # {"backgrounds": {...}, "texts": {...}}
                    saved_backgrounds = saved.get("backgrounds")
                    saved_texts = saved.get("texts")

                    # Совместимость со старым v14:
                    # {"expired": [...], "today": [...], ...}
                    if not isinstance(saved_backgrounds, dict):
                        saved_backgrounds = saved

                    if not isinstance(saved_texts, dict):
                        saved_texts = {}

                    for key in DEFAULT_STATUS_COLORS:
                        value = saved_backgrounds.get(key)

                        if isinstance(value, list) and len(value) == 4:
                            backgrounds[key] = [
                                max(0.0, min(1.0, float(channel)))
                                for channel in value
                            ]

                    for key in DEFAULT_STATUS_TEXT_COLORS:
                        value = saved_texts.get(key)

                        if isinstance(value, list) and len(value) == 4:
                            text_colors[key] = [
                                max(0.0, min(1.0, float(channel)))
                                for channel in value
                            ]

        except Exception as exc:
            print("status color load error:", exc)

        return backgrounds, text_colors

    def _save_status_colors(self):

        try:
            self.status_colors_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            payload = {
                "backgrounds": self.status_colors,
                "texts": self.status_text_colors,
            }

            self.status_colors_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return True

        except Exception as exc:
            print("status color save error:", exc)
            return False

    def get_status_color(self, key):

        value = self.status_colors.get(
            key,
            DEFAULT_STATUS_COLORS.get(key, CARD),
        )

        try:
            return tuple(float(x) for x in value[:4])
        except Exception:
            return DEFAULT_STATUS_COLORS.get(key, CARD)

    def set_status_color(self, key, color):

        if key not in DEFAULT_STATUS_COLORS:
            return

        self.status_colors[key] = [
            float(channel)
            for channel in color[:4]
        ]

        self._save_status_colors()

        try:
            settings = self.sm.get_screen("settings")
            settings.refresh_color_previews()
        except Exception:
            pass

        try:
            home = self.sm.get_screen("home")
            home.refresh()
        except Exception:
            pass

    def get_status_text_color(self, key):

        value = self.status_text_colors.get(
            key,
            DEFAULT_STATUS_TEXT_COLORS.get(key, TEXT),
        )

        try:
            return tuple(float(x) for x in value[:4])
        except Exception:
            return DEFAULT_STATUS_TEXT_COLORS.get(key, TEXT)

    def set_status_text_color(self, key, color):

        if key not in DEFAULT_STATUS_TEXT_COLORS:
            return

        self.status_text_colors[key] = [
            float(channel)
            for channel in color[:4]
        ]

        self._save_status_colors()

        try:
            settings = self.sm.get_screen("settings")
            settings.refresh_color_previews()
        except Exception:
            pass

        try:
            home = self.sm.get_screen("home")
            home.refresh()
        except Exception:
            pass

    def reset_status_colors(self):

        self.status_colors = {
            key: list(value)
            for key, value in DEFAULT_STATUS_COLORS.items()
        }

        self.status_text_colors = {
            key: list(value)
            for key, value in DEFAULT_STATUS_TEXT_COLORS.items()
        }

        self._save_status_colors()

        try:
            self.sm.get_screen(
                "settings"
            ).refresh_color_previews()
        except Exception:
            pass

        try:
            self.sm.get_screen("home").refresh()
        except Exception:
            pass

        self.message("Цвета восстановлены по умолчанию.")

    def open_status_color_picker(self, status_key):

        if status_key not in DEFAULT_STATUS_COLORS:
            return

        overlay = ModalView(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0.66),
            auto_dismiss=True,
        )

        card = BoxLayout(
            orientation="vertical",
            size_hint=(0.92, None),
            height=dp(530),
            padding=(dp(16), dp(16), dp(16), dp(14)),
            spacing=dp(10),
        )

        with card.canvas.before:
            _card_color = Color(0.12, 0.13, 0.15, 1)
            _card_rect = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[dp(26)],
            )

        def sync_card(*_):
            _card_rect.pos = card.pos
            _card_rect.size = card.size

        card.bind(
            pos=sync_card,
            size=sync_card,
        )

        title = Label(
            text="Настройка цвета",
            color=TEXT,
            bold=True,
            font_size="21sp",
            size_hint_y=None,
            height=dp(38),
            halign="left",
            valign="middle",
        )
        title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        card.add_widget(title)

        subtitle = Label(
            text=STATUS_COLOR_LABELS.get(status_key, status_key),
            color=TEXT_SECONDARY,
            font_size="14sp",
            size_hint_y=None,
            height=dp(38),
            halign="left",
            valign="top",
        )
        subtitle.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (value[0], None))
        )
        card.add_widget(subtitle)

        def make_section(label_text, current_color, setter):
            section = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(168),
                spacing=dp(8),
            )

            label = Label(
                text=label_text,
                color=TEXT,
                bold=True,
                font_size="15sp",
                size_hint_y=None,
                height=dp(28),
                halign="left",
                valign="middle",
            )
            label.bind(
                size=lambda instance, value:
                setattr(instance, "text_size", value)
            )
            section.add_widget(label)

            grid = GridLayout(
                cols=5,
                rows=4,
                spacing=dp(7),
                size_hint_y=None,
                height=dp(132),
            )

            for color in STATUS_COLOR_PALETTE:
                selected = (
                    tuple(round(x, 4) for x in current_color)
                    ==
                    tuple(round(x, 4) for x in color)
                )

                swatch = ColorSwatch(
                    swatch_color=color,
                    selected=selected,
                )

                def choose(_button, chosen=color, apply=setter):
                    apply(status_key, chosen)
                    overlay.dismiss()

                swatch.bind(
                    on_release=choose
                )
                grid.add_widget(swatch)

            section.add_widget(grid)
            return section

        card.add_widget(
            make_section(
                "Цвет карточки",
                self.get_status_color(status_key),
                self.set_status_color,
            )
        )

        card.add_widget(
            make_section(
                "Цвет текста",
                self.get_status_text_color(status_key),
                self.set_status_text_color,
            )
        )

        cancel = RoundedButton(
            text="Отмена",
            size_hint_y=None,
            height=dp(52),
            font_size="15sp",
            normal_color=BUTTON_BG,
            down_color=BUTTON_BG_DOWN,
        )
        cancel.bind(
            on_release=lambda *_:
            overlay.dismiss()
        )
        card.add_widget(cancel)

        wrapper = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
        )
        wrapper.add_widget(card)
        overlay.add_widget(wrapper)
        overlay.open()

    def build(self):

        self.db_path = (
            Path(
                self.user_data_dir
            )
            /
            DB_NAME
        )

        self.current_department = None
        self.pending_photo_screen = None

        self.status_colors_path = (
            Path(self.user_data_dir)
            /
            "status_colors.json"
        )

        try:
            (
                self.status_colors,
                self.status_text_colors,
            ) = self._load_status_colors()
        except Exception as exc:
            print("status colors startup fallback:", exc)
            self.status_colors = {
                key: list(value)
                for key, value in DEFAULT_STATUS_COLORS.items()
            }
            self.status_text_colors = {
                key: list(value)
                for key, value in DEFAULT_STATUS_TEXT_COLORS.items()
            }

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
            self.create_department_screen()
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

        if self.sm.current == "departments":
            return False

        if self.sm.current == "home":
            self.open_departments()
            return True

        if self.sm.current == "settings":
            self.open_departments()
            return True

        self.open_home()
        return True


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
    # DEPARTMENT SELECTION
    # =====================================================

    def create_department_screen(self):

        screen = DepartmentScreen(name="departments")

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(horizontal=14, top=7, bottom=12),
            spacing=dp(10),
        )

        root.add_widget(self.create_header())

        # Поиск товара находится именно на стартовом экране.
        search_input = RoundedTextInput(
            hint_text="Поиск...",
            hint_text_color=(1, 1, 1, 1),
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size="16sp",
            padding=(dp(15), dp(13)),
        )

        root.add_widget(search_input)
        screen.search_input = search_input

        search_results_scroll = ScrollView(
            do_scroll_x=False,
            size_hint_y=None,
            height=0,
            opacity=0,
        )
        search_results = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
        )
        search_results.bind(
            minimum_height=search_results.setter("height")
        )
        search_results_scroll.add_widget(search_results)
        root.add_widget(search_results_scroll)

        screen.search_results = search_results
        screen.search_results_scroll = search_results_scroll

        def update_search(_instance, value):
            screen.refresh_search(value)
            if value.strip():
                search_results_scroll.height = min(
                    dp(250),
                    max(dp(50), search_results.height)
                )
                search_results_scroll.opacity = 1
            else:
                search_results_scroll.height = 0
                search_results_scroll.opacity = 0

        search_input.bind(text=update_search)
        search_input.bind(
            on_text_validate=lambda *_: screen.submit_search()
        )

        settings_button = RoundedButton(
            text="Настройки",
            size_hint_y=None,
            height=dp(52),
            font_size="15sp",
        )
        settings_button.bind(
            on_release=lambda *_: self.open_settings()
        )
        root.add_widget(settings_button)

        title = Label(
            text="Выберите отдел",
            color=TEXT,
            bold=True,
            font_size="22sp",
            size_hint_y=None,
            height=dp(46),
            halign="left",
            valign="middle",
        )
        title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        root.add_widget(title)

        scroll = ScrollView(do_scroll_x=False)

        departments_list = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8),
            padding=(0, dp(2), 0, dp(10)),
        )
        departments_list.bind(
            minimum_height=departments_list.setter("height")
        )

        for department_name in DEPARTMENTS:
            button = RoundedButton(
                text=department_name,
                size_hint_y=None,
                height=dp(56),
                font_size="14sp",
                halign="left",
                valign="middle",
                padding=(dp(18), dp(10)),
                normal_color=CARD,
                down_color=BUTTON_BG_DOWN,
            )
            button.bind(
                size=lambda instance, value:
                setattr(
                    instance,
                    "text_size",
                    (value[0] - dp(36), value[1])
                )
            )
            button.bind(
                on_release=lambda _button, name=department_name:
                self.select_department(name)
            )
            departments_list.add_widget(button)

        scroll.add_widget(departments_list)
        root.add_widget(scroll)

        screen.add_widget(root)
        return screen


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

        department_button = RoundedButton(
            text=(self.current_department or "Выбрать отдел"),
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            normal_color=CARD,
            down_color=BUTTON_BG_DOWN,
        )
        department_button.bind(on_release=lambda *_: self.open_departments())
        root.add_widget(department_button)
        screen.department_button = department_button

        # Поиск только внутри текущего отдела.
        local_search = RoundedTextInput(
            hint_text="Поиск...",
            hint_text_color=(1, 1, 1, 1),
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size="15sp",
            padding=(dp(15), dp(12)),
        )
        local_search.bind(
            text=lambda _instance, value: screen.schedule_search(value)
        )

        root.add_widget(local_search)
        screen.search_input = local_search

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
            size_hint_x=0.82,
        )
        add_button.bind(
            on_release=lambda *_:
            self.start_barcode_scanner()
        )

        sort_button = RoundedImageButton(
            image_source="sort.png",
            size_hint_x=0.18,
        )
        sort_button.bind(
            on_release=lambda *_:
            self.open_sort_popup()
        )

        actions.add_widget(add_button)
        actions.add_widget(sort_button)

        root.add_widget(actions)


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
        screen.product_scroll = scroll

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
            text="Назад",
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

        add_title = Label(
            text="Добавить срок",
            color=TEXT,
            font_size="25sp",
            bold=True,
            size_hint_y=None,
            height=dp(58),
        )
        root.add_widget(add_title)

        info = Label(
            text=(
                "Отсканируй штрихкод или введи его вручную.\n"
                "Дата и фото необязательны."
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
            hint_text="ДД.ММ.ГГ (необязательно)",
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

        date_input.bind(
            text=
            screen.on_date_change
        )

        date_input.bind(
            on_date_complete=lambda _instance, _value:
            screen._try_auto_save()
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

        photo_title = Label(
            text="Фото товара (необязательно)",
            color=TEXT_SECONDARY,
            font_size="12sp",
            size_hint_y=None,
            height=dp(25),
            halign="left",
            valign="middle",
        )
        photo_title.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )
        root.add_widget(
            photo_title
        )

        photo_row = BoxLayout(
            size_hint_y=None,
            height=dp(96),
            spacing=dp(10),
        )

        preview_holder = BoxLayout(
            size_hint_x=None,
            width=dp(96),
            padding=dp(5),
        )

        with preview_holder.canvas.before:

            Color(
                *THUMBNAIL_BG
            )

            preview_bg = RoundedRectangle(
                pos=preview_holder.pos,
                size=preview_holder.size,
                radius=[dp(15)],
            )

        preview_holder.bind(
            pos=lambda instance, value:
            setattr(
                preview_bg,
                "pos",
                value
            ),
            size=lambda instance, value:
            setattr(
                preview_bg,
                "size",
                value
            ),
        )

        photo_preview = AsyncImage(
            source="",
            fit_mode="contain",
            opacity=0,
            nocache=False,
        )

        preview_holder.add_widget(
            photo_preview
        )

        photo_controls = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
        )

        camera_photo_button = RoundedButton(
            text="Сделать фото",
            font_size="13sp",
        )

        camera_photo_button.bind(
            on_release=lambda *_:
            screen.take_photo()
        )

        gallery_photo_button = RoundedButton(
            text="Выбрать из галереи",
            font_size="13sp",
        )

        gallery_photo_button.bind(
            on_release=lambda *_:
            screen.choose_photo()
        )

        photo_status = Label(
            text="Фото не добавлено",
            color=TEXT_SECONDARY,
            font_size="11sp",
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
        )

        photo_status.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        photo_controls.add_widget(
            camera_photo_button
        )

        photo_controls.add_widget(
            gallery_photo_button
        )

        photo_controls.add_widget(
            photo_status
        )

        photo_row.add_widget(
            preview_holder
        )

        photo_row.add_widget(
            photo_controls
        )

        root.add_widget(
            photo_row
        )

        image_url_button = RoundedButton(
            text="Добавить URL картинки",
            size_hint_y=None,
            height=dp(46),
            font_size="14sp",
        )

        image_url_button.bind(
            on_release=lambda *_:
            screen.add_image_url()
        )

        root.add_widget(
            image_url_button
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

        screen.photo_preview = (
            photo_preview
        )

        screen.photo_status = (
            photo_status
        )

        screen.pending_photo_path = ""
        screen.pending_photo_url = ""
        screen.title_label = add_title
        screen.save_button = save

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

        top_actions = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
        )

        back = RoundedButton(
            text="<",
            size_hint_x=None,
            width=dp(58),
            font_size="22sp",
        )
        back.bind(
            on_release=lambda *_: self.open_home()
        )

        edit_button = RoundedButton(
            text="Редактировать",
            font_size="15sp",
        )
        edit_button.bind(
            on_release=lambda *_: self.open_edit_product(screen.barcode)
        )

        top_actions.add_widget(back)
        top_actions.add_widget(edit_button)
        root.add_widget(top_actions)

        product_name = Label(
            text="Товар",
            color=TEXT,
            font_size="26sp",
            bold=True,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(58),
        )

        def update_product_title_layout(
            instance,
            *_args
        ):
            instance.text_size = (
                max(
                    dp(40),
                    instance.width - dp(18)
                ),
                None
            )

            instance.height = max(
                dp(58),
                instance.texture_size[1]
                +
                dp(18)
            )

        product_name.bind(
            width=update_product_title_layout,
            texture_size=update_product_title_layout,
        )

        image_holder = AnchorLayout(
            size_hint_y=None,
            height=dp(220),
            anchor_x="center",
            anchor_y="center",
        )

        with image_holder.canvas.before:
            detail_bg_color = Color(
                *THUMBNAIL_BG
            )
            detail_bg_rect = RoundedRectangle(
                pos=image_holder.pos,
                size=(dp(204), dp(204)),
                radius=[dp(18)],
            )

        def update_detail_bg(
            instance,
            *_args
        ):
            detail_bg_rect.pos = (
                instance.center_x - dp(102),
                instance.center_y - dp(102),
            )
            detail_bg_rect.size = (
                dp(204),
                dp(204),
            )

        image_holder.bind(
            pos=update_detail_bg,
            size=update_detail_bg,
        )

        product_image = AsyncImage(
            source="",
            fit_mode="contain",
            size_hint=(None, None),
            size=(dp(204), dp(204)),
            opacity=0,
            nocache=False,
        )

        image_holder.add_widget(
            product_image
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
            image_holder
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

        action_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(10),
        )

        writeoff = RoundedButton(
            text="Списано",
            font_size="16sp",
            normal_color=RED,
            down_color=(
                0.65,
                0.08,
                0.10,
                1,
            ),
        )

        delete_product = RoundedButton(
            text="Удалить товар",
            font_size="16sp",
            normal_color=BUTTON_BG,
            down_color=BUTTON_BG_DOWN,
        )

        writeoff.bind(
            on_release=lambda *_:
            screen.write_off()
        )

        delete_product.bind(
            on_release=lambda *_:
            screen.delete_product()
        )

        action_row.add_widget(
            writeoff
        )

        action_row.add_widget(
            delete_product
        )

        root.add_widget(
            action_row
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

        screen.product_image = (
            product_image
        )
        screen.product_image_bg_color = detail_bg_color

        screen.writeoff_button = (
            writeoff
        )

        screen.delete_product_button = (
            delete_product
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
            text="Назад",
            size_hint_y=None,
            height=dp(50),
        )
        back.bind(
            on_release=lambda *_:
            self.open_home()
        )
        root.add_widget(back)

        root.add_widget(
            Label(
                text="Настройки",
                color=TEXT,
                font_size="26sp",
                bold=True,
                size_hint_y=None,
                height=dp(54),
            )
        )

        scroll = ScrollView(
            do_scroll_x=False,
        )

        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=(0, 0, 0, dp(12)),
        )
        content.bind(
            minimum_height=content.setter("height")
        )

        colors_title = Label(
            text="Цвета статусов товаров",
            color=TEXT,
            bold=True,
            font_size="18sp",
            size_hint_y=None,
            height=dp(42),
            halign="left",
            valign="middle",
        )
        colors_title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        content.add_widget(colors_title)

        colors_help = Label(
            text=(
                "Нажми на нужный статус, чтобы выбрать его цвет. "
                "Настройка сохраняется автоматически."
            ),
            color=TEXT_SECONDARY,
            font_size="13sp",
            size_hint_y=None,
            height=dp(58),
            halign="left",
            valign="middle",
        )
        colors_help.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", (value[0], None))
        )
        content.add_widget(colors_help)

        screen.color_previews = {}

        for key in (
            "expired",
            "today",
            "tomorrow",
            "no_date",
            "normal",
        ):
            color = self.get_status_color(key)

            button = RoundedButton(
                text=STATUS_COLOR_LABELS[key],
                size_hint_y=None,
                height=dp(56),
                font_size="15sp",
                normal_color=color,
                down_color=tuple(
                    max(0, c * 0.82)
                    for c in color[:3]
                ) + (1,),
            )
            button.set_foreground(
                self.get_status_text_color(key)
            )
            button.bind(
                on_release=lambda _button, status=key:
                self.open_status_color_picker(status)
            )

            screen.color_previews[key] = button
            content.add_widget(button)

        reset_colors = RoundedButton(
            text="Сбросить цвета",
            size_hint_y=None,
            height=dp(50),
            font_size="14sp",
            normal_color=BUTTON_BG,
            down_color=BUTTON_BG_DOWN,
        )
        reset_colors.bind(
            on_release=lambda *_:
            self.reset_status_colors()
        )
        content.add_widget(reset_colors)


        divider = Widget(
            size_hint_y=None,
            height=dp(12),
        )
        content.add_widget(divider)

        content.add_widget(
            Label(
                text="База данных",
                color=TEXT,
                font_size="18sp",
                bold=True,
                size_hint_y=None,
                height=dp(42),
                halign="left",
                valign="middle",
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
        content.add_widget(export_button)

        import_button = RoundedButton(
            text="Импортировать БД",
            size_hint_y=None,
            height=dp(58),
        )
        import_button.bind(
            on_release=lambda *_:
            self.import_database()
        )
        content.add_widget(import_button)

        clear_button = RoundedButton(
            text="Очистить БД",
            size_hint_y=None,
            height=dp(58),
            normal_color=RED,
            down_color=(0.65, 0.08, 0.10, 1),
        )
        clear_button.bind(
            on_release=lambda *_:
            self.confirm_clear_database()
        )
        content.add_widget(clear_button)

        scroll.add_widget(content)
        root.add_widget(scroll)

        screen.add_widget(root)
        return screen


    # =====================================================
    # SORT / FILTER
    # =====================================================

    def open_sort_popup(self):

        overlay = ModalView(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0.62),
            auto_dismiss=True,
        )

        card = BoxLayout(
            orientation="vertical",
            size_hint=(0.90, None),
            height=dp(590),
            padding=dp(14),
            spacing=dp(8),
        )

        with card.canvas.before:
            _card_color = Color(
                0.12,
                0.13,
                0.15,
                1,
            )
            _card_rect = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[dp(24)],
            )

        def update_card(*_):
            _card_rect.pos = card.pos
            _card_rect.size = card.size

        card.bind(
            pos=update_card,
            size=update_card,
        )

        title = Label(
            text="[b]Сортировка и фильтр[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(38),
            font_size="20sp",
            halign="left",
            valign="middle",
            color=TEXT,
        )
        title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        card.add_widget(title)

        home = self.sm.get_screen("home")

        filter_title = Label(
            text="Показывать",
            color=TEXT_SECONDARY,
            bold=True,
            font_size="13sp",
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
        )
        filter_title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        card.add_widget(filter_title)

        filter_options = (
            ("Все товары", "all", BUTTON_BG, BUTTON_BG_DOWN, TEXT),
            ("Просроченный товар", "expired", ACCENT_RED, ACCENT_RED_DOWN, TEXT),
            (
                "Истекающий товар",
                "expiring",
                (1.0, 0.78, 0.12, 1),
                (0.90, 0.66, 0.06, 1),
                (0.08, 0.08, 0.08, 1),
            ),
            ("Без даты", "no_date", PURPLE, PURPLE_DOWN, TEXT),
        )

        for title_text, mode, normal, down, text_color in filter_options:
            selected = home.filter_mode == mode

            button = RoundedButton(
                text=("• " if selected else "") + title_text,
                size_hint_y=None,
                height=dp(48),
                font_size="14sp",
                normal_color=normal,
                down_color=down,
                color=text_color,
            )

            def choose_filter(_button, selected_mode=mode):
                home.set_filter(selected_mode)
                overlay.dismiss()

            button.bind(on_release=choose_filter)
            card.add_widget(button)

        sort_title = Label(
            text="Порядок списка",
            color=TEXT_SECONDARY,
            bold=True,
            font_size="13sp",
            size_hint_y=None,
            height=dp(28),
            halign="left",
            valign="middle",
        )
        sort_title.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )
        card.add_widget(sort_title)

        sort_options = (
            ("По порядку добавления", "added"),
            ("По сроку годности", "expiry"),
            ("По алфавиту А–Я", "alphabet"),
        )

        for title_text, mode in sort_options:
            selected = home.sort_mode == mode

            button = RoundedButton(
                text=("• " if selected else "") + title_text,
                size_hint_y=None,
                height=dp(48),
                font_size="14sp",
                normal_color=(
                    ACCENT_RED if selected else BUTTON_BG
                ),
                down_color=(
                    ACCENT_RED_DOWN if selected else BUTTON_BG_DOWN
                ),
                color=TEXT,
            )

            def choose_sort(_button, selected_mode=mode):
                home.set_sort(selected_mode)
                overlay.dismiss()

            button.bind(on_release=choose_sort)
            card.add_widget(button)

        wrapper = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
        )
        wrapper.add_widget(card)
        overlay.add_widget(wrapper)
        overlay.open()


    # =====================================================
    # NAVIGATION
    # =====================================================

    def open_departments(self):
        self.sm.current = "departments"

    def open_search_result(self, product):

        department = (
            product["department"]
            if product["department"]
            else None
        )

        if department:
            self.current_department = department

        self.open_product(
            product["barcode"]
        )

    def select_department(self, department):
        self.current_department = department
        self.sm.current = "home"
        self.sm.get_screen("home").refresh()

    def open_home(self):

        if not self.current_department:
            self.open_departments()
            return

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

    def open_edit_product(self, barcode):
        screen = self.sm.get_screen("add")
        if not screen.load_for_edit(barcode):
            self.message("Товар не найден.")
            return
        self.sm.current = "add"

    def open_settings(self):

        self.sm.current = (
            "settings"
        )

        try:
            self.sm.get_screen(
                "settings"
            ).refresh_color_previews()
        except Exception:
            pass


    # =====================================================
    # PRODUCT PHOTO
    # =====================================================

    def _product_photo_dir(
        self
    ):

        folder = (
            Path(
                self.user_data_dir
            )
            /
            "product_photos"
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return folder

    def choose_product_photo(
        self,
        screen
    ):

        if not ANDROID:

            self.message(
                "Выбор фото из галереи доступен на Android."
            )

            return

        if not PYJNIUS_AVAILABLE:

            self.message(
                "PyJNIus недоступен."
            )

            return

        try:

            self.pending_photo_screen = (
                screen
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            intent = Intent(
                Intent.ACTION_OPEN_DOCUMENT
            )

            intent.addCategory(
                Intent.CATEGORY_OPENABLE
            )

            intent.setType(
                "image/*"
            )

            current_activity.startActivityForResult(
                intent,
                REQUEST_PICK_PRODUCT_PHOTO
            )

        except Exception as exc:

            self.pending_photo_screen = None

            self.message(
                "Не удалось открыть галерею:\\n\\n"
                +
                str(exc)
            )

    def take_product_photo(
        self,
        screen
    ):

        if not ANDROID:

            self.message(
                "Камера для фото доступна на Android."
            )

            return

        if not PYJNIUS_AVAILABLE:

            self.message(
                "PyJNIus недоступен."
            )

            return

        try:

            self.pending_photo_screen = (
                screen
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            MediaStore = autoclass(
                "android.provider.MediaStore"
            )

            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )

            intent = Intent(
                MediaStore.ACTION_IMAGE_CAPTURE
            )

            current_activity.startActivityForResult(
                intent,
                REQUEST_TAKE_PRODUCT_PHOTO
            )

        except Exception as exc:

            self.pending_photo_screen = None

            self.message(
                "Не удалось открыть камеру:\\n\\n"
                +
                str(exc)
            )

    def _copy_content_uri_to_photo(
        self,
        uri
    ):

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

        parcel_fd = (
            resolver
            .openFileDescriptor(
                uri,
                "r"
            )
        )

        if parcel_fd is None:

            raise RuntimeError(
                "Не удалось открыть выбранное изображение."
            )

        target = (
            self._product_photo_dir()
            /
            (
                "product_"
                +
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
                +
                ".jpg"
            )
        )

        duplicated_fd = None

        try:

            duplicated_fd = os.dup(
                parcel_fd.getFd()
            )

            with os.fdopen(
                duplicated_fd,
                "rb",
                closefd=True
            ) as source_file:

                duplicated_fd = None

                with target.open(
                    "wb"
                ) as target_file:

                    shutil.copyfileobj(
                        source_file,
                        target_file,
                        length=1024 * 1024
                    )

        finally:

            if duplicated_fd is not None:

                try:
                    os.close(
                        duplicated_fd
                    )
                except OSError:
                    pass

            parcel_fd.close()

        return str(
            target
        )

    def _save_camera_thumbnail(
        self,
        intent
    ):

        extras = (
            intent.getExtras()
            if intent is not None
            else None
        )

        if extras is None:

            raise RuntimeError(
                "Камера не вернула изображение."
            )

        bitmap = (
            extras.get(
                "data"
            )
        )

        if bitmap is None:

            raise RuntimeError(
                "Камера не вернула изображение."
            )

        target = (
            self._product_photo_dir()
            /
            (
                "product_"
                +
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
                +
                ".jpg"
            )
        )

        FileOutputStream = autoclass(
            "java.io.FileOutputStream"
        )

        CompressFormat = autoclass(
            "android.graphics.Bitmap$CompressFormat"
        )

        output_stream = FileOutputStream(
            str(target)
        )

        try:

            ok = bitmap.compress(
                CompressFormat.JPEG,
                92,
                output_stream
            )

            output_stream.flush()

            if not ok:

                raise RuntimeError(
                    "Не удалось сохранить фотографию."
                )

        finally:

            output_stream.close()

        return str(
            target
        )

    @mainthread
    def _apply_product_photo(
        self,
        path
    ):

        screen = (
            self.pending_photo_screen
        )

        self.pending_photo_screen = None

        if screen is None:
            return

        screen.set_photo(
            path
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

            return

        if (
            request_code
            ==
            REQUEST_PICK_PRODUCT_PHOTO
        ):

            if (
                result_code == -1
                and
                intent is not None
            ):

                try:

                    uri = intent.getData()

                    if uri is not None:

                        path = (
                            self._copy_content_uri_to_photo(
                                uri
                            )
                        )

                        self._apply_product_photo(
                            path
                        )

                except Exception as exc:

                    self.pending_photo_screen = None

                    self.message(
                        "Ошибка выбора фото:\n\n"
                        +
                        str(exc)
                    )

            else:

                self.pending_photo_screen = None

            return

        if (
            request_code
            ==
            REQUEST_TAKE_PRODUCT_PHOTO
        ):

            if (
                result_code == -1
                and
                intent is not None
            ):

                try:

                    path = (
                        self._save_camera_thumbnail(
                            intent
                        )
                    )

                    self._apply_product_photo(
                        path
                    )

                except Exception as exc:

                    self.pending_photo_screen = None

                    self.message(
                        "Ошибка сохранения фото:\n\n"
                        +
                        str(exc)
                    )

            else:

                self.pending_photo_screen = None

            return

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

            self.current_department = None
            self.open_departments()

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

            self.current_department = None
            self.open_departments()

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

    def _open_rounded_dialog(
        self,
        message_text,
        title_text=APP_TITLE,
        confirm_text="OK",
        on_confirm=None,
        cancel_text=None,
    ):
        overlay = ModalView(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0.68),
            auto_dismiss=False,
        )

        card = RoundedPanel(
            orientation="vertical",
            size_hint=(0.88, None),
            height=dp(245 if cancel_text else 220),
            padding=dp(18),
            spacing=dp(14),
            bg_color=(0.12, 0.13, 0.15, 1),
            radius=24,
        )

        title = Label(
            text=f"[b]{title_text}[/b]",
            markup=True,
            color=TEXT,
            font_size="18sp",
            size_hint_y=None,
            height=dp(36),
            halign="left",
            valign="middle",
        )
        title.bind(
            size=lambda instance, value: setattr(instance, "text_size", value)
        )

        label = Label(
            text=message_text,
            color=TEXT,
            font_size="15sp",
            halign="left",
            valign="middle",
        )
        label.bind(
            size=lambda instance, value: setattr(instance, "text_size", (value[0], None))
        )

        buttons = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            spacing=dp(10),
        )

        if cancel_text:
            cancel = RoundedButton(
                text=cancel_text,
                font_size="15sp",
                normal_color=BUTTON_BG,
                down_color=BUTTON_BG_DOWN,
            )
            cancel.bind(on_release=lambda *_: overlay.dismiss())
            buttons.add_widget(cancel)

        confirm = RoundedButton(
            text=confirm_text,
            font_size="15sp",
            normal_color=ACCENT_RED if cancel_text else BUTTON_BG,
            down_color=ACCENT_RED_DOWN if cancel_text else BUTTON_BG_DOWN,
        )

        def do_confirm(*_):
            overlay.dismiss()
            if on_confirm:
                on_confirm()

        confirm.bind(on_release=do_confirm)
        buttons.add_widget(confirm)

        card.add_widget(title)
        card.add_widget(label)
        card.add_widget(buttons)

        wrapper = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
        )
        wrapper.add_widget(card)
        overlay.add_widget(wrapper)
        overlay.open()

    def message(
        self,
        text
    ):
        self._open_rounded_dialog(
            message_text=text,
            title_text=APP_TITLE,
            confirm_text="OK",
        )

    def confirm_delete_product(self, barcode):
        product = self.db.get_product(barcode)

        if not product:
            self.message("Товар не найден.")
            return

        name = product["name"] or barcode

        def do_delete():
            if self.db.delete_product_completely(barcode):
                # Удаляем также локально кэшированное изображение, если оно было.
                try:
                    cached = Path(self.get_cached_photo_path(barcode))
                    if cached.exists():
                        cached.unlink()
                except Exception:
                    pass
                self.open_home()
            else:
                self.message("Не удалось удалить товар.")

        self._open_rounded_dialog(
            message_text=(
                f"Удалить товар «{name}»?\n\n"
                "Будут удалены сам товар и все его сроки годности."
            ),
            title_text="Удалить товар",
            confirm_text="Удалить",
            cancel_text="Отмена",
            on_confirm=do_delete,
        )


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

            self.current_department = None
            self.open_departments()

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
