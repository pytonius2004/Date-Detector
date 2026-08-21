[app]

title = Сроки Годности

package.name = expiringgoods
package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json,db

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.0.4

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius,filetype

orientation = portrait
fullscreen = 0

presplash.filename = icon.png
icon.filename = icon.png

android.api = 35
android.minapi = 23

android.sdk_path = /usr/local/lib/android/sdk

android.ndk = 25b
android.ndk_api = 23

android.archs = arm64-v8a

android.permissions = CAMERA

android.private_storage = True
android.allow_backup = True

android.enable_androidx = True

android.add_src = android_src

android.add_activities = org.example.expiringgoods.BarcodeScannerActivity

android.gradle_dependencies = androidx.activity:activity:1.8.2,androidx.camera:camera-core:1.3.4,androidx.camera:camera-camera2:1.3.4,androidx.camera:camera-lifecycle:1.3.4,androidx.camera:camera-view:1.3.4,com.google.mlkit:barcode-scanning:17.2.0

p4a.branch = master
p4a.commit = v2024.01.21


[buildozer]

log_level = 2
warn_on_root = 1
