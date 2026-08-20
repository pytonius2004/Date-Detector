[app]
title = Expiry Tracker
package.name = expirytracker
package.domain = org.pytonius

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0

requirements = python3,kivy==2.3.0,kivymd,camera4kivy,pyjnius,android,pillow,pyzbar

orientation = portrait
fullscreen = 0

android.permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True
android.build_tools_version = 33.0.2
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
