[app]

title = Сроки Годности

package.name = expiringgoods
package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json,db,ttf

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.0.6


# =========================================================
# PYTHON / KIVY
# =========================================================

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius,filetype


# =========================================================
# APP
# =========================================================

orientation = portrait
fullscreen = 0

presplash.filename = icon.png
icon.filename = icon.png


# =========================================================
# ANDROID SDK
# =========================================================

android.api = 35
android.minapi = 23

# ВАЖНО:
# Используем Android SDK, который уже установлен GitHub Actions.
# Иначе Buildozer начинает качать свой SDK и снова спрашивает лицензии.
android.sdk_path = /usr/local/lib/android/sdk

android.ndk = 25b
android.ndk_api = 23

android.archs = arm64-v8a


# =========================================================
# PERMISSIONS
# =========================================================

android.permissions = CAMERA,INTERNET

android.private_storage = True
android.allow_backup = True


# =========================================================
# ANDROIDX
# =========================================================

android.enable_androidx = True


# =========================================================
# JAVA BARCODE SCANNER
# =========================================================

android.add_src = android_src

android.add_activities = org.example.expiringgoods.BarcodeScannerActivity


# =========================================================
# CAMERAX + GOOGLE ML KIT
# =========================================================

android.gradle_dependencies = androidx.activity:activity:1.8.2,androidx.camera:camera-core:1.3.4,androidx.camera:camera-camera2:1.3.4,androidx.camera:camera-lifecycle:1.3.4,androidx.camera:camera-view:1.3.4,com.google.mlkit:barcode-scanning:17.2.0,org.jetbrains.kotlin:kotlin-stdlib:1.8.22


# =========================================================
# KOTLIN
# =========================================================

android.gradle_options = kotlin.stdlib.default.dependency=false


# =========================================================
# PYTHON-FOR-ANDROID
# =========================================================

p4a.branch = master
p4a.commit = v2024.01.21


[buildozer]

log_level = 2
warn_on_root = 1
