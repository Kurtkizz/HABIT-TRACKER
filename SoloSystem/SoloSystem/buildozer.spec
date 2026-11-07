[app]
title = The System
package.name = solosystem
package.domain = org.hunter
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy==2.3.0,plyer,pyjnius,android
orientation = portrait
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #020510
android.permissions = POST_NOTIFICATIONS,VIBRATE,FOREGROUND_SERVICE,WAKE_LOCK
services = Quest:service.py:foreground:sticky
fullscreen = 0
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
