"""Built-in bootstrap (never live-updated). Starts the app from downloaded 'live' code
when available and falls back to the code built into the APK if the live code fails."""
import hashlib
import os
import shutil
import sys
import time

UPDATE_FILES = ["app_main.py", "engine.py", "service_main.py", "notifier.py"]
REPO_RAW = os.environ.get(
    "SOLO_REPO_RAW", "https://raw.githubusercontent.com/Kurtkizz/HABIT-TRACKER/main/SoloSystem/SoloSystem/")
HERE = os.path.dirname(os.path.abspath(__file__))


def base_dir():
    return os.environ.get("ANDROID_PRIVATE") or HERE


def updates_dir():
    return os.path.join(base_dir(), "updates")


def log(msg):
    try:
        with open(os.path.join(base_dir(), "update.log"), "a") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def builtin_id():
    h = hashlib.sha1()
    for n in UPDATE_FILES:
        try:
            with open(os.path.join(HERE, n), "rb") as f:
                h.update(f.read())
        except Exception:
            pass
    return h.hexdigest()


def discard(reason=""):
    d = updates_dir()
    shutil.rmtree(d, ignore_errors=True)
    shutil.rmtree(d + ".new", ignore_errors=True)
    if d in sys.path:
        sys.path.remove(d)
    if reason:
        log("live code discarded: " + reason)


def _purge():
    for m in ("app_main", "engine", "service_main", "notifier"):
        sys.modules.pop(m, None)


def _live_ok(need):
    d = updates_dir()
    if not all(os.path.exists(os.path.join(d, n)) for n in need):
        return False
    try:
        with open(os.path.join(d, "base_id")) as f:
            if f.read().strip() != builtin_id():
                discard("APK changed, old live code was stale")
                return False
    except Exception:
        discard("live code had no base id")
        return False
    return True


def is_live():
    m = sys.modules.get("app_main")
    try:
        return bool(m) and os.path.abspath(os.path.dirname(m.__file__)) == os.path.abspath(updates_dir())
    except Exception:
        return False


def confirm():
    """Called once the app is up: tells the next start that the live code did not crash."""
    try:
        os.remove(os.path.join(updates_dir(), "booting"))
    except OSError:
        pass


def boot():
    d = updates_dir()
    live = _live_ok(["app_main.py", "engine.py"])
    flag = os.path.join(d, "booting")
    if live and os.path.exists(flag):
        discard("last start with live code never finished")
        live = False
    if live:
        with open(flag, "w") as f:
            f.write(str(time.time()))
        sys.path.insert(0, d)
    try:
        import app_main
        app_main.run()
    except Exception:
        if not live:
            raise
        import traceback
        log("live code crashed, reverting:\n" + traceback.format_exc())
        discard()
        _purge()
        import app_main
        app_main.run()
