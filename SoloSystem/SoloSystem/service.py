"""Background watcher (Android foreground service). Sends quest notifications
while the app is closed. It only READS the save file; penalties are applied
when the app is opened."""
import json, os, time

DAY = 86400


def check(path, state, now):
    """Return a list of (title, message). `state` remembers what was already sent."""
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return []
    out = []
    start = d.get("cycle_start", now)
    left = start + DAY - now
    undone = [q for q in d.get("quests", []) if not q.get("done")]
    if left <= 0 and state.get("expired") != start:
        state["expired"] = start
        if undone:
            out.append(("QUEST FAILED", "The 24 hours are over. Open the app to face the Penalty Zone."))
        else:
            out.append(("QUEST ARRIVED", "A new day begins. Open the app to receive your daily quests."))
    elif 0 < left < 7200 and undone and state.get("warned") != start:
        state["warned"] = start
        out.append(("WARNING", "Less than 2 hours left to finish your daily quests!"))
    return out


def app_is_open(folder, now):
    try:
        with open(os.path.join(folder, "alive.txt")) as f:
            return now - float(f.read()) < 120
    except Exception:
        return False


def main():
    folder = os.environ.get("PYTHON_SERVICE_ARGUMENT", "")
    path = os.path.join(folder, "system.json")
    from plyer import notification
    state = {}
    while True:
        now = time.time()
        if not app_is_open(folder, now):
            for title, msg in check(path, state, now):
                try:
                    notification.notify(title=title, message=msg, app_name="The System", timeout=10)
                except Exception:
                    pass
        time.sleep(60)


if __name__ == "__main__":
    main()
