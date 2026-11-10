"""Background watcher (Android foreground service). While the app is closed it keeps the
24-hour quest cycle running and sends [SYSTEM] notifications."""
import os
import time

from engine import Game, hours_text

POLL = 15  # seconds between checks


def app_is_open(folder, now):
    try:
        with open(os.path.join(folder, "alive.txt")) as f:
            return now - float(f.read()) < 120
    except Exception:
        return False


def screen_unlocked():
    """True/False, or None if the phone state cannot be read."""
    try:
        from jnius import autoclass, cast
        ctx = autoclass("org.kivy.android.PythonService").mService.getApplicationContext()
        power = cast("android.os.PowerManager", ctx.getSystemService("power"))
        keyguard = cast("android.app.KeyguardManager", ctx.getSystemService("keyguard"))
        return bool(power.isInteractive()) and not bool(keyguard.isKeyguardLocked())
    except Exception:
        return None


def pending_lines(g, now):
    lines = []
    if g.d.get("unseen_arrival"):
        lines.append("A new Daily Quest has arrived.")
    left, todo = g.remaining(), g.unfinished_text()
    if todo and left < 3 * 3600:
        lines.append("%s left. Unfinished: %s" % (hours_text(left), todo))
    late = [t["text"] for t in g.d["todos"] if t.get("due") and t["due"] <= now]
    if late:
        lines.append("Overdue: " + ", ".join(late))
    return lines


def step(g, folder, state, notify, now, unlocked):
    if app_is_open(folder, now):
        state["was_unlocked"] = unlocked if unlocked is not None else True
        return
    g.reload()
    for m in g.tick():
        notify("[SYSTEM] Quest Failed", m)
    if g.arrived:
        g.arrived = False
        g.d["unseen_arrival"] = True
        g.save()
        notify("[SYSTEM] Quest Arrived", "Daily Quest: %s.\nComplete it within 24 hours or face the Penalty Zone."
               % g.quest_names())
    left = g.warning_due(now)
    if left is not None:
        notify("[SYSTEM] Warning: %s left" % hours_text(left), "Unfinished: %s" % g.unfinished_text())
    for t in g.due_todos(now):
        notify("[SYSTEM] Reminder", t["text"])
    if unlocked and state.get("was_unlocked") is False:  # the phone was just unlocked
        lines = pending_lines(g, now)
        if lines:
            notify("[SYSTEM] Waiting for you", "\n".join(lines))
    if unlocked is not None:
        state["was_unlocked"] = unlocked


def main():
    folder = os.environ.get("PYTHON_SERVICE_ARGUMENT", "")
    def notify(title, text):
        try:
            import notifier
            notifier.send(title, text)
        except Exception:
            try:
                from plyer import notification
                notification.notify(title=title, message=text, app_name="The System", timeout=10)
            except Exception:
                pass
    g = Game(os.path.join(folder, "system.json"), write=False)
    state = {}
    while True:
        try:
            step(g, folder, state, notify, time.time(), screen_unlocked())
        except Exception:
            pass
        time.sleep(POLL)


if __name__ == "__main__":
    main()
