[app]

# (str) Title of your application
title = My App

# (str) Package name
package.name = myapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db,json

# (str) Application versioning
version = 0.1

# (list) Application requirements
# ВАЖНО: cython сюда НЕ ПИСАТЬ!
requirements = python3,kivy==2.3.0,kivymd,camera4kivy,gestures,pyjnius,android,pillow,pyzbar,sqlite3

# (str) Supported orientation (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET

# (int) Target Android API
android.api = 33

# (int) Minimum API required
android.minapi = 21

# (int) Android NDK version
android.ndk = 25b

# (bool) Accept SDK license automatically
android.accept_sdk_license = True

# (list) The Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Enable AndroidX
android.enable_androidx = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = false, 1 = true)
warn_on_root = 1
