[app]

# (str) Title of your application
title = Pyton Detect

# (str) Package name
package.name = pytondetect

# (str) Package domain (needed for android/ios packaging)
package.domain = org.pytondetect

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,db,xz

# (str) Application versioning
version = 0.1

# (list) Application requirements (указан правильный gestures4kivy)
requirements = python3,kivy,kivymd,camera4kivy,gestures4kivy,pyjnius,android,pillow,pyzbar

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = CAMERA, INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (list) Features
android.features = android.hardware.camera, android.hardware.camera.autofocus

# (int) Target Android API
android.api = 33

# (int) Minimum API support
android.minapi = 21

# (str) Bootstrap to use for android build
p4a.bootstrap = sdl2

# (list) Android application architectures
android.archs = arm64-v8a

# (bool) Enable AndroidX support
android.enable_androidx = True

# (bool) Accept SDK license agreement automatically
android.accept_sdk_license = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
