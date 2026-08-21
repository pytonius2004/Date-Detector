from pathlib import Path
import re, ast

src = Path("/mnt/data/main_departments_fixed.py")
text = src.read_text(encoding="utf-8")

def must_replace(old, new, count=1):
    global text
    if old not in text:
        raise RuntimeError(f"Pattern not found: {old[:80]!r}")
    text = text.replace(old, new, count)

# ---------- constants ----------
must_replace(
    "REQUEST_IMPORT_DB = 4102\n",
    "REQUEST_IMPORT_DB = 4102\nREQUEST_PICK_PHOTO = 4201\nREQUEST_TAKE_PHOTO = 4202\n",
)

# ---------- schema ----------
must_replace(
    "department TEXT NOT NULL DEFAULT '',\n                created_at TEXT NOT NULL",
    "department TEXT NOT NULL DEFAULT '',\n                photo_path TEXT NOT NULL DEFAULT '',\n                created_at TEXT NOT NULL",
)

must_replace(
'''        if "department" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN department TEXT NOT NULL DEFAULT ''"
            )

        self.conn.commit()
''',
'''        if "department" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN department TEXT NOT NULL DEFAULT ''"
            )

        if "photo_path" not in product_columns:
            self.conn.execute(
                "ALTER TABLE products "
                "ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''"
            )

        self.conn.commit()
''')

# ---------- save_product ----------
m = re.search(r'    def save_product\([\s\S]*?\n    def add_expiration\(', text)
if not m:
    raise RuntimeError("save_product block not found")
replacement = '''    def save_product(
        self,
        barcode,
        name,
        department=None,
        photo_path=None
    ):

        barcode = normalize_barcode(barcode)
        name = name.strip()

        existing = self.get_product(barcode)

        final_department = (
            str(department).strip()
            if department is not None
            else (
                (existing["department"] or "")
                if existing
                else ""
            )
        )

        final_photo = (
            str(photo_path).strip()
            if photo_path is not None
            else (
                (existing["photo_path"] or "")
                if existing
                else ""
            )
        )

        if existing:
            self.conn.execute(
                """
                UPDATE products
                SET name = ?, department = ?, photo_path = ?
                WHERE barcode = ?
                """,
                (
                    name,
                    final_department,
                    final_photo,
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
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    final_department,
                    final_photo,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

        self.conn.commit()

    def add_expiration('''
text = text[:m.start()] + replacement + text[m.end():]

# ---------- product list + search ----------
m = re.search(r'    def get_product_list\([\s\S]*?\n    def backup_to\(', text)
if not m:
    raise RuntimeError("get_product_list block not found")
replacement = '''    def get_product_list(
        self,
        department=None
    ):

        department = str(department).strip() if department else ""

        return self.conn.execute(
            """
            SELECT
                p.barcode,
                p.name,
                p.department,
                p.photo_path,
                (
                    SELECT e.exp_date
                    FROM expirations e
                    WHERE e.barcode = p.barcode
                      AND e.written_off = 0
                    ORDER BY e.exp_date ASC, e.id ASC
                    LIMIT 1
                ) AS next_exp,
                (
                    SELECT COUNT(*)
                    FROM expirations e3
                    WHERE e3.barcode = p.barcode
                ) AS total_expirations
            FROM products p
            WHERE ? = '' OR p.department = ? OR p.department = ''
            ORDER BY
                CASE WHEN (
                    SELECT e2.exp_date
                    FROM expirations e2
                    WHERE e2.barcode = p.barcode
                      AND e2.written_off = 0
                    ORDER BY e2.exp_date ASC, e2.id ASC
                    LIMIT 1
                ) IS NULL THEN 1 ELSE 0 END ASC,
                next_exp ASC,
                p.name COLLATE NOCASE ASC
            """,
            (department, department),
        ).fetchall()

    def search_products(
        self,
        query,
        limit=10
    ):

        query = str(query).strip()
        if not query:
            return []

        pattern = "%" + query + "%"

        return self.conn.execute(
            """
            SELECT
                p.*,
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
            ORDER BY p.name COLLATE NOCASE ASC
            LIMIT ?
            """,
            (
                pattern,
                pattern,
                int(limit),
            ),
        ).fetchall()

    def backup_to('''
text = text[:m.start()] + replacement + text[m.end():]

# ---------- Home: classify no-date separately ----------
must_replace(
    "        active = []\n        completed = []\n",
    "        active = []\n        completed = []\n        no_date = []\n",
)

must_replace(
'''            if not product[
                "next_exp"
            ]:

                completed.append(
                    product
                )

                continue
''',
'''            if not product[
                "next_exp"
            ]:

                if int(product["total_expirations"] or 0) == 0:
                    no_date.append(product)
                else:
                    completed.append(product)

                continue
''')

must_replace(
'''        elif self.filter_mode == "no_date":
            active = []
            # completed уже содержит товары без активной даты
''',
'''        elif self.filter_mode == "no_date":
            active = []
            completed = []
''')

# clear no_date for other filters
must_replace(
'''            completed = []

        elif self.filter_mode == "expiring":
''',
'''            completed = []
            no_date = []

        elif self.filter_mode == "expiring":
''', 1)
must_replace(
'''            completed = []

        elif self.filter_mode == "no_date":
''',
'''            completed = []
            no_date = []

        elif self.filter_mode == "no_date":
''', 1)

must_replace(
'''        if completed:

            separator = Label(
''',
'''        if no_date:

            for product in no_date:
                self.product_list.add_widget(
                    self.make_product_card(
                        product,
                        None,
                        today,
                        yesterday,
                        no_date=True
                    )
                )

        if completed:

            separator = Label(
''')

must_replace(
'''            not active
            and
            not completed
''',
'''            not active
            and
            not completed
            and
            not no_date
''')

must_replace(
'''        today,
        yesterday
    ):

        if exp_date is None:

            bg = CARD_DISABLED
            fg = TEXT_SECONDARY
            date_text = "—"
''',
'''        today,
        yesterday,
        no_date=False
    ):

        if no_date:
            bg = GREEN
            fg = TEXT
            date_text = "Без даты"

        elif exp_date is None:

            bg = CARD_DISABLED
            fg = TEXT_SECONDARY
            date_text = "—"
''')

# ---------- ProductCard thumbnail ----------
must_replace(
'''        exp_date,
        **kwargs
''',
'''        exp_date,
        photo_path="",
        **kwargs
''')

must_replace(
'''        # -------------------------------------------------
        # LEFT SIDE
        # -------------------------------------------------

        left = BoxLayout(
''',
'''        thumb_wrap = BoxLayout(
            size_hint_x=None,
            width=dp(72),
            padding=dp(4),
        )

        if photo_path and Path(photo_path).exists():
            thumb = Image(
                source=photo_path,
                fit_mode="cover",
            )
        else:
            thumb = Widget()
            with thumb.canvas:
                Color(0.38, 0.39, 0.42, 1)
                thumb_rect = RoundedRectangle(
                    pos=thumb.pos,
                    size=thumb.size,
                    radius=[dp(11)],
                )
            thumb.bind(
                pos=lambda instance, value: setattr(thumb_rect, "pos", value),
                size=lambda instance, value: setattr(thumb_rect, "size", value),
            )

        thumb_wrap.add_widget(thumb)
        self.add_widget(thumb_wrap)

        # -------------------------------------------------
        # LEFT SIDE
        # -------------------------------------------------

        left = BoxLayout(
''', 1)

must_replace(
'''            exp_date=date_text,
        )
''',
'''            exp_date=date_text,
            photo_path=(product["photo_path"] or ""),
        )
''', 1)

# ---------- AddProductScreen optional date/photo ----------
must_replace(
'''        self.date_input.text = ""
''',
'''        self.date_input.text = ""
        self.pending_photo_path = ""
        if hasattr(self, "photo_preview"):
            self.photo_preview.source = ""
            self.photo_preview.opacity = 0
''', 1)

must_replace(
'''        if name:

            self.name_input.text = (
                name
            )
''',
'''        if name:

            self.name_input.text = (
                name
            )

        photo_path = product["photo_path"] or ""
        if photo_path and hasattr(self, "photo_preview"):
            self.pending_photo_path = photo_path
            self.photo_preview.source = photo_path
            self.photo_preview.opacity = 1
''', 1)

# photo methods before save
marker = "    def save(self):\n"
pos = text.find(marker, text.find("class AddProductScreen"))
if pos < 0:
    raise RuntimeError("AddProductScreen.save not found")
helpers = '''    def choose_photo(self):
        self.app.choose_product_photo(self)

    def take_photo(self):
        self.app.take_product_photo(self)

    def set_photo(self, path):
        self.pending_photo_path = path or ""
        if hasattr(self, "photo_preview"):
            self.photo_preview.source = self.pending_photo_path
            self.photo_preview.opacity = 1 if self.pending_photo_path else 0

'''
text = text[:pos] + helpers + text[pos:]

must_replace(
'''        exp_date = parse_user_date(
            date_text
        )

        if not exp_date:

            self.app.message(
                "Введите срок в формате ДД.ММ.ГГ.\\n\\n"
                "Например: 280826 → 28.08.26"
            )

            return
''',
'''        exp_date = None

        if date_text:
            exp_date = parse_user_date(date_text)

            if not exp_date:
                self.app.message(
                    "Введите срок в формате ДД.ММ.ГГ.\\n\\n"
                    "Например: 280826 → 28.08.26"
                )
                return
''')

must_replace(
'''        self.app.db.save_product(
            barcode,
            name,
            self.app.current_department
        )
''',
'''        self.app.db.save_product(
            barcode,
            name,
            self.app.current_department,
            getattr(self, "pending_photo_path", "")
        )
''')

must_replace(
'''        if not self.app.db.add_expiration(
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
''',
'''        if exp_date:

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

        else:

            self.app.message(
                "Товар сохранён без срока.\\n\\n"
                "Он будет отображаться зелёным."
            )
''')

# ---------- Department screen search/settings ----------
m = re.search(r'    def create_department_screen\(self\):[\s\S]*?\n\n    # =====================================================\n    # HOME UI', text)
if not m:
    raise RuntimeError("department screen block not found")

dept = '''    def create_department_screen(self):

        screen = DepartmentScreen(name="departments")

        root = BoxLayout(
            orientation="vertical",
            padding=safe_padding(horizontal=14, top=7, bottom=12),
            spacing=dp(10),
        )

        root.add_widget(self.create_header())

        search = TextInput(
            hint_text="Поиск товара",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size="16sp",
            padding=(dp(14), dp(13)),
        )
        root.add_widget(search)

        results = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
        )
        results.bind(minimum_height=results.setter("height"))
        root.add_widget(results)

        search.bind(
            text=lambda instance, value:
            self.update_global_search(screen, value)
        )
        search.bind(
            on_text_validate=lambda *_:
            self.open_first_search_result(screen)
        )

        settings = RoundedButton(
            text="Настройки",
            size_hint_y=None,
            height=dp(52),
            font_size="15sp",
        )
        settings.bind(
            on_release=lambda *_:
            self.open_settings()
        )
        root.add_widget(settings)

        title = Label(
            text="Выберите отдел",
            color=TEXT,
            bold=True,
            font_size="22sp",
            size_hint_y=None,
            height=dp(48),
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda instance, value: setattr(instance, "text_size", value))
        root.add_widget(title)

        scroll = ScrollView(do_scroll_x=False)
        departments_list = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8),
            padding=(0, dp(2), 0, dp(10)),
        )
        departments_list.bind(minimum_height=departments_list.setter("height"))

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
                setattr(instance, "text_size", (value[0] - dp(36), value[1]))
            )
            button.bind(
                on_release=lambda _button, name=department_name:
                self.select_department(name)
            )
            departments_list.add_widget(button)

        scroll.add_widget(departments_list)
        root.add_widget(scroll)

        screen.search_input = search
        screen.search_results = results
        screen.search_matches = []

        screen.add_widget(root)
        return screen


    # =====================================================
    # HOME UI'''
text = text[:m.start()] + dept + text[m.end():]

# ---------- Home actions: only Add + Sort ----------
m = re.search(r'        department_button = RoundedButton\([\s\S]*?        root.add_widget\(\n            actions\n        \)\n', text)
if not m:
    raise RuntimeError("home controls block not found")
controls = '''        actions = BoxLayout(
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
'''
text = text[:m.start()] + controls + text[m.end():]

# remove refresh department label block if present
text = re.sub(
    r'        if hasattr\(self, "department_button"\):[\s\S]*?            \)\n\n',
    '',
    text,
    count=1
)

# ---------- Add screen photo UI ----------
must_replace(
'''                "Отсканируй штрихкод или введи его вручную.\\n"
                "Для известного товара название заполнится автоматически."
''',
'''                "Отсканируй штрихкод или введи его вручную.\\n"
                "Дата и фото необязательны."
''')

must_replace(
'''        root.add_widget(
            date_input
        )

        root.add_widget(
            Widget()
        )
''',
'''        root.add_widget(
            date_input
        )

        photo_row = BoxLayout(
            size_hint_y=None,
            height=dp(88),
            spacing=dp(10),
        )

        preview_holder = BoxLayout(
            size_hint_x=None,
            width=dp(88),
            padding=dp(5),
        )
        with preview_holder.canvas.before:
            Color(0.36, 0.37, 0.40, 1)
            preview_bg = RoundedRectangle(
                pos=preview_holder.pos,
                size=preview_holder.size,
                radius=[dp(14)],
            )
        preview_holder.bind(
            pos=lambda instance, value: setattr(preview_bg, "pos", value),
            size=lambda instance, value: setattr(preview_bg, "size", value),
        )

        photo_preview = Image(
            source="",
            fit_mode="cover",
            opacity=0,
        )
        preview_holder.add_widget(photo_preview)

        photo_buttons = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
        )

        camera_photo = RoundedButton(
            text="Фото с камеры",
            font_size="13sp",
        )
        camera_photo.bind(
            on_release=lambda *_:
            screen.take_photo()
        )

        gallery_photo = RoundedButton(
            text="Из галереи",
            font_size="13sp",
        )
        gallery_photo.bind(
            on_release=lambda *_:
            screen.choose_photo()
        )

        photo_buttons.add_widget(camera_photo)
        photo_buttons.add_widget(gallery_photo)

        photo_row.add_widget(preview_holder)
        photo_row.add_widget(photo_buttons)
        root.add_widget(photo_row)

        root.add_widget(
            Widget()
        )
''')

must_replace(
'''        screen.date_input = (
            date_input
        )

        screen.add_widget(
''',
'''        screen.date_input = (
            date_input
        )
        screen.photo_preview = photo_preview
        screen.pending_photo_path = ""

        screen.add_widget(
''')

# ---------- Product detail: add date button ----------
must_replace(
'''        else:

            self.nearest_date_label.text = (
                "Активных сроков нет"
            )
''',
'''        else:

            self.nearest_date_label.text = (
                "Срок не указан"
            )

        if hasattr(self, "add_date_button"):
            self.add_date_button.disabled = bool(active)
            self.add_date_button.opacity = 0 if active else 1
''')

must_replace(
'''        writeoff = RoundedButton(
            text="Списано",
''',
'''        add_date_button = RoundedButton(
            text="Добавить срок",
            size_hint_y=None,
            height=dp(56),
            font_size="16sp",
            normal_color=GREEN,
            down_color=(0.08, 0.48, 0.21, 1),
        )
        add_date_button.bind(
            on_release=lambda *_:
            self.open_add(screen.barcode)
        )
        root.add_widget(add_date_button)

        writeoff = RoundedButton(
            text="Списано",
''')

must_replace(
'''        screen.writeoff_button = (
            writeoff
        )
''',
'''        screen.writeoff_button = (
            writeoff
        )
        screen.add_date_button = add_date_button
''')

must_replace(
'''        self.writeoff_button.disabled = (
            not bool(
                active
            )
        )
''',
'''        self.writeoff_button.disabled = (
            not bool(
                active
            )
        )
        self.writeoff_button.opacity = 1 if active else 0
''')

# ---------- Search methods ----------
nav_marker = '''    # =====================================================
    # SORT / FILTER
    # =====================================================
'''
search_code = '''    # =====================================================
    # GLOBAL SEARCH
    # =====================================================

    def update_global_search(self, screen, value):

        query = str(value).strip()
        screen.search_results.clear_widgets()
        screen.search_matches = []

        if len(query) < 2:
            return

        matches = self.db.search_products(query, limit=5)
        screen.search_matches = list(matches)

        for product in matches:
            button = RoundedButton(
                text=(
                    (product["name"] or "Без названия")
                    +
                    "\\nШтрихкод: "
                    +
                    product["barcode"]
                ),
                size_hint_y=None,
                height=dp(58),
                font_size="13sp",
                halign="left",
                valign="middle",
                padding=(dp(14), dp(6)),
                normal_color=CARD,
                down_color=BUTTON_BG_DOWN,
            )
            button.bind(
                size=lambda instance, size:
                setattr(instance, "text_size", (size[0] - dp(28), size[1]))
            )
            button.bind(
                on_release=lambda _button, barcode=product["barcode"]:
                self.open_product_from_search(barcode)
            )
            screen.search_results.add_widget(button)

    def open_first_search_result(self, screen):

        if screen.search_matches:
            self.open_product_from_search(
                screen.search_matches[0]["barcode"]
            )

    def open_product_from_search(self, barcode):

        product = self.db.get_product(barcode)
        if product:
            department = (product["department"] or "").strip()
            if department:
                self.current_department = department
        self.open_product(barcode)


    # =====================================================
    # PRODUCT PHOTOS
    # =====================================================

    def _product_photo_dir(self):
        folder = Path(self.user_data_dir) / "product_photos"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def choose_product_photo(self, screen):

        if not ANDROID:
            self.message("Галерея настроена для Android.")
            return

        try:
            self.pending_photo_screen = screen

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )
            Intent = autoclass("android.content.Intent")

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")

            current_activity.startActivityForResult(
                intent,
                REQUEST_PICK_PHOTO
            )

        except Exception as exc:
            self.message("Не удалось открыть галерею:\\n\\n" + str(exc))

    def take_product_photo(self, screen):

        if not ANDROID:
            self.message("Камера для фото настроена для Android.")
            return

        try:
            self.pending_photo_screen = screen

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            current_activity = cast(
                "android.app.Activity",
                PythonActivity.mActivity
            )
            Intent = autoclass("android.content.Intent")
            MediaStore = autoclass("android.provider.MediaStore")

            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            current_activity.startActivityForResult(
                intent,
                REQUEST_TAKE_PHOTO
            )

        except Exception as exc:
            self.message("Не удалось открыть камеру:\\n\\n" + str(exc))

    def _copy_photo_uri(self, uri):

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        current_activity = cast(
            "android.app.Activity",
            PythonActivity.mActivity
        )
        resolver = current_activity.getContentResolver()
        input_stream = resolver.openInputStream(uri)

        if input_stream is None:
            raise RuntimeError("Android не смог открыть фото.")

        target = (
            self._product_photo_dir()
            /
            (
                "product_"
                +
                datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                +
                ".jpg"
            )
        )

        with target.open("wb") as output:
            while True:
                value = input_stream.read()
                if value == -1:
                    break
                output.write(bytes((value & 0xFF,)))

        input_stream.close()
        return str(target)

    def _save_camera_thumbnail(self, intent):

        extras = intent.getExtras()
        if extras is None:
            raise RuntimeError("Камера не вернула фото.")

        bitmap = extras.get("data")
        if bitmap is None:
            raise RuntimeError("Камера не вернула миниатюру.")

        ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
        CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")

        stream = ByteArrayOutputStream()
        bitmap.compress(CompressFormat.JPEG, 92, stream)

        java_bytes = stream.toByteArray()
        data = bytes((value & 0xFF for value in java_bytes))

        target = (
            self._product_photo_dir()
            /
            (
                "product_"
                +
                datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                +
                ".jpg"
            )
        )
        target.write_bytes(data)
        stream.close()
        return str(target)

'''
must_replace(nav_marker, search_code + nav_marker)

# ---------- app state ----------
must_replace(
'''        self.current_department = None

        self.db = Database(
''',
'''        self.current_department = None
        self.pending_photo_screen = None

        self.db = Database(
''')

# ---------- activity results for photos ----------
must_replace(
'''        if (
            request_code
            ==
            REQUEST_IMPORT_DB
        ):

            self.handle_import_result(
                result_code,
                intent
            )
''',
'''        if (
            request_code
            ==
            REQUEST_IMPORT_DB
        ):

            self.handle_import_result(
                result_code,
                intent
            )
            return

        if request_code == REQUEST_PICK_PHOTO:
            if result_code == -1 and intent is not None:
                try:
                    uri = intent.getData()
                    if uri is not None:
                        path = self._copy_photo_uri(uri)
                        if self.pending_photo_screen is not None:
                            self.pending_photo_screen.set_photo(path)
                except Exception as exc:
                    self.message("Ошибка выбора фото:\\n\\n" + str(exc))
            self.pending_photo_screen = None
            return

        if request_code == REQUEST_TAKE_PHOTO:
            if result_code == -1 and intent is not None:
                try:
                    path = self._save_camera_thumbnail(intent)
                    if self.pending_photo_screen is not None:
                        self.pending_photo_screen.set_photo(path)
                except Exception as exc:
                    self.message("Ошибка сохранения фото:\\n\\n" + str(exc))
            self.pending_photo_screen = None
            return
''')

# ---------- syntax ----------
ast.parse(text)

out = Path("/mnt/data/main.py")
out.write_text(text, encoding="utf-8")

print(f"Готово: {out}")
print(f"Строк: {len(text.splitlines())}")
print("AST syntax check: OK")
