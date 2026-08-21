[app]

title = Pyton Date Detect

package.name = expiringgoods
package.domain = org.example

source.dir = .

source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json

source.exclude_dirs = .git,.github,.buildozer,bin,venv,__pycache__

version = 0.0.4

requirements = python3==3.11.6,hostpython3==3.11.6,kivy==2.3.1,plyer,pyjnius,filetype

orientation = portrait
fullscreen = 0

presplash.filename = icon.png

# Legacy/fallback icon
icon.filename = icon.png

android.api = 33
android.minapi = 23

android.sdk_path = /usr/local/lib/android/sdk

android.ndk = 25b
android.ndk_api = 23

android.archs = arm64-v8a

android.permissions = CAMERA

android.private_storage = True
android.allow_backup = True

p4a.branch = master
p4a.commit = v2024.01.21

[buildozer]

log_level = 2
warn_on_root = 1
