"""Downloads newer code from the GitHub repo into the app's private 'updates' folder."""
import hashlib
import os
import shutil
import ssl
import sys
import time
import urllib.request

import loader


def fetch(name, timeout=20):
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    url = "%s%s?t=%d" % (loader.REPO_RAW, name, int(time.time()))
    req = urllib.request.Request(url, headers={"User-Agent": "TheSystem-App", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8")


def current_source(name):
    for folder in (loader.updates_dir(), loader.HERE):
        p = os.path.join(folder, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    return ""


def check():
    """Returns (message, changed). Raises on network problems."""
    new = {}
    for name in loader.UPDATE_FILES:
        src = fetch(name)
        compile(src, name, "exec")  # reject files with syntax errors
        new[name] = src
    if "def run" not in new["app_main.py"] or "def main" not in new["service_main.py"]:
        raise ValueError("downloaded files look wrong")
    changed = [n for n in new if new[n] != current_source(n)]
    if not changed:
        return "Already up to date.", False
    tmp = loader.updates_dir() + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for n, s in new.items():
        with open(os.path.join(tmp, n), "w", encoding="utf-8") as f:
            f.write(s)
    with open(os.path.join(tmp, "base_id"), "w") as f:
        f.write(loader.builtin_id())
    shutil.rmtree(loader.updates_dir(), ignore_errors=True)
    os.rename(tmp, loader.updates_dir())
    loader.log("downloaded: " + ", ".join(changed))
    return "Update downloaded (%s).\nClose the app completely and open it again to use it." % ", ".join(changed), True


def code_label():
    m = sys.modules.get("app_main")
    try:
        with open(m.__file__, "rb") as f:
            h = hashlib.sha1(f.read()).hexdigest()[:7]
    except Exception:
        h = "?"
    return "%s %s" % ("live" if loader.is_live() else "built-in", h)
