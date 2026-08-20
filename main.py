# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

# Barcode camera
try:
    from kivy_garden.zbarcam import ZBarCam
    ZBAR_AVAILABLE = True
except Exception:
    try:
        from zbarcam import ZBarCam
        ZBAR_AVAILABLE = True
    except Exception:
        ZBAR_AVAILABLE = False

# Android shared storage
if platform == "android":
    from android.permissions import request_permissions, Permission
    from androidstorage4kivy import Chooser, SharedStorage

APP_TITLE = "Сроки товаров"
DB_NAME = "inventory.db"
DATE_FMT = "%Y-%m-%d"
DISPLAY_FMT = "%d.%m.%Y"


def parse_date(text):
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime(DATE_FMT)
        except ValueError:
            pass
    return None


def show_date(value):
    if not value:
        return "—"
    try:
        return datetime.strptime(value, DATE_FMT).strftime(DISPLAY_FMT)
    except ValueError:
        return value


class DB:
    def __init__(self, path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.create()

    def create(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            photo_blob BLOB,
            photo_ext TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS expirations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            exp_date TEXT NOT NULL,
            written_off INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(barcode) REFERENCES products(barcode) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_barcode_date
        ON expirations(barcode, exp_date);
        """)
        self.conn.commit()

        # Migration from the previous version if it existed.
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(products)")}
        if "photo_blob" not in cols:
            self.conn.execute("ALTER TABLE products ADD COLUMN photo_blob BLOB")
        if "photo_ext" not in cols:
            self.conn.execute("ALTER TABLE products ADD COLUMN photo_ext TEXT NOT NULL DEFAULT ''")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def product(self, barcode):
        return self.conn.execute(
            "SELECT * FROM products WHERE barcode=?", (barcode,)
        ).fetchone()

    def save_product(self, barcode, name, photo_blob=None, photo_ext=""):
        old = self.product(barcode)
        if old:
            if photo_blob is None:
                photo_blob = old["photo_blob"]
            if not photo_ext:
                photo_ext = old["photo_ext"]
            self.conn.execute("""
                UPDATE products
                SET name=?, photo_blob=?, photo_ext=?
                WHERE barcode=?
            """, (name.strip(), photo_blob, photo_ext, barcode))
        else:
            self.conn.execute("""
                INSERT INTO products(barcode,name,photo_blob,photo_ext,created_at)
                VALUES(?,?,?,?,?)
            """, (
                barcode, name.strip(), photo_blob, photo_ext,
                datetime.now().isoformat(timespec="seconds")
            ))
        self.conn.commit()

    def add_expiration(self, barcode, exp_date):
        try:
            self.conn.execute("""
                INSERT INTO expirations(barcode,exp_date,written_off,created_at)
                VALUES(?,?,0,?)
            """, (
                barcode, exp_date,
                datetime.now().isoformat(timespec="seconds")
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def next_expiration(self, barcode):
        return self.conn.execute("""
            SELECT * FROM expirations
            WHERE barcode=? AND written_off=0
            ORDER BY exp_date,id
            LIMIT 1
        """, (barcode,)).fetchone()

    def all_expirations(self, barcode):
        return self.conn.execute("""
            SELECT * FROM expirations
            WHERE barcode=?
            ORDER BY written_off,exp_date,id
        """, (barcode,)).fetchall()

    def write_off(self, barcode):
        row = self.next_expiration(barcode)
        if not row:
            return False
        self.conn.execute(
            "UPDATE expirations SET written_off=1 WHERE id=?",
            (row["id"],)
        )
        self.conn.commit()
        return True

    def products(self):
        return self.conn.execute("""
            SELECT p.*,
                (
                    SELECT e.exp_date
                    FROM expirations e
                    WHERE e.barcode=p.barcode AND e.written_off=0
                    ORDER BY e.exp_date,e.id
                    LIMIT 1
                ) AS next_exp
            FROM products p
            ORDER BY
                CASE WHEN (
                    SELECT e2.exp_date
                    FROM expirations e2
                    WHERE e2.barcode=p.barcode AND e2.written_off=0
                    ORDER BY e2.exp_date,e2.id
                    LIMIT 1
                ) IS NULL THEN 1 ELSE 0 END,
                next_exp,p.name COLLATE NOCASE
        """).fetchall()

    def backup_to(self, target):
        target = Path(target)
        if target.exists():
            target.unlink()
        out = sqlite3.connect(str(target))
        with out:
            self.conn.backup(out)
        out.close()

    @staticmethod
    def validate(path):
        try:
            con = sqlite3.connect(str(path))
            tables = {
                r[0] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            ok = "products" in tables and "expirations" in tables
            con.close()
            return ok
        except Exception:
            return False


class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()


class HomeScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        box = self.ids.list_box
        box.clear_widgets()

        today = date.today()
        yesterday = today - timedelta(days=1)
        active = []
        empty = []

        for p in self.app.db.products():
            if p["next_exp"]:
                try:
                    d = datetime.strptime(p["next_exp"], DATE_FMT).date()
                except ValueError:
                    d = None
                if d:
                    active.append((p, d))
                else:
                    empty.append(p)
            else:
                empty.append(p)

        for p, d in active:
            box.add_widget(self.item(p, d, today, yesterday))

        if empty:
            title = Label(
                text="[color=777777]— СРОКОВ БОЛЬШЕ НЕТ —[/color]",
                markup=True, size_hint_y=None, height=dp(36),
                halign="center", valign="middle"
            )
            title.bind(size=lambda i, v: setattr(i, "text_size", v))
            box.add_widget(title)
            for p in empty:
                box.add_widget(self.item(p, None, today, yesterday))

    def item(self, p, d, today, yesterday):
        if d is None:
            bg, fg, status = (0.78,0.78,0.78,1), (0.25,0.25,0.25,1), "Сроков больше нет"
        elif d == today:
            bg, fg, status = (1.0,0.86,0.20,1), (0.1,0.1,0.1,1), "УЦЕНКА СЕГОДНЯ"
        elif d == yesterday:
            bg, fg, status = (0.92,0.22,0.18,1), (1,1,1,1), "ИСТЁК ВЧЕРА — СПИСАНИЕ"
        else:
            bg, fg, status = (0.94,0.94,0.94,1), (0.12,0.12,0.12,1), ""

        photo = "  📷" if p["photo_blob"] else ""
        text = (
            f"{p['name'] or 'Без названия'}{photo}\n"
            f"Срок: {show_date(p['next_exp'])}\n{status}"
        ).strip()

        b = Button(
            text=text, size_hint_y=None, height=dp(78),
            background_normal="", background_color=bg,
            color=fg, halign="left", valign="middle",
            padding=(dp(14), dp(6))
        )
        b.bind(size=lambda i, v: setattr(i, "text_size", (v[0]-dp(20), v[1])))
        b.bind(on_release=lambda *_: self.app.open_product(p["barcode"]))
        return b


class ProductScreen(BaseScreen):
    barcode = StringProperty("")

    def load(self, barcode):
        self.barcode = barcode
        p = self.app.db.product(barcode)
        if not p:
            return

        self.ids.title.text = p["name"] or "Без названия"
        self.ids.barcode.text = f"Штрихкод: {barcode}"

        active = [x for x in self.app.db.all_expirations(barcode) if not x["written_off"]]
        self.ids.next.text = (
            f"Ближайший срок: {show_date(active[0]['exp_date'])}"
            if active else "Активных сроков нет"
        )

        lines = []
        for x in self.app.db.all_expirations(barcode):
            lines.append(
                f"{show_date(x['exp_date'])} — "
                f"{'СПИСАНО' if x['written_off'] else 'АКТИВНО'}"
            )
        self.ids.history.text = "\n".join(lines) if lines else "Сроков нет"

        photo = p["photo_blob"]
        if photo:
            ext = p["photo_ext"] or ".jpg"
            path = Path(self.app.user_data_dir) / f"preview{ext}"
            path.write_bytes(photo)
            self.ids.photo.source = str(path)
            self.ids.photo.opacity = 1
        else:
            self.ids.photo.source = ""
            self.ids.photo.opacity = 0

        self.ids.writeoff.disabled = not bool(active)

    def write_off(self):
        if not self.app.db.write_off(self.barcode):
            self.app.message("Активного срока уже нет.")
            return
        self.app.message("Списано. Теперь показан следующий ближайший срок.")
        self.app.open_home()


class ScannerScreen(BaseScreen):
    _locked = False

    def on_enter(self, *_):
        self._locked = False
        if platform == "android":
            try:
                request_permissions([Permission.CAMERA])
            except Exception:
                pass

    def on_scanned(self, *_):
        if self._locked:
            return
        try:
            symbols = self.ids.zbar.symbols
        except Exception:
            return
        if not symbols:
            return

        value = symbols[0].data
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        value = str(value).strip()
        if not value:
            return

        self._locked = True
        Clock.schedule_once(lambda dt: self.app.open_edit(value), 0.1)

    def manual(self):
        content = BoxLayout(
            orientation="vertical", padding=dp(12),
            spacing=dp(10)
        )
        field = TextInput(
            hint_text="Штрихкод", multiline=False,
            input_filter="int", size_hint_y=None, height=dp(50)
        )
        ok = Button(text="Продолжить", size_hint_y=None, height=dp(48))
        cancel = Button(text="Отмена", size_hint_y=None, height=dp(48))
        content.add_widget(field)
        content.add_widget(ok)
        content.add_widget(cancel)

        pop = Popup(
            title="Ввести штрихкод",
            content=content,
            size_hint=(0.9, None), height=dp(250),
            auto_dismiss=False
        )

        def go(*_):
            if not field.text.strip():
                self.app.message("Введите штрихкод.")
                return
            pop.dismiss()
            self.app.open_edit(field.text.strip())

        ok.bind(on_release=go)
        cancel.bind(on_release=pop.dismiss)
        pop.open()


class EditScreen(BaseScreen):
    barcode = StringProperty("")
    photo_blob = None
    photo_ext = ""

    def load(self, barcode):
        self.barcode = barcode
        self.photo_blob = None
        self.photo_ext = ""

        self.ids.barcode.text = barcode
        self.ids.name.text = ""
        self.ids.date.text = ""
        self.ids.photo_info.text = "Фото не выбрано"

        p = self.app.db.product(barcode)
        if p:
            self.ids.name.text = p["name"] or ""
            if p["photo_blob"]:
                self.photo_blob = p["photo_blob"]
                self.photo_ext = p["photo_ext"] or ".jpg"
                self.ids.photo_info.text = "Фото уже сохранено"

    def save(self):
        barcode = self.ids.barcode.text.strip()
        name = self.ids.name.text.strip()
        exp = parse_date(self.ids.date.text)

        if not barcode:
            self.app.message("Введите штрихкод.")
            return
        if not name:
            self.app.message("Введите название товара.")
            return
        if not exp:
            self.app.message("Дата должна быть в формате ДД.ММ.ГГГГ.")
            return

        self.app.db.save_product(
            barcode, name, self.photo_blob, self.photo_ext
        )
        if not self.app.db.add_expiration(barcode, exp):
            self.app.message("Такой срок у этого товара уже есть.")
            return

        self.app.message(
            f"Срок {show_date(exp)} сохранён. "
            "В списке будет отображаться только ближайший."
        )
        self.app.open_home()


class MainApp(App):
    title = APP_TITLE

    def build(self):
        Window.softinput_mode = "below_target"
        self.db = DB(Path(self.user_data_dir) / DB_NAME)

        if platform == "android":
            self.chooser = Chooser(self._import_callback)
            self.photo_chooser = Chooser(self._photo_callback)

        sm = ScreenManager(transition=FadeTransition(duration=0.12))
        sm.add_widget(self.home_screen())
        sm.add_widget(self.product_screen())
        sm.add_widget(self.scanner_screen())
        sm.add_widget(self.edit_screen())
        self.sm = sm
        return sm

    # ---------- Screens ----------
    def home_screen(self):
        s = HomeScreen(name="home")
        root = BoxLayout(
            orientation="vertical", padding=dp(10), spacing=dp(8)
        )

        top = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        title = Label(
            text=APP_TITLE, bold=True, font_size="21sp",
            halign="left", valign="middle"
        )
        title.bind(size=lambda i, v: setattr(i, "text_size", v))
        add = Button(text="+ Добавить срок")
        add.bind(on_release=lambda *_: self.open_scanner())
        export = Button(text="Экспорт БД")
        export.bind(on_release=lambda *_: self.export_db())
        imp = Button(text="Импорт БД")
        imp.bind(on_release=lambda *_: self.import_db())

        top.add_widget(title)
        top.add_widget(add)
        top.add_widget(export)
        top.add_widget(imp)
        root.add_widget(top)

        scroll = ScrollView()
        box = BoxLayout(
            orientation="vertical", spacing=dp(7),
            size_hint_y=None
        )
        box.bind(minimum_height=box.setter("height"))
        scroll.add_widget(box)
        root.add_widget(scroll)

        s.ids = {"list_box": box}
        s.add_widget(root)
        return s

    def product_screen(self):
        s = ProductScreen(name="product")
        root = BoxLayout(
            orientation="vertical", padding=dp(12), spacing=dp(8)
        )

        back = Button(text="← Назад", size_hint_y=None, height=dp(45))
        back.bind(on_release=lambda *_: self.open_home())
        root.add_widget(back)

        photo = Image(size_hint_y=None, height=dp(170), opacity=0)
        title = Label(
            font_size="23sp", bold=True,
            size_hint_y=None, height=dp(45)
        )
        barcode = Label(size_hint_y=None, height=dp(28))
        next_label = Label(size_hint_y=None, height=dp(32))

        root.add_widget(photo)
        root.add_widget(title)
        root.add_widget(barcode)
        root.add_widget(next_label)
        root.add_widget(Label(
            text="История сроков:", bold=True,
            size_hint_y=None, height=dp(28)
        ))

        hist_scroll = ScrollView()
        history = Label(
            text="Сроков нет", halign="left", valign="top",
            size_hint_y=None
        )
        history.bind(
            texture_size=lambda i, v: setattr(i, "height", max(dp(70), v[1]))
        )
        hist_scroll.add_widget(history)
        root.add_widget(hist_scroll)

        writeoff = Button(
            text="Списано", size_hint_y=None, height=dp(55),
            background_normal="", background_color=(0.86,0.18,0.16,1)
        )
        writeoff.bind(on_release=lambda *_: s.write_off())
        root.add_widget(writeoff)

        s.ids = {
            "photo": photo, "title": title, "barcode": barcode,
            "next": next_label, "history": history, "writeoff": writeoff
        }
        s.add_widget(root)
        return s

    def scanner_screen(self):
        s = ScannerScreen(name="scanner")
        root = BoxLayout(orientation="vertical")

        top = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        back = Button(text="← Назад")
        back.bind(on_release=lambda *_: self.open_home())
        manual = Button(text="Ввести вручную")
        manual.bind(on_release=lambda *_: s.manual())
        top.add_widget(back)
        top.add_widget(manual)
        root.add_widget(top)

        if ZBAR_AVAILABLE:
            zbar = ZBarCam(
                code_types=(
                    "EAN13", "EAN8", "UPCA", "UPCE",
                    "CODE128", "CODE39", "QRCODE"
                )
            )
            zbar.bind(symbols=s.on_scanned)
            root.add_widget(zbar)
            s.ids = {"zbar": zbar}
        else:
            msg = Label(
                text="Камера-сканер не собрана.\nИспользуйте «Ввести вручную».",
                halign="center", valign="middle"
            )
            msg.bind(size=lambda i, v: setattr(i, "text_size", v))
            root.add_widget(msg)
            s.ids = {}

        s.add_widget(root)
        return s

    def edit_screen(self):
        s = EditScreen(name="edit")
        root = BoxLayout(
            orientation="vertical", padding=dp(12), spacing=dp(8)
        )

        back = Button(text="← Назад", size_hint_y=None, height=dp(45))
        back.bind(on_release=lambda *_: self.open_scanner())
        root.add_widget(back)

        root.add_widget(Label(
            text="Данные товара", font_size="22sp", bold=True,
            size_hint_y=None, height=dp(42)
        ))

        name = TextInput(
            hint_text="Наименование товара", multiline=False,
            size_hint_y=None, height=dp(50)
        )
        barcode = TextInput(
            hint_text="Штрихкод", multiline=False, input_filter="int",
            size_hint_y=None, height=dp(50)
        )
        exp = TextInput(
            hint_text="Срок годности ДД.ММ.ГГГГ", multiline=False,
            size_hint_y=None, height=dp(50)
        )

        root.add_widget(name)
        root.add_widget(barcode)
        root.add_widget(exp)

        # Photo is optional and stored inside the DB as BLOB,
        # so an exported database remains self-contained.
        photo_btn = Button(
            text="Выбрать фото (необязательно)",
            size_hint_y=None, height=dp(48)
        )
        photo_btn.bind(on_release=lambda *_: self.choose_photo(s))
        root.add_widget(photo_btn)

        photo_info = Label(
            text="Фото не выбрано", size_hint_y=None, height=dp(30)
        )
        root.add_widget(photo_info)

        root.add_widget(Widget())

        save = Button(
            text="Сохранить срок", size_hint_y=None, height=dp(55),
            background_normal="", background_color=(0.15,0.58,0.26,1)
        )
        save.bind(on_release=lambda *_: s.save())
        root.add_widget(save)

        s.ids = {
            "name": name, "barcode": barcode,
            "date": exp, "photo_info": photo_info
        }
        s.add_widget(root)
        return s

    # ---------- Navigation ----------
    def open_home(self):
        self.sm.current = "home"
        self.sm.get_screen("home").refresh()

    def open_scanner(self):
        self.sm.current = "scanner"

    def open_edit(self, barcode):
        self.sm.current = "edit"
        self.sm.get_screen("edit").load(barcode)

    def open_product(self, barcode):
        self.sm.current = "product"
        self.sm.get_screen("product").load(barcode)

    # ---------- Product photo ----------
    def choose_photo(self, screen):
        if platform == "android":
            self.photo_chooser.choose_content("image/*")
            return

        from kivy.uix.filechooser import FileChooserListView
        chooser = FileChooserListView(
            path=str(Path.home()),
            filters=["*.png", "*.jpg", "*.jpeg", "*.webp"]
        )
        ok = Button(text="Выбрать", size_hint_y=None, height=dp(48))
        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)
        box.add_widget(ok)
        pop = Popup(
            title="Выберите фото товара",
            content=box, size_hint=(0.95, 0.9)
        )

        def pick(*_):
            if chooser.selection:
                self._set_photo_from_path(screen, chooser.selection[0])
                pop.dismiss()

        ok.bind(on_release=pick)
        pop.open()

    def _photo_callback(self, files):
        if not files:
            return
        try:
            private = SharedStorage().copy_from_shared(files[0])
            if private:
                Clock.schedule_once(
                    lambda dt: self._set_photo_from_path(
                        self.sm.get_screen("edit"), private
                    ), 0
                )
        except Exception as exc:
            self.message(f"Ошибка выбора фото:\n{exc}")

    def _set_photo_from_path(self, screen, path):
        try:
            path = Path(path)
            data = path.read_bytes()
            if not data:
                self.message("Фото пустое.")
                return
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                self.message("Поддерживаются PNG, JPG, JPEG и WEBP.")
                return
            screen.photo_blob = data
            screen.photo_ext = path.suffix.lower()
            screen.ids.photo_info.text = f"Фото выбрано: {path.name}"
        except Exception as exc:
            self.message(f"Не удалось прочитать фото:\n{exc}")

    # ---------- Database export/import ----------
    def export_db(self):
        self.db.conn.commit()
        temp = Path(self.user_data_dir) / "inventory_export.db"
        self.db.backup_to(temp)

        filename = f"inventory_{date.today().strftime('%Y%m%d')}.db"

        if platform == "android":
            try:
                ss = SharedStorage()
                shared = ss.copy_to_shared(
                    str(temp),
                    collection="Documents",
                    filepath=f"/{filename}"
                )
                if shared:
                    self.message(
                        f"База экспортирована в Documents:\n{filename}"
                    )
                else:
                    self.message("Android не смог сохранить файл.")
            except Exception as exc:
                self.message(f"Ошибка экспорта:\n{exc}")
        else:
            # Desktop fallback: put it next to the app.
            dest = Path.cwd() / filename
            shutil.copy2(temp, dest)
            self.message(f"База сохранена:\n{dest}")

        try:
            temp.unlink()
        except OSError:
            pass

    def import_db(self):
        if platform == "android":
            self.chooser.choose_content("*/*")
        else:
            # Desktop fallback using Kivy file chooser.
            content = BoxLayout(orientation="vertical")
            from kivy.uix.filechooser import FileChooserListView
            chooser = FileChooserListView(
                path=str(Path.cwd()),
                filters=["*.db", "*.sqlite", "*.sqlite3"]
            )
            ok = Button(text="Импортировать", size_hint_y=None, height=dp(48))
            content.add_widget(chooser)
            content.add_widget(ok)
            pop = Popup(
                title="Выберите базу данных",
                content=content,
                size_hint=(0.95, 0.9)
            )

            def pick(*_):
                if chooser.selection:
                    pop.dismiss()
                    self._replace_with_file(chooser.selection[0])

            ok.bind(on_release=pick)
            pop.open()

    def _import_callback(self, files):
        if not files:
            return
        try:
            ss = SharedStorage()
            private = ss.copy_from_shared(files[0])
            if private:
                Clock.schedule_once(
                    lambda dt: self._replace_with_file(private), 0
                )
        except Exception as exc:
            self.message(f"Ошибка чтения базы:\n{exc}")

    def _replace_with_file(self, source):
        source = Path(source)
        if not source.exists():
            self.message("Файл базы не найден.")
            return
        if source.suffix.lower() not in (".db", ".sqlite", ".sqlite3"):
            self.message("Выберите файл .db, .sqlite или .sqlite3.")
            return
        if not DB.validate(source):
            self.message(
                "Файл не похож на базу этого приложения.\n"
                "Нужны таблицы products и expirations."
            )
            return

        backup = Path(self.user_data_dir) / "inventory_before_import.db"
        self.db.backup_to(backup)
        self.db.close()

        try:
            shutil.copy2(source, Path(self.user_data_dir) / DB_NAME)
            self.db = DB(Path(self.user_data_dir) / DB_NAME)
        except Exception as exc:
            try:
                shutil.copy2(backup, Path(self.user_data_dir) / DB_NAME)
                self.db = DB(Path(self.user_data_dir) / DB_NAME)
            except Exception:
                pass
            self.message(f"Импорт не удался:\n{exc}")
            return
        finally:
            try:
                backup.unlink()
            except OSError:
                pass

        self.message("База импортирована.")
        self.open_home()

    def message(self, text):
        content = BoxLayout(
            orientation="vertical", padding=dp(12), spacing=dp(10)
        )
        label = Label(text=text, halign="left", valign="middle")
        label.bind(size=lambda i, v: setattr(i, "text_size", v))
        ok = Button(text="OK", size_hint_y=None, height=dp(48))
        content.add_widget(label)
        content.add_widget(ok)

        pop = Popup(
            title="Сроки товаров", content=content,
            size_hint=(0.9, 0.55), auto_dismiss=False
        )
        ok.bind(on_release=pop.dismiss)
        pop.open()

    def on_stop(self):
        if hasattr(self, "db"):
            self.db.close()


if __name__ == "__main__":
    MainApp().run()
