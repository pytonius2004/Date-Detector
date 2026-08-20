[app]

title = Сроки товаров

package.name = expiringgoods

package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 1.0.0

requirements = python3==3.10.12,kivy==2.2.1,plyer,pyjnius

orientation = portrait

fullscreen = 0

presplash.filename = icon.png

icon.filename = icon.png

android.api = 33

android.minapi = 23

android.ndk = 25b

android.ndk_api = 23

android.accept_sdk_license = True

android.private_storage = True

android.archs = arm64-v8a

android.permissions = CAMERA

android.gradle_dependencies = com.google.mlkit:barcode-scanning:17.3.0

android.enable_androidx = True

android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"

android.debug_artifact = apk

[buildozer]

log_level = 2

warn_on_root = 1
