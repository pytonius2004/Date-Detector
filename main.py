import os
import json
import shutil
from datetime import date, datetime, timedelta

os.environ.setdefault("KIVY_GL_BACKEND", "sdl2")
os.environ.setdefault("KIVY_GRAPHICS", "gles")
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "0")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.metrics import dp

# ---------------------------------------------------------
# Android permissions
# ---------------------------------------------------------

try:
    from android.permissions import request_permissions, check_permission, Permission
except Exception:
    request_permissions = None
    check_permission = None
    Permission = None

# ---------------------------------------------------------
# Android Java / ML Kit
# ---------------------------------------------------------

try:
    from jnius import autoclass, PythonJavaClass, java_method
except Exception:
    autoclass = None
    PythonJavaClass = None
    java_method = None

# ---------------------------------------------------------
# File chooser
# ---------------------------------------------------------

try:
    from plyer import filechooser
except Exception:
    filechooser = None


DATE_FORMAT = "%d.%m.%Y"


# =========================================================
# Helpers
# =========================================================

def parse_date(value):
    return datetime.strptime(value.strip(), DATE_FORMAT).date()


def format_date(value):
    return value.strftime(DATE_FORMAT)


# =========================================================
# Database
# =========================================================

class DataStore:

    def __init__(self, path):
        self.path = path
        self.data = {
            "products": {}
        }
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                self.data = json.load(file)

            if "products" not in self.data:
                self.data["products"] = {}

        except Exception:
            self.data = {
                "products": {}
            }

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        temp_path = self.path + ".tmp"

        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                self.data,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_path, self.path)

    def get_product(self, barcode):
        return self.data["products"].get(barcode)

    def create_or_update_product(
        self,
        barcode,
        name="",
        photo=""
    ):
        products = self.data["products"]

        if barcode not in products:
            products[barcode] = {
                "barcode": barcode,
                "name": name.strip() or "Без названия",
                "photo": photo or "",
                "dates": []
            }

        else:
            product = products[barcode]

            if name.strip():
                product["name"] = name.strip()

            if photo:
                product["photo"] = photo

        return products[barcode]

    def add_expiry(
        self,
        barcode,
        name,
        expiry,
        photo=""
    ):
        product = self.create_or_update_product(
            barcode=barcode,
            name=name,
            photo=photo
        )

        product["dates"].append({
            "date": expiry.isoformat(),
            "added_at": datetime.now().isoformat()
        })

        product["dates"].sort(
            key=lambda item: item["date"]
        )

        self.save()

    def get_nearest_expiry(self, product):

        dates = product.get("dates", [])

        if not dates:
            return None

        valid_dates = []

        for item in dates:
            try:
                date.fromisoformat(item["date"])
                valid_dates.append(item)
            except Exception:
                pass

        if not valid_dates:
            return None

        return min(
            valid_dates,
            key=lambda item: item["date"]
        )

    def write_off_nearest(self, barcode):

        product = self.get_product(barcode)

        if not product:
            return False

        if not product.get("dates"):
            return False

        nearest = self.get_nearest_expiry(product)

        if nearest is None:
            return False

        product["dates"].remove(nearest)

        self.save()

        return True


# =========================================================
# Main screen
# =========================================================

class MainScreen(Screen):

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):

        app = App.get_running_app()

        container = self.ids.products_box

        container.clear_widgets()

        active_products = []
        completed_products = []

        today = date.today()

        for barcode, product in app.store.data["products"].items():

            nearest = app.store.get_nearest_expiry(product)

            if nearest:

                try:
                    expiry = date.fromisoformat(
                        nearest["date"]
                    )
                except Exception:
                    continue

                active_products.append(
                    (expiry, product)
                )

            else:
                completed_products.append(product)

        # Ближайшие сроки сверху
        active_products.sort(
            key=lambda item: (
                item[0],
                item[1].get("name", "").lower()
            )
        )

        completed_products.sort(
            key=lambda product:
            product.get("name", "").lower()
        )

        if not active_products and not completed_products:

            container.add_widget(
                Label(
                    text=(
                        "Пока нет товаров.\n\n"
                        "Нажмите «Добавить срок»"
                    ),
                    color=(0.65, 0.67, 0.72, 1),
                    font_size="18sp",
                    size_hint_y=None,
                    height=dp(140),
                    halign="center",
                    valign="middle"
                )
            )

            return

        for expiry, product in active_products:

            container.add_widget(
                ProductRow(
                    product=product,
                    expiry=expiry,
                    archived=False
                )
            )

        if completed_products:

            container.add_widget(
                Label(
                    text="СПИСАНО",
                    color=(0.45, 0.47, 0.52, 1),
                    font_size="13sp",
                    size_hint_y=None,
                    height=dp(40),
                    halign="left",
                    valign="middle"
                )
            )

            for product in completed_products:

                container.add_widget(
                    ProductRow(
                        product=product,
                        expiry=None,
                        archived=True
                    )
                )


# =========================================================
# Product row
# =========================================================

class ProductRow(BoxLayout):

    def __init__(
        self,
        product,
        expiry,
        archived=False,
        **kwargs
    ):

        super().__init__(
            orientation="horizontal",
            spacing=dp(10),
            padding=[
                dp(10),
                dp(8)
            ],
            size_hint_y=None,
            height=dp(88),
            **kwargs
        )

        self.product = product
        self.expiry = expiry
        self.archived = archived

        # Background
        with self.canvas.before:

            self.background_color = Color(
                *self.get_background_color()
            )

            self.background_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[12]
            )

        self.bind(
            pos=self.update_background,
            size=self.update_background
        )

        # Photo
        photo = product.get("photo", "")

        if photo and os.path.exists(photo):

            image = Image(
                source=photo,
                size_hint_x=None,
                width=dp(62),
                allow_stretch=True,
                keep_ratio=True
            )

        else:

            image = Label(
                text="📦",
                size_hint_x=None,
                width=dp(62),
                font_size="30sp",
                color=(
                    0.38,
                    0.40,
                    0.45,
                    1
                )
            )

        self.add_widget(image)

        # Middle
        middle = BoxLayout(
            orientation="vertical",
            spacing=dp(2)
        )

        title_color = (
            (0.45, 0.47, 0.52, 1)
            if archived
            else (0.92, 0.93, 0.96, 1)
        )

        middle.add_widget(
            Label(
                text=product.get(
                    "name",
                    "Без названия"
                ),
                color=title_color,
                font_size="17sp",
                bold=True,
                halign="left",
                valign="middle"
            )
        )

        middle.add_widget(
            Label(
                text=product.get(
                    "barcode",
                    ""
                ),
                color=(
                    0.48,
                    0.50,
                    0.56,
                    1
                ),
                font_size="12sp",
                halign="left"
            )
        )

        self.add_widget(middle)

        # Right
        right = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(125),
            spacing=dp(2)
        )

        if expiry:

            color = self.get_date_color()

            right.add_widget(
                Label(
                    text=format_date(expiry),
                    color=color,
                    bold=True,
                    font_size="15sp"
                )
            )

            right.add_widget(
                Label(
                    text=self.get_status_text(),
                    color=color,
                    font_size="10sp"
                )
            )

        else:

            right.add_widget(
                Label(
                    text="ВСЁ СПИСАНО",
                    color=(
                        0.48,
                        0.50,
                        0.55,
                        1
                    ),
                    bold=True,
                    font_size="11sp"
                )
            )

        self.add_widget(right)

    def on_touch_down(self, touch):

        if self.collide_point(
            *touch.pos
        ):

            App.get_running_app().open_product(
                self.product["barcode"]
            )

            return True

        return super().on_touch_down(touch)

    def get_background_color(self):

        if self.archived:

            return (
                0.12,
                0.13,
                0.16,
                1
            )

        if self.expiry == date.today():

            return (
                0.38,
                0.29,
                0.05,
                1
            )

        if self.expiry == (
            date.today() -
            timedelta(days=1)
        ):

            return (
                0.40,
                0.10,
                0.10,
                1
            )

        return (
            0.11,
            0.12,
            0.15,
            1
        )

    def get_date_color(self):

        if self.expiry == date.today():

            return (
                1.0,
                0.82,
                0.20,
                1
            )

        if self.expiry == (
            date.today() -
            timedelta(days=1)
        ):

            return (
                1.0,
                0.35,
                0.35,
                1
            )

        return (
            0.80,
            0.82,
            0.88,
            1
        )

    def get_status_text(self):

        if self.expiry == date.today():
            return "УЦЕНКА СЕГОДНЯ"

        if self.expiry == (
            date.today() -
            timedelta(days=1)
        ):
            return "ИСТЁК ВЧЕРА"

        if self.expiry < date.today():
            return "ИСТЁК"

        return "СРОК ГОДНОСТИ"

    def update_background(self, *_):

        self.background_rect.pos = self.pos
        self.background_rect.size = self.size


# =========================================================
# Add product screen
# =========================================================

class AddScreen(Screen):

    photo_path = ""

    def on_enter(self, *args):
        pass

    def set_barcode(self, barcode):

        self.ids.barcode.text = barcode

        self.prefill_product()

    def prefill_product(self, *args):

        barcode = self.ids.barcode.text.strip()

        if not barcode:
            return

        app = App.get_running_app()

        product = app.store.get_product(
            barcode
        )

        if not product:
            return

        self.ids.name.text = product.get(
            "name",
            ""
        )

        self.photo_path = product.get(
            "photo",
            ""
        )

        if self.photo_path:

            self.ids.photo_preview.source = (
                self.photo_path
            )

            self.ids.photo_preview.reload()

    def save_product(self):

        app = App.get_running_app()

        barcode = self.ids.barcode.text.strip()
        name = self.ids.name.text.strip()
        expiry_text = self.ids.expiry.text.strip()

        if not barcode:

            app.show_message(
                "Ошибка",
                "Введите штрих-код."
            )

            return

        if not name:

            app.show_message(
                "Ошибка",
                "Введите название товара."
            )

            return

        try:

            expiry = parse_date(
                expiry_text
            )

        except Exception:

            app.show_message(
                "Ошибка",
                "Дата должна быть в формате:\nДД.ММ.ГГГГ"
            )

            return

        app.store.add_expiry(
            barcode=barcode,
            name=name,
            expiry=expiry,
            photo=self.photo_path
        )

        self.reset_form()

        app.sm.current = "main"

        app.sm.get_screen(
            "main"
        ).refresh()

    def reset_form(self):

        self.ids.barcode.text = ""
        self.ids.name.text = ""
        self.ids.expiry.text = ""

        self.photo_path = ""

        self.ids.photo_preview.source = ""

    def choose_photo(self):

        if filechooser is None:

            App.get_running_app().show_message(
                "Фото",
                "Выбор фото недоступен."
            )

            return

        try:

            filechooser.open_file(
                on_selection=self.photo_selected
            )

        except Exception as error:

            App.get_running_app().show_message(
                "Фото",
                str(error)
            )

    def photo_selected(self, selection):

        if not selection:
            return

        source = selection[0]

        try:

            extension = (
                os.path.splitext(source)[1]
                .lower()
            )

            if not extension:
                extension = ".jpg"

            photo_dir = os.path.join(
                App.get_running_app().user_data_dir,
                "photos"
            )

            os.makedirs(
                photo_dir,
                exist_ok=True
            )

            destination = os.path.join(
                photo_dir,
                "product_" +
                str(abs(hash(source))) +
                extension
            )

            shutil.copy2(
                source,
                destination
            )

            self.photo_path = destination

            self.ids.photo_preview.source = (
                destination
            )

            self.ids.photo_preview.reload()

        except Exception as error:

            App.get_running_app().show_message(
                "Фото",
                "Не удалось добавить фото:\n" +
                str(error)
            )


# =========================================================
# Manual barcode
# =========================================================

class ManualScreen(Screen):

    def submit(self):

        barcode = (
            self.ids.manual_barcode.text
            .strip()
        )

        if not barcode:

            App.get_running_app().show_message(
                "Ошибка",
                "Введите штрих-код."
            )

            return

        add_screen = (
            App.get_running_app()
            .sm
            .get_screen("add")
        )

        add_screen.reset_form()
        add_screen.set_barcode(barcode)

        self.ids.manual_barcode.text = ""

        App.get_running_app().sm.current = "add"


# =========================================================
# Barcode scanner
# =========================================================

class ScannerScreen(Screen):

    scanning = False
    last_barcode = ""

    def on_enter(self, *args):

        app = App.get_running_app()

        if app.camera_permission_granted():

            self.start_camera()

        else:

            app.request_camera_permission()

            Clock.schedule_once(
                self.check_permission_after_request,
                1.0
            )

    def check_permission_after_request(self, dt):

        app = App.get_running_app()

        if app.camera_permission_granted():

            self.start_camera()

        else:

            self.ids.status.text = (
                "Нет доступа к камере.\n"
                "Разрешите камеру в настройках Android."
            )

    def on_leave(self, *args):

        self.stop_camera()

    def start_camera(self):

        if self.scanning:
            return

        self.scanning = True

        self.ids.camera.play = True

        self.ids.status.text = (
            "Наведите камеру на штрих-код"
        )

        Clock.schedule_interval(
            self.scan_frame,
            0.8
        )

    def stop_camera(self):

        self.scanning = False

        Clock.unschedule(
            self.scan_frame
        )

        try:
            self.ids.camera.play = False
        except Exception:
            pass

    def manual_input(self):

        self.stop_camera()

        App.get_running_app().sm.current = (
            "manual"
        )

    def scan_frame(self, dt):

        if not self.scanning:
            return

        if autoclass is None:
            return

        texture = self.ids.camera.texture

        if texture is None:
            return

        try:

            frame_path = os.path.join(
                App.get_running_app().user_data_dir,
                "barcode_scan.jpg"
            )

            texture.save(
                frame_path,
                flipped=False,
                imagefmt="jpg"
            )

            self.scan_with_mlkit(
                frame_path
            )

        except Exception:
            pass

    def scan_with_mlkit(self, frame_path):

        try:

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            Uri = autoclass(
                "android.net.Uri"
            )

            InputImage = autoclass(
                "com.google.mlkit.vision.common.InputImage"
            )

            BarcodeScanning = autoclass(
                "com.google.mlkit.vision.barcode.BarcodeScanning"
            )

            Barcode = autoclass(
                "com.google.mlkit.vision.barcode.common.Barcode"
            )

            options_builder = (
                BarcodeScanning
                .getClient()
            )

            scanner = options_builder

            uri = Uri.parse(
                "file://" + frame_path
            )

            image = InputImage.fromFilePath(
                PythonActivity.mActivity,
                uri
            )

            screen = self

            class SuccessListener(
                PythonJavaClass
            ):

                __javainterfaces__ = [
                    "com/google/android/gms/tasks/OnSuccessListener"
                ]

                __javacontext__ = "app"

                @java_method(
                    "(Ljava/lang/Object;)V"
                )
                def onSuccess(
                    self,
                    result
                ):

                    try:

                        for barcode in result:

                            value = (
                                barcode.getRawValue()
                            )

                            if value:

                                Clock.schedule_once(
                                    lambda dt,
                                    v=str(value):
                                    screen.barcode_found(v),
                                    0
                                )

                                break

                    except Exception:
                        pass

            class FailureListener(
                PythonJavaClass
            ):

                __javainterfaces__ = [
                    "com/google/android/gms/tasks/OnFailureListener"
                ]

                __javacontext__ = "app"

                @java_method(
                    "(Ljava/lang/Exception;)V"
                )
                def onFailure(
                    self,
                    exception
                ):
                    pass

            self._success_listener = (
                SuccessListener()
            )

            self._failure_listener = (
                FailureListener()
            )

            scanner.process(
                image
            ).addOnSuccessListener(
                self._success_listener
            ).addOnFailureListener(
                self._failure_listener
            )

        except Exception:
            pass

    def barcode_found(self, value):

        if not self.scanning:
            return

        if not value:
            return

        if value == self.last_barcode:
            return

        self.last_barcode = value

        self.stop_camera()

        add_screen = (
            App.get_running_app()
            .sm
            .get_screen("add")
        )

        add_screen.reset_form()
        add_screen.set_barcode(value)

        App.get_running_app().sm.current = (
            "add"
        )


# =========================================================
# Product information
# =========================================================

class ProductScreen(Screen):

    barcode = StringProperty("")

    def on_enter(self, *args):

        self.refresh()

    def refresh(self):

        app = App.get_running_app()

        product = app.store.get_product(
            self.barcode
        )

        if not product:

            app.go_main()

            return

        self.ids.name.text = product.get(
            "name",
            "Без названия"
        )

        self.ids.barcode_label.text = (
            "Штрих-код: " +
            product.get(
                "barcode",
                ""
            )
        )

        photo = product.get(
            "photo",
            ""
        )

        if photo and os.path.exists(photo):

            self.ids.photo.source = photo
            self.ids.photo.reload()

        else:

            self.ids.photo.source = ""

        dates = []

        for item in product.get(
            "dates",
            []
        ):

            try:

                dates.append(
                    date.fromisoformat(
                        item["date"]
                    )
                )

            except Exception:
                pass

        dates.sort()

        if dates:

            nearest = dates[0]

            self.ids.nearest.text = (
                "Ближайший срок: " +
                format_date(nearest)
            )

            self.ids.dates.text = (
                "Активных сроков: " +
                str(len(dates))
            )

            self.ids.writeoff.disabled = False

        else:

            self.ids.nearest.text = (
                "Все сроки списаны"
            )

            self.ids.dates.text = (
                "Активных сроков: 0"
            )

            self.ids.writeoff.disabled = True

    def write_off(self):

        app = App.get_running_app()

        success = (
            app.store.write_off_nearest(
                self.barcode
            )
        )

        if not success:

            app.show_message(
                "Списание",
                "У этого товара нет активных сроков."
            )

            return

        self.refresh()

        app.sm.get_screen(
            "main"
        ).refresh()

        app.show_message(
            "Готово",
            "Товар списан.\n"
            "Если есть следующий срок, "
            "он теперь будет отображаться."
        )


# =========================================================
# KV layout
# =========================================================

KV = r'''
#:import dp kivy.metrics.dp


<MainScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(14)
        spacing: dp(10)

        canvas.before:

            Color:
                rgba: .055, .06, .075, 1

            Rectangle:
                pos: self.pos
                size: self.size


        BoxLayout:

            size_hint_y: None
            height: dp(56)

            Label:

                text: "Сроки товаров"

                color:
                    .95, .96, 1, 1

                font_size: "24sp"

                bold: True

                halign: "left"

                valign: "middle"


            Button:

                text: "+ Добавить срок"

                size_hint_x: None
                width: dp(160)

                background_normal: ""

                background_color:
                    .16, .35, .78, 1

                on_release:
                    app.open_scanner()


        ScrollView:

            do_scroll_x: False

            bar_width: dp(4)

            GridLayout:

                id: products_box

                cols: 1

                spacing: dp(8)

                padding: dp(2)

                size_hint_y: None

                height:
                    self.minimum_height


<ScannerScreen>:

    BoxLayout:

        orientation: "vertical"

        canvas.before:

            Color:
                rgba: .03, .035, .045, 1

            Rectangle:
                pos: self.pos
                size: self.size


        BoxLayout:

            size_hint_y: None
            height: dp(58)

            padding: dp(8)

            Button:

                text: "← Назад"

                size_hint_x: None
                width: dp(90)

                on_release:
                    app.go_main()


            Label:

                text: "Сканирование"

                font_size: "20sp"

                bold: True


            Widget:

                size_hint_x: None
                width: dp(90)


        Camera:

            id: camera

            resolution:
                (1280, 720)

            play: False

            index: 0


        Label:

            id: status

            text:
                "Наведите камеру на штрих-код"

            size_hint_y: None

            height: dp(45)

            color:
                .8, .82, .88, 1


        Button:

            text: "Ввести вручную"

            size_hint_y: None

            height: dp(56)

            on_release:
                root.manual_input()


<ManualScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(18)

        spacing: dp(12)

        canvas.before:

            Color:
                rgba: .055, .06, .075, 1

            Rectangle:
                pos: self.pos
                size: self.size


        Label:

            text: "Введите штрих-код"

            font_size: "24sp"

            bold: True

            size_hint_y: None

            height: dp(55)


        TextInput:

            id: manual_barcode

            hint_text: "Штрих-код"

            multiline: False

            input_type: "number"

            font_size: "22sp"

            size_hint_y: None

            height: dp(55)


        Button:

            text: "Продолжить"

            size_hint_y: None

            height: dp(55)

            background_normal: ""

            background_color:
                .16, .35, .78, 1

            on_release:
                root.submit()


        Widget:


        Button:

            text: "Назад"

            size_hint_y: None

            height: dp(50)

            on_release:
                app.go_main()


<AddScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(16)

        spacing: dp(10)

        canvas.before:

            Color:
                rgba: .055, .06, .075, 1

            Rectangle:
                pos: self.pos
                size: self.size


        BoxLayout:

            size_hint_y: None

            height: dp(52)

            Button:

                text: "← Назад"

                size_hint_x: None

                width: dp(90)

                on_release:
                    app.go_main()


            Label:

                text: "Добавить срок"

                font_size: "21sp"

                bold: True


        TextInput:

            id: barcode

            hint_text: "Штрих-код"

            multiline: False

            input_type: "number"

            size_hint_y: None

            height: dp(52)

            font_size: "19sp"

            on_text:
                root.prefill_product()


        TextInput:

            id: name

            hint_text: "Название товара"

            multiline: False

            size_hint_y: None

            height: dp(52)

            font_size: "18sp"


        TextInput:

            id: expiry

            hint_text: "Срок годности: ДД.ММ.ГГГГ"

            multiline: False

            size_hint_y: None

            height: dp(52)

            font_size: "18sp"


        BoxLayout:

            size_hint_y: None

            height: dp(150)

            spacing: dp(10)


            Image:

                id: photo_preview

                allow_stretch: True

                keep_ratio: True


            Button:

                text:
                    "Добавить фото\n(необязательно)"

                on_release:
                    root.choose_photo()


        Button:

            text: "Сохранить срок"

            size_hint_y: None

            height: dp(58)

            background_normal: ""

            background_color:
                .16, .35, .78, 1

            on_release:
                root.save_product()


        Widget:


<ProductScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(16)

        spacing: dp(10)

        canvas.before:

            Color:
                rgba: .055, .06, .075, 1

            Rectangle:
                pos: self.pos
                size: self.size


        BoxLayout:

            size_hint_y: None

            height: dp(52)


            Button:

                text: "← Назад"

                size_hint_x: None

                width: dp(90)

                on_release:
                    app.go_main()


            Label:

                text:
                    "Информация о товаре"

                font_size: "19sp"

                bold: True


        Image:

            id: photo

            size_hint_y: None

            height: dp(180)

            allow_stretch: True

            keep_ratio: True


        Label:

            id: name

            text: ""

            font_size: "24sp"

            bold: True

            size_hint_y: None

            height: dp(50)


        Label:

            id: barcode_label

            text: ""

            color:
                .55, .57, .64, 1

            size_hint_y: None

            height: dp(30)


        Label:

            id: nearest

            text: ""

            font_size: "19sp"

            size_hint_y: None

            height: dp(40)


        Label:

            id: dates

            text: ""

            color:
                .6, .62, .68, 1

            size_hint_y: None

            height: dp(35)


        Widget:


        Button:

            id: writeoff

            text: "Списано"

            size_hint_y: None

            height: dp(60)

            background_normal: ""

            background_color:
                .75, .16, .16, 1

            on_release:
                root.write_off()
'''


Builder.load_string(KV)


# =========================================================
# App
# =========================================================

class ExpiringGoodsApp(App):

    title = "Сроки товаров"

    def build(self):

        self.store = DataStore(
            os.path.join(
                self.user_data_dir,
                "products.json"
            )
        )

        self.sm = ScreenManager(
            transition=SlideTransition(
                duration=0.15
            )
        )

        self.sm.add_widget(
            MainScreen(name="main")
        )

        self.sm.add_widget(
            ScannerScreen(name="scanner")
        )

        self.sm.add_widget(
            ManualScreen(name="manual")
        )

        self.sm.add_widget(
            AddScreen(name="add")
        )

        self.sm.add_widget(
            ProductScreen(name="product")
        )

        return self.sm

    def on_start(self):

        Clock.schedule_once(
            lambda dt:
            self.request_camera_permission(),
            0.5
        )

    # -----------------------------------------------------
    # Camera permission
    # -----------------------------------------------------

    def camera_permission_granted(self):

        if (
            request_permissions is None
            or Permission is None
            or check_permission is None
        ):

            # Desktop
            return True

        try:

            return check_permission(
                Permission.CAMERA
            )

        except Exception:

            return False

    def request_camera_permission(self):

        if (
            request_permissions is None
            or Permission is None
        ):

            return

        try:

            request_permissions(
                [Permission.CAMERA]
            )

        except Exception:
            pass

    # -----------------------------------------------------
    # Navigation
    # -----------------------------------------------------

    def open_scanner(self):

        if not self.camera_permission_granted():

            self.request_camera_permission()

        self.sm.current = "scanner"

    def open_product(self, barcode):

        product_screen = (
            self.sm.get_screen(
                "product"
            )
        )

        product_screen.barcode = barcode

        self.sm.current = "product"

    def go_main(self):

        self.sm.current = "main"

        self.sm.get_screen(
            "main"
        ).refresh()

    # -----------------------------------------------------
    # Popup
    # -----------------------------------------------------

    def show_message(
        self,
        title,
        message
    ):

        content = Label(
            text=message,
            halign="center",
            valign="middle"
        )

        Popup(
            title=title,
            content=content,
            size_hint=(0.86, 0.35)
        ).open()


# =========================================================
# Start
# =========================================================

if __name__ == "__main__":

    ExpiringGoodsApp().run()
