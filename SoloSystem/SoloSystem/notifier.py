"""Android notifications through pyjnius. Works from the app and from the background service
(plyer needs an Activity, which the service does not have)."""
import time

CHANNEL_ID = "system_alerts"


def _context():
    from jnius import autoclass
    try:
        svc = autoclass("org.kivy.android.PythonService").mService
        if svc is not None:
            return svc
    except Exception:
        pass
    return autoclass("org.kivy.android.PythonActivity").mActivity


def _manager(ctx):
    from jnius import cast
    return cast("android.app.NotificationManager", ctx.getSystemService("notification"))


def enabled():
    """True / False, or None when it cannot be read."""
    try:
        return bool(_manager(_context()).areNotificationsEnabled())
    except Exception:
        return None


def send(title, text):
    from jnius import autoclass
    ctx = _context()
    nm = _manager(ctx)
    sdk = autoclass("android.os.Build$VERSION").SDK_INT
    String = autoclass("java.lang.String")
    Builder = autoclass("android.app.Notification$Builder")
    if sdk >= 26:
        importance = autoclass("android.app.NotificationManager").IMPORTANCE_HIGH
        channel = autoclass("android.app.NotificationChannel")(CHANNEL_ID, String("System alerts"), importance)
        nm.createNotificationChannel(channel)
        b = Builder(ctx, CHANNEL_ID)
    else:
        b = Builder(ctx)
    b.setSmallIcon(autoclass("android.R$drawable").ic_dialog_info)
    b.setContentTitle(String(title))
    b.setContentText(String(text))
    style = autoclass("android.app.Notification$BigTextStyle")()
    style.bigText(String(text))
    b.setStyle(style)
    intent = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName())
    if intent is not None:  # tapping the notification opens the app
        pi = autoclass("android.app.PendingIntent")
        flags = pi.FLAG_UPDATE_CURRENT | (pi.FLAG_IMMUTABLE if sdk >= 23 else 0)
        b.setContentIntent(pi.getActivity(ctx, 0, intent, flags))
    b.setAutoCancel(True)
    b.setPriority(1)
    nm.notify(int(time.time() * 1000) % 2000000000, b.build())


def vibrate(ms=400):
    from jnius import autoclass, cast
    ctx = _context()
    vib = cast("android.os.Vibrator", ctx.getSystemService("vibrator"))
    if autoclass("android.os.Build$VERSION").SDK_INT >= 26:
        vib.vibrate(autoclass("android.os.VibrationEffect").createOneShot(ms, -1))
    else:
        vib.vibrate(ms)


def share_text(text):
    from jnius import autoclass
    ctx = _context()
    intent = autoclass("android.content.Intent")
    i = intent(intent.ACTION_SEND)
    i.setType("text/plain")
    i.putExtra(intent.EXTRA_TEXT, text)
    chooser = intent.createChooser(i, autoclass("java.lang.String")("Save your backup to..."))
    chooser.addFlags(intent.FLAG_ACTIVITY_NEW_TASK)
    ctx.startActivity(chooser)


def open_settings():
    from jnius import autoclass
    ctx = _context()
    intent_cls = autoclass("android.content.Intent")
    settings = autoclass("android.provider.Settings")
    i = intent_cls(settings.ACTION_APP_NOTIFICATION_SETTINGS)
    i.putExtra(settings.EXTRA_APP_PACKAGE, ctx.getPackageName())
    i.addFlags(intent_cls.FLAG_ACTIVITY_NEW_TASK)
    ctx.startActivity(i)
