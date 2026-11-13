"""python-for-android build hook that adds a home screen widget to the app.
It is only used when the 'widget' option is ticked in the Build APK workflow (buildozer.spec gets 'p4a.hook = ...').
It writes the widget's Java class and XML into the build and registers the receiver in the Android manifest."""
import os

JAVA = r'''package org.hunter.solosystem;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.util.TypedValue;
import android.widget.RemoteViews;

public class StatusWidget extends AppWidgetProvider {
    private static final String PREFS = "system_widget";

    public static void push(Context context, String text) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("text", text).apply();
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        int[] ids = manager.getAppWidgetIds(new ComponentName(context, StatusWidget.class));
        if (ids != null && ids.length > 0) {
            new StatusWidget().onUpdate(context, manager, ids);
        }
    }

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        String text = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString("text", "THE SYSTEM\nOpen the app once to load your status.");
        for (int id : ids) {
            RemoteViews views = new RemoteViews("android", android.R.layout.simple_list_item_1);
            views.setTextViewText(android.R.id.text1, text);
            views.setTextColor(android.R.id.text1, Color.rgb(154, 240, 255));
            views.setTextViewTextSize(android.R.id.text1, TypedValue.COMPLEX_UNIT_SP, 13);
            views.setInt(android.R.id.text1, "setBackgroundColor", Color.rgb(5, 10, 30));
            Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
            if (launch != null) {
                int flags = PendingIntent.FLAG_UPDATE_CURRENT;
                if (Build.VERSION.SDK_INT >= 23) {
                    flags |= PendingIntent.FLAG_IMMUTABLE;
                }
                views.setOnClickPendingIntent(android.R.id.text1, PendingIntent.getActivity(context, 0, launch, flags));
            }
            manager.updateAppWidget(id, views);
        }
    }
}
'''

PROVIDER_XML = '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp"
    android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@android:layout/simple_list_item_1"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
'''

RECEIVER = '''
        <receiver android:name="org.hunter.solosystem.StatusWidget" android:exported="true" android:label="The System status">
            <intent-filter>
                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
            </intent-filter>
            <meta-data android:name="android.appwidget.provider" android:resource="@xml/status_widget_info" />
        </receiver>
'''


def _dist_dir(toolchain):
    dist = getattr(toolchain, "_dist", None)
    path = getattr(dist, "dist_dir", None)
    if not path:
        raise RuntimeError("widget hook: cannot find the dist directory")
    return path


def install(dist_dir):
    java_dir = os.path.join(dist_dir, "src", "main", "java", "org", "hunter", "solosystem")
    xml_dir = os.path.join(dist_dir, "src", "main", "res", "xml")
    os.makedirs(java_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    with open(os.path.join(java_dir, "StatusWidget.java"), "w") as f:
        f.write(JAVA)
    with open(os.path.join(xml_dir, "status_widget_info.xml"), "w") as f:
        f.write(PROVIDER_XML)
    template = None
    for root, _, files in os.walk(dist_dir):
        if "AndroidManifest.tmpl.xml" in files:
            template = os.path.join(root, "AndroidManifest.tmpl.xml")
            break
    if template is None:
        raise RuntimeError("widget hook: AndroidManifest.tmpl.xml not found in " + dist_dir)
    with open(template) as f:
        text = f.read()
    if "StatusWidget" not in text:
        if text.count("</application>") != 1:
            raise RuntimeError("widget hook: unexpected manifest template")
        with open(template, "w") as f:
            f.write(text.replace("</application>", RECEIVER + "    </application>"))
    return template


def before_apk_build(toolchain):
    print("widget hook: installed into", install(_dist_dir(toolchain)))
