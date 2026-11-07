# The System (Solo Leveling habit tracker)

Files: `main.py` (UI), `engine.py` (game rules), `service.py` (background quest notifications), `buildozer.spec`.

## Build the APK
- GitHub: push this folder to a repo, open Actions > "Build APK" > Run workflow, download the `TheSystem-apk` artifact.
- Local (Linux/WSL): `pip install buildozer cython && buildozer -v android debug` -> APK in `bin/`.

## Admin
ADMIN tab, default PIN `0000` (change it on first use). Save data is `system.json` in the app's data folder.
Habit rule format: `keywords, comma separated | EXP value | STAT`. Quest format: `name | reward | penalty | punishment`.

## Notes
- Allow notifications, and exclude the app from battery optimization so Android keeps the background service alive.
- Penalties for missed quests are applied when you open the app.
