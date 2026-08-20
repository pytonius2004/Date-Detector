[app]

title = Сроки товаров
package.name = expiringgoods
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas
source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.0.1

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 23
android.ndk = 25b
android.ndk_api = 23
android.sdk_path = /home/runner/.android/sdk
android.archs = arm64-v8a
android.permissions = CAMERA

android.private_storage = True
android.allow_backup = True

p4a.branch = master
p4a.commit = v2024.01.21
