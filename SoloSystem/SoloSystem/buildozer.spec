[app]
title = The System
package.name = solosystem
package.domain = org.hunter
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy==2.3.0,plyer,pyjnius,android,certifi
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #020510
android.permissions = INTERNET,CAMERA,ACCESS_BACKGROUND_LOCATION,POST_NOTIFICATIONS,VIBRATE,FOREGROUND_SERVICE,WAKE_LOCK,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION
services = Quest:service.py:foreground:sticky
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
