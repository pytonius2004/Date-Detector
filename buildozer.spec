[app]

title = Сроки Годности

package.name = expiringgoods
package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json,db,ttf

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__,scripts,google_apps_script

version = 0.0.7


# =========================================================
# PYTHON / KIVY
# =========================================================

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius,filetype


# =========================================================
# APP
# =========================================================

orientation = portrait

fullscreen = 0

presplash.filename = presplash.png
icon.filename = icon.png


# =========================================================
# ANDROID SDK
# =========================================================

android.api = 35
android.minapi = 23

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
# JAVA SOURCE
# =========================================================

android.add_src = android_src


# =========================================================
# BARCODE SCANNER ACTIVITY
# =========================================================

android.add_activities = org.example.expiringgoods.BarcodeScannerActivity


# =========================================================
# CAMERAX + GOOGLE ML KIT
#
# ВАЖНО:
# Все Kotlin-библиотеки принудительно ставим на 1.8.22.
# Это убирает конфликт:
#
# kotlin-stdlib 1.8.22
# VS
# kotlin-stdlib-jdk7/jdk8 1.6.21
# =========================================================

android.gradle_dependencies = androidx.activity:activity:1.8.2,androidx.camera:camera-core:1.3.4,androidx.camera:camera-camera2:1.3.4,androidx.camera:camera-lifecycle:1.3.4,androidx.camera:camera-view:1.3.4,com.google.mlkit:barcode-scanning:17.2.0,org.jetbrains.kotlin:kotlin-stdlib:1.8.22,org.jetbrains.kotlin:kotlin-stdlib-jdk7:1.8.22,org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.8.22


# =========================================================
# PYTHON-FOR-ANDROID
# =========================================================

p4a.branch = master
p4a.commit = v2024.01.21


# =========================================================
# BUILDOZER
# =========================================================

[buildozer]

log_level = 2
warn_on_root = 1
