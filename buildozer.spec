[app]

title = Pyton Date Detect

package.name = expiringgoods
package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.0.6

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius,filetype

orientation = portrait
fullscreen = 0

presplash.filename = icon.png
icon.filename = icon.png


# =========================================================
# ANDROID SDK / NDK
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

android.permissions = CAMERA

android.private_storage = True
android.allow_backup = True


# =========================================================
# ANDROIDX
# =========================================================

android.enable_androidx = True


# =========================================================
# JAVA SOURCE
#
# Репозиторий:
#
# android_src/
#   org/
#     example/
#       expiringgoods/
#         BarcodeScannerActivity.java
# =========================================================

android.add_src = android_src


# =========================================================
# EXTRA ACTIVITY
#
# ВАЖНО:
# именно android.add_activities
# во множественном числе.
# =========================================================

android.add_activities = org.example.expiringgoods.BarcodeScannerActivity


# =========================================================
# CAMERA X + GOOGLE ML KIT
# =========================================================

android.gradle_dependencies = androidx.activity:activity:1.10.1,androidx.camera:camera-core:1.4.2,androidx.camera:camera-camera2:1.4.2,androidx.camera:camera-lifecycle:1.4.2,androidx.camera:camera-view:1.4.2,com.google.mlkit:barcode-scanning:17.3.0


# =========================================================
# PYTHON-FOR-ANDROID
# =========================================================

p4a.branch = master
p4a.commit = v2024.01.21


[buildozer]

log_level = 2
warn_on_root = 1
