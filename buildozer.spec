[app]

title = Сроки товаров
package.name = expiringgoods
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,db,txt,xz
source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.3.0

requirements = python3==3.10.12,android,Kivy==2.3.1,androidstorage4kivy

orientation = portrait
fullscreen = 0

presplash.filename = icon.png
icon.filename = icon.png

android.permissions = CAMERA
android.api = 35
android.minapi = 23
android.ndk = 25b
android.ndk_api = 23
android.accept_sdk_license = True
android.private_storage = True
android.archs = arm64-v8a

# Compatibility workaround for GLES2 on some Samsung/Android devices.
android.meta_data = android.opengl.eglVersion=0x00020000

[buildozer]

log_level = 2
warn_on_root = 1
