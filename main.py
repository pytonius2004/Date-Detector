import os

os.environ["KIVY_GL_BACKEND"] = "sdl2"
os.environ["KIVY_GRAPHICS"] = "gles"
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.config import Config

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "0")

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class TestApp(App):
    title = "Сроки товаров"

    def build(self):
        root = BoxLayout(
            orientation="vertical"
        )

        root.add_widget(
            Label(
                text="Сроки товаров\n\n"
                     "Тестовая сборка работает",
                font_size="24sp",
                halign="center",
                valign="middle",
            )
        )

        return root


if __name__ == "__main__":
    TestApp().run()
