[app]
title = Сроки товаров
package.name = expiringgoods
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,db,txt,xz
source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.2.0

requirements = python3==3.10.12,android,Kivy==2.3.1,libiconv,libzbar,Pillow==8.4.0,pyzbar==0.1.8,xcamera==2019.928,zbarcam,androidstorage4kivy

orientation = portrait
fullscreen = 0

presplash.filename = icon.png
icon.filename = icon.png

android.permissions = CAMERA
android.api = 34
android.minapi = 23
android.ndk = 25b
android.ndk_api = 23
android.accept_sdk_license = True
android.private_storage = True
android.archs = arm64-v8a

# zbarcam's Android stack is based on xcamera + pyzbar + libzbar.
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
