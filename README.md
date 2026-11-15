[Uploading README.md…]()
# The System (Solo Leveling habit tracker)

Starter files (not live-updated): main.py, loader.py, updater.py, service.py, buildozer.spec, p4a_widget_hook.py
Live-updatable: app_main.py, engine.py, service_main.py, notifier.py, reps.py, camera_pose.py, runtrack.py (Build 2.0 needs only these)

Live updates: edit a live-updatable file on GitHub, commit, then ADMIN > CHECK FOR UPDATES in the app, close and reopen it.
Backup your save first: ADMIN > EXPORT BACKUP.

Build APK (GitHub > Actions > Build APK > Run workflow):
- Pushes make a standard build (background GPS, no camera library, no widget).
- Tick "camera" to add Google ML Kit pose detection (camera rep counter).
- Tick "widget" to add the home screen widget.
Experimental builds are named TheSystem-apk-experimental. All builds use the same signing key, so they install over each other.
