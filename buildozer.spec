[app]

# (str) Title of your application
title = Date-Detector

# (str) Package name
package.name = datedetector

# (str) Package domain (needed for android/ios packaging)
package.domain = org.datedetector

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db,json

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# Чистый список без C-библиотек zbar, вызывавших сбой NDK
requirements = python3,kivy==2.3.0,kivymd,camera4kivy,gestures,pyjnius,android,pillow

# (str) Supported orientations (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = CAMERA, INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Target Android API
android.api = 33

# (int) Minimum API required
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (list) List of architectures to build for (только arm64-v8a для стабильности)
android.archs = arm64-v8a

# (bool) Enable Android auto backup
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = false, 1 = true)
warn_on_root = 1
