import os
import shutil
import sqlite3
import time
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode

from kivy.utils import platform
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager

from camera4kivy import Preview

if platform == 'android':
    from android.permissions import request_permissions, Permission


class BarcodeAnalyzer:
    """Анализатор потока кадров камеры для camera4kivy"""
    def __init__(self, callback):
        self.callback = callback

    def analyze_pixels_callback(self, pixels, size, image_format, orientation, mirror):
        try:
            img = Image.frombytes('RGBA', size, pixels)
            barcodes = decode(img)

            if barcodes:
                for barcode in barcodes:
                    code_data = barcode.data.decode('utf-8')
                    Clock.schedule_once(lambda dt: self.callback(code_data), 0)
                    break
        except Exception:
            pass


class ExpiryApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.import_db_file,
            ext=['.db']
        )
        self.is_scanning = True
        self.last_scanned_code = None
        self.last_scanned_time = 0

    def build(self):
        self.title = "Pyton Detect"
        self.theme_cls.primary_palette = "Blue"
        self.init_db()

        self.layout = MDBoxLayout(
            orientation='vertical',
            padding=15,
            spacing=10
        )

        self.status_label = MDLabel(
            text="Инициализация приложения...",
            halign="center",
            size_hint_y=None,
            height="30dp"
        )
        self.layout.add_widget(self.status_label)

        self.preview = Preview(aspect_ratio='16:9', size_hint_y=0.4)
        self.layout.add_widget(self.preview)

        self.barcode_input = MDTextField(
            hint_text="Штрихкод товара",
            size_hint_y=None,
            height="50dp"
        )
        self.name_input = MDTextField(
            hint_text="Название товара (опционально)",
            size_hint_y=None,
            height="50dp"
        )
        self.expiry_input = MDTextField(
            hint_text="Срок годности (ГГГГ-ММ-ДД)",
            size_hint_y=None,
            height="50dp"
        )

        self.layout.add_widget(self.barcode_input)
        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.expiry_input)

        btn_layout = MDBoxLayout(
            spacing="10dp",
            pos_hint={"center_x": 0.5},
            adaptive_size=True
        )

        save_btn = MDRaisedButton(
            text="Сохранить",
            on_release=self.save_to_db
        )
        export_btn = MDRaisedButton(
            text="Экспорт БД",
            on_release=self.export_db
        )
        import_btn = MDRaisedButton(
            text="Импорт БД",
            on_release=self.open_file_manager
        )

        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(export_btn)
        btn_layout.add_widget(import_btn)

        self.layout.add_widget(btn_layout)

        return self.layout

    def on_start(self):
        if platform == 'android':
            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ], self.permission_callback)
        else:
            self.status_label.text = "Режим ПК"
            self.start_camera()

    def permission_callback(self, permissions, results):
        if all(results):
            self.status_label.text = "Разрешения получены"
            self.start_camera()
        else:
            self.status_label.text = "Ошибка: Отсутствуют необходимые разрешения"

    def start_camera(self):
        try:
            self.analyzer = BarcodeAnalyzer(self.on_barcode_scanned)
            self.preview.connect_camera(
                enable_analyzer=True,
                analyzer=self.analyzer
            )
            self.status_label.text = "Наведите камеру на штрихкод"
        except Exception as err:
            self.status_label.text = f"Ошибка камеры: {err}"

    def on_barcode_scanned(self, barcode_data):
        now = time.time()
        
        if not self.is_scanning:
            return

        if barcode_data == self.last_scanned_code and (now - self.last_scanned_time) < 2.0:
            return

        self.last_scanned_code = barcode_data
        self.last_scanned_time = now
        self.is_scanning = False

        self.barcode_input.text = barcode_data
        self.status_label.text = f"Сосканировано: {barcode_data}"
        Clock.schedule_once(self.resume_scanning, 3.0)

    def resume_scanning(self, dt):
        self.is_scanning = True
        self.status_label.text = "Наведите камеру на штрихкод"

    def on_stop(self):
        if hasattr(self, 'preview'):
            self.preview.disconnect_camera()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def init_db(self):
        self.conn = sqlite3.connect("selver_base.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,
                name TEXT,
                expiry_date TEXT NOT NULL,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    def save_to_db(self, instance):
        barcode = self.barcode_input.text.strip()
        name = self.name_input.text.strip()
        expiry = self.expiry_input.text.strip()

        if not barcode or not expiry:
            self.show_dialog("Ошибка", "Заполните штрихкод и срок годности!")
            return

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO inventory (barcode, name, expiry_date, created_at) VALUES (?, ?, ?, ?)",
            (barcode, name, expiry, created_at)
        )
        self.conn.commit()

        self.show_dialog("Успех", f"Товар {barcode} успешно записан!")
        self.barcode_input.text = ""
        self.name_input.text = ""
        self.expiry_input.text = ""
        self.is_scanning = True

    def export_db(self, instance):
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.commit()

            if platform == 'android':
                export_dir = "/sdcard/Download"
            else:
                export_dir = os.getcwd()

            if not os.path.exists(export_dir):
                os.makedirs(export_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(export_dir, f"selver_base_backup_{timestamp}.db")

            shutil.copy2("selver_base.db", target_path)
            self.show_dialog("Экспорт завершен", f"База сохранена в:\n{target_path}")
        except Exception as err:
            self.show_dialog("Ошибка экспорта", str(err))

    def open_file_manager(self, instance):
        if platform == 'android':
            start_path = "/sdcard/Download"
        else:
            start_path = os.getcwd()
        self.file_manager.show(start_path)

    def exit_file_manager(self, *args):
        self.file_manager.close()

    def import_db_file(self, selected_path):
        self.exit_file_manager()
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()

            shutil.copy2(selected_path, "selver_base.db")
            self.init_db()
            self.show_dialog("Импорт завершен", "База данных успешно обновлена!")
        except Exception as err:
            self.show_dialog("Ошибка импорта", str(err))

    def show_dialog(self, title, text):
        dialog = MDDialog(title=title, text=text)
        dialog.open()


if __name__ == '__main__':
    ExpiryApp().run()
