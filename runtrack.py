"""Run tracking that keeps going with the screen off.
The background service owns the GPS. The app and the service talk through two small files:
  run_cmd.json   written by the app:     {"id": 123, "active": true}
  run_state.json written by the service: {"id", "active", "meters", "fixes", "accuracy", "status", "ts", "started"}"""
import json
import os
import time

from engine import RunTracker

CMD = "run_cmd.json"
STATE = "run_state.json"


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


class AndroidGps:
    """GPS through Android's LocationManager (used inside the service)."""

    def __init__(self):
        self.lm = None
        self.listener = None

    def start(self, on_fix, on_status):
        from jnius import autoclass, cast, PythonJavaClass, java_method

        class Listener(PythonJavaClass):
            __javainterfaces__ = ["android/location/LocationListener"]
            __javacontext__ = "app"

            def __init__(s, fix, status):
                super().__init__()
                s.fix, s.status = fix, status

            @java_method("(Landroid/location/Location;)V")
            def onLocationChanged(s, loc):
                s.fix(loc.getLatitude(), loc.getLongitude(), loc.getAccuracy())

            @java_method("(Ljava/lang/String;)V")
            def onProviderEnabled(s, provider):
                s.status("%s on" % provider)

            @java_method("(Ljava/lang/String;)V")
            def onProviderDisabled(s, provider):
                s.status("%s is OFF - turn Location on" % provider)

            @java_method("(Ljava/lang/String;ILandroid/os/Bundle;)V")
            def onStatusChanged(s, provider, status, extras):
                pass

        ctx = autoclass("org.kivy.android.PythonService").mService
        self.lm = cast("android.location.LocationManager", ctx.getSystemService("location"))
        self.listener = Listener(on_fix, on_status)
        looper = autoclass("android.os.Looper").getMainLooper()
        started = []
        for provider in ("gps", "network"):
            try:
                if self.lm.isProviderEnabled(provider):
                    self.lm.requestLocationUpdates(provider, 1000, 0.0, self.listener, looper)
                    started.append(provider)
            except Exception:
                pass
        if not started:
            raise RuntimeError("Location is switched off or not allowed")

    def stop(self):
        if self.lm is not None and self.listener is not None:
            self.lm.removeUpdates(self.listener)
        self.lm = self.listener = None


class RunService:
    """Lives in the service. Call tick() about once a second."""

    def __init__(self, folder, gps=None):
        self.cmd_path = os.path.join(folder, CMD)
        self.state_path = os.path.join(folder, STATE)
        self.gps = gps
        self.tracker = None
        self.id = None
        self.fixes = 0
        self.acc = None
        self.status = ""
        self.started = 0.0
        self.last_write = 0.0

    def on_fix(self, lat, lon, accuracy=None, now=None):
        if self.tracker is None:
            return
        self.fixes += 1
        self.acc = accuracy
        self.tracker.update(float(lat), float(lon), accuracy, now)
        self.status = "Tracking" if self.tracker.last else "Signal too weak - move to open sky"

    def on_status(self, text):
        self.status = text

    def tick(self, now=None):
        now = time.time() if now is None else now
        cmd = read_json(self.cmd_path) or {}
        if cmd.get("active") and cmd.get("id") != self.id:
            self._start(cmd["id"], now)
        elif not cmd.get("active") and self.id is not None:
            self._stop(now)
        if self.id is not None and now - self.last_write >= 1.0:
            self._write(now, True)

    def _start(self, rid, now):
        if self.id is not None:
            self._stop(now)
        self.tracker, self.id, self.fixes, self.acc, self.started = RunTracker(), rid, 0, None, now
        self.status = "Starting GPS..."
        try:
            self.gps.start(self.on_fix, self.on_status)
            self.status = "Waiting for GPS (can take 1 minute)"
        except Exception as e:
            self.status = "GPS error: %s" % e
        self._write(now, True)

    def _stop(self, now):
        try:
            self.gps.stop()
        except Exception:
            pass
        self._write(now, False)
        self.id = None

    def _write(self, now, active):
        self.last_write = now
        write_json(self.state_path, {
            "id": self.id, "active": active, "meters": self.tracker.meters if self.tracker else 0.0,
            "fixes": self.fixes, "accuracy": self.acc, "status": self.status, "ts": now, "started": self.started})
