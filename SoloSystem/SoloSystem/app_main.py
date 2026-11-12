import os
import threading
import time
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.factory import Factory
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from engine import Game, due_from, hours_text, today_str, tomorrow_str, CATS, norm_cat, SHOP, TITLES, hp_max, rank_for, exp_needed, log_line, days_text, habits_to_text, text_to_habits, quests_to_text, text_to_quests

import loader
import updater
try:
    import notifier
except ImportError:
    notifier = None

Window.softinput_mode = "below_target"

KV = """
<Panel@BoxLayout>:
    canvas.before:
        Color:
            rgba: 0.03, 0.07, 0.16, 0.95
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: 0.25, 0.85, 1, 1
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1.3
<L@Label>:
    color: 0.6, 0.95, 1, 1
    markup: True
<SB@Button>:
    background_normal: ''
    background_color: 0.05, 0.18, 0.35, 1
    color: 0.6, 0.95, 1, 1
    bold: True
<TI@TextInput>:
    background_color: 0.02, 0.05, 0.12, 1
    foreground_color: 0.7, 1, 1, 1
    cursor_color: 0.3, 0.9, 1, 1

<StatusScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(10)
        L:
            text: '[b][ STATUS ][/b]'
            font_size: '24sp'
            size_hint_y: None
            height: dp(40)
        Panel:
            orientation: 'vertical'
            padding: dp(12)
            L:
                text: app.name_text
                font_size: '20sp'
            L:
                text: app.level_text
                font_size: '18sp'
            L:
                text: app.rank_text
                font_size: '30sp'
                color: 1, 0.85, 0.3, 1
            L:
                text: app.exp_text
            ProgressBar:
                max: 100
                value: app.exp_pct
                size_hint_y: None
                height: dp(14)
            L:
                text: app.hp_text
                color: 1, 0.45, 0.45, 1
            ProgressBar:
                max: 100
                value: app.hp_pct
                size_hint_y: None
                height: dp(14)
        Panel:
            padding: dp(12)
            L:
                text: app.stats_text
                halign: 'center'
                valign: 'middle'
                text_size: self.size
        L:
            text: app.extra_text
            size_hint_y: None
            height: dp(48)
        SB:
            text: 'HISTORY'
            size_hint_y: None
            height: dp(44)
            on_release: app.open_history()

<LogScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ LOG HABIT ][/b]'
            font_size: '24sp'
            size_hint_y: None
            height: dp(40)
        TI:
            id: habit_in
            hint_text: 'e.g. did a workout / scrolling tiktok'
            multiline: False
            size_hint_y: None
            height: dp(44)
            on_text_validate: app.log_habit(self.text); self.text = ''
        SB:
            text: 'REGISTER'
            size_hint_y: None
            height: dp(48)
            on_release: app.log_habit(habit_in.text); habit_in.text = ''
        L:
            text: app.result_text
            size_hint_y: None
            height: dp(36)
        L:
            text: 'Tap an entry to undo or rename it'
            font_size: '12sp'
            size_hint_y: None
            height: dp(20)
        ScrollView:
            GridLayout:
                id: log_box
                cols: 1
                spacing: dp(6)
                size_hint_y: None
                height: self.minimum_height

<QuestScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ DAILY QUEST ][/b]'
            font_size: '24sp'
            size_hint_y: None
            height: dp(36)
        L:
            text: app.timer_text
            color: 1, 0.4, 0.4, 1
            size_hint_y: None
            height: dp(28)
        SB:
            text: 'START GPS RUN TRACKER'
            size_hint_y: None
            height: dp(48)
            on_release: app.open_run()
        ScrollView:
            GridLayout:
                id: quest_box
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height

<TasksScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ ROUTINE & TO-DO ][/b]'
            font_size: '22sp'
            size_hint_y: None
            height: dp(40)
        ScrollView:
            GridLayout:
                id: task_box
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height

<JournalScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ JOURNAL BOOK ][/b]'
            font_size: '22sp'
            size_hint_y: None
            height: dp(40)
        SB:
            text: '+ WRITE NEW ENTRY'
            size_hint_y: None
            height: dp(52)
            on_release: app.write_journal()
        ScrollView:
            GridLayout:
                id: journal_box
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height
        SB:
            text: 'BACK'
            size_hint_y: None
            height: dp(48)
            on_release: app.go('tasks')

<PlannerScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ TOMORROW PLANNER ][/b]'
            font_size: '22sp'
            size_hint_y: None
            height: dp(40)
        SB:
            text: '+ ADD TO TOMORROW'
            size_hint_y: None
            height: dp(52)
            on_release: app.add_plan_dialog()
        ScrollView:
            GridLayout:
                id: planner_box
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height
        SB:
            text: 'BACK'
            size_hint_y: None
            height: dp(48)
            on_release: app.go('tasks')

<Bar@Widget>:
    value: 0
    canvas:
        Color:
            rgba: 0.55, 0.3, 1, 1
        Rectangle:
            pos: self.x, self.y + dp(4)
            size: max(self.width * self.value, 1), self.height - dp(8)

<Cell@Label>:
    bg: 0.1, 0.1, 0.18, 1
    color: 0.8, 0.95, 1, 1
    canvas.before:
        Color:
            rgba: self.bg
        Rectangle:
            pos: self.x + dp(1), self.y + dp(1)
            size: self.width - dp(2), self.height - dp(2)

<HistoryScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ HISTORY ][/b]'
            font_size: '22sp'
            size_hint_y: None
            height: dp(40)
        ScrollView:
            GridLayout:
                id: hist_box
                cols: 1
                spacing: dp(6)
                size_hint_y: None
                height: self.minimum_height
        SB:
            text: 'BACK'
            size_hint_y: None
            height: dp(48)
            on_release: app.go('status')

<ShopScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        L:
            text: '[b][ SHOP & TITLES ][/b]'
            font_size: '24sp'
            size_hint_y: None
            height: dp(40)
        L:
            text: app.gold_text
            color: 1, 0.85, 0.3, 1
            size_hint_y: None
            height: dp(28)
        ScrollView:
            GridLayout:
                id: shop_box
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height

<AdminScreen>:
    ScrollView:
        GridLayout:
            cols: 1
            spacing: dp(8)
            padding: dp(12)
            size_hint_y: None
            height: self.minimum_height
            L:
                text: '[b][ ADMIN ][/b]'
                font_size: '24sp'
                size_hint_y: None
                height: dp(40)
            TI:
                id: amount_in
                hint_text: 'EXP amount'
                input_filter: 'int'
                multiline: False
                size_hint_y: None
                height: dp(44)
            BoxLayout:
                size_hint_y: None
                height: dp(44)
                spacing: dp(8)
                SB:
                    text: '+ EXP'
                    on_release: app.admin_exp(amount_in.text, 1)
                SB:
                    text: '- EXP'
                    on_release: app.admin_exp(amount_in.text, -1)
                SB:
                    text: 'SET LEVEL'
                    on_release: app.admin_level(amount_in.text)
            BoxLayout:
                size_hint_y: None
                height: dp(44)
                spacing: dp(8)
                SB:
                    text: '+ GOLD'
                    on_release: app.admin_gold(amount_in.text)
                SB:
                    text: 'FULL HEAL'
                    on_release: app.admin_heal()
            L:
                text: 'Habit rules  (keywords, comma separated | EXP value | Physical / Mental / Spiritual)'
                text_size: self.width, None
                halign: 'left'
                valign: 'middle'
                size_hint_y: None
                height: dp(46)
            TI:
                id: habits_in
                size_hint_y: None
                height: dp(260)
            L:
                text: 'Daily quests  (name | reward | penalty | punishment | target | unit | category)'
                text_size: self.width, None
                halign: 'left'
                valign: 'middle'
                size_hint_y: None
                height: dp(46)
            TI:
                id: quests_in
                size_hint_y: None
                height: dp(160)
            SB:
                text: 'SAVE RULES + QUESTS'
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_save(habits_in.text, quests_in.text)
            SB:
                text: 'RE-ISSUE TODAY\\'S QUESTS'
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_reissue()
            L:
                text: '[b]Add a daily quest[/b]'
                size_hint_y: None
                height: dp(28)
            TI:
                id: q_name
                hint_text: 'Quest name (e.g. Pull-ups)'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_target
                hint_text: 'Target amount (e.g. 50)'
                input_filter: 'float'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_unit
                hint_text: 'Unit (reps, km, minutes...)'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_reward
                hint_text: 'Reward EXP (e.g. 40)'
                input_filter: 'int'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_penalty
                hint_text: 'Penalty EXP if failed (e.g. 30)'
                input_filter: 'int'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_punish
                hint_text: 'Punishment if failed'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: q_cat
                hint_text: 'Category: Physical, Mental or Spiritual'
                multiline: False
                size_hint_y: None
                height: dp(44)
            SB:
                text: 'ADD QUEST'
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_add_quest(q_name.text, q_target.text, q_unit.text, q_reward.text, q_penalty.text, q_punish.text, q_cat.text)
            TI:
                id: name_in
                hint_text: 'Player name'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: pin_in
                hint_text: 'New admin PIN'
                password: True
                multiline: False
                size_hint_y: None
                height: dp(44)
            SB:
                text: 'SAVE NAME / PIN'
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_profile(name_in.text, pin_in.text)
            SB:
                text: 'FULL RESET'
                background_color: 0.4, 0.05, 0.05, 1
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_reset()
            L:
                text: app.update_text
                text_size: self.width, None
                halign: 'center'
                size_hint_y: None
                height: dp(44)
            SB:
                text: 'EXPORT BACKUP'
                size_hint_y: None
                height: dp(48)
                on_release: app.export_backup()
            SB:
                text: 'RESTORE BACKUP'
                size_hint_y: None
                height: dp(48)
                on_release: app.restore_backup()
            SB:
                text: 'TOGGLE QUEST SCALING'
                size_hint_y: None
                height: dp(48)
                on_release: app.toggle_scaling()
            SB:
                text: 'TEST NOTIFICATION'
                size_hint_y: None
                height: dp(48)
                on_release: app.test_notification()
            SB:
                text: 'CHECK FOR UPDATES'
                size_hint_y: None
                height: dp(48)
                on_release: app.check_updates()
            SB:
                text: 'REVERT TO BUILT-IN CODE'
                size_hint_y: None
                height: dp(48)
                on_release: app.admin_revert()
            SB:
                text: 'LOCK ADMIN'
                size_hint_y: None
                height: dp(48)
                on_release: app.lock_admin()

BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.01, 0.02, 0.06, 1
        Rectangle:
            pos: self.pos
            size: self.size
    ScreenManager:
        id: sm
        StatusScreen:
            name: 'status'
        LogScreen:
            name: 'log'
        TasksScreen:
            name: 'tasks'
        JournalScreen:
            name: 'journal'
        PlannerScreen:
            name: 'planner'
        HistoryScreen:
            name: 'history'
        QuestScreen:
            name: 'quests'
        ShopScreen:
            name: 'shop'
        AdminScreen:
            name: 'admin'
    BoxLayout:
        size_hint_y: None
        height: dp(56)
        spacing: dp(2)
        SB:
            font_size: '12sp'
            text: 'STATUS'
            on_release: sm.current = 'status'
        SB:
            font_size: '12sp'
            text: 'LOG'
            on_release: sm.current = 'log'
        SB:
            font_size: '12sp'
            text: 'TASKS'
            on_release: sm.current = 'tasks'
        SB:
            font_size: '12sp'
            text: 'QUESTS'
            on_release: sm.current = 'quests'
        SB:
            font_size: '12sp'
            text: 'SHOP'
            on_release: sm.current = 'shop'
        SB:
            font_size: '12sp'
            text: 'ADMIN'
            on_release: app.open_admin()
"""


class StatusScreen(Screen):
    pass


class LogScreen(Screen):
    pass


class QuestScreen(Screen):
    pass


class AdminScreen(Screen):
    pass


class TasksScreen(Screen):
    pass


class JournalScreen(Screen):
    pass


class PlannerScreen(Screen):
    pass


class HistoryScreen(Screen):
    pass


class ShopScreen(Screen):
    pass


class SoloSystemApp(App):
    name_text = StringProperty("")
    level_text = StringProperty("")
    rank_text = StringProperty("")
    exp_text = StringProperty("")
    exp_pct = NumericProperty(0)
    stats_text = StringProperty("")
    extra_text = StringProperty("")
    timer_text = StringProperty("")
    result_text = StringProperty("")
    log_text = StringProperty("")
    hp_text = StringProperty("")
    hp_pct = NumericProperty(0)
    gold_text = StringProperty("")
    update_text = StringProperty("")

    admin_unlocked = False
    _after_log = None

    def build(self):
        self.title = "The System"
        self.beat()
        self.g = Game(os.path.join(self.user_data_dir, "system.json"))
        self.root_widget = Builder.load_string(KV)
        Clock.schedule_once(lambda dt: self.check_cycle(), 0.5)
        Clock.schedule_once(lambda dt: loader.confirm(), 2)
        Clock.schedule_once(lambda dt: self.check_updates(auto=True), 4)
        Clock.schedule_interval(lambda dt: self.update_timer(), 1)
        Clock.schedule_interval(lambda dt: self.check_cycle(), 30)
        return self.root_widget

    def on_start(self):
        try:  # Android 13+ notification permission
            from android.permissions import request_permissions
            request_permissions(["android.permission.POST_NOTIFICATIONS"])
        except Exception:
            pass
        try:  # background quest watcher (keeps notifications working when the app is closed)
            from android import AndroidService
            AndroidService("The System", "Watching your quests").start(self.user_data_dir)
        except Exception:
            pass

    def notify(self, title, text):
        try:
            notifier.send(title, text)
        except Exception:
            try:
                from plyer import notification
                notification.notify(title=title, message=text, app_name="The System", timeout=10)
            except Exception:
                pass

    def test_notification(self):
        try:
            if notifier is None:
                raise RuntimeError("notifier.py is missing - install the newest APK")
            try:
                from android.permissions import request_permissions
                request_permissions(["android.permission.POST_NOTIFICATIONS"])
            except ImportError:
                pass
            if notifier.enabled() is False:
                self.dialog("[ NOTIFICATIONS ]", "Notifications are turned off for this app.\nOpen settings and switch them on.",
                            [("OPEN SETTINGS", lambda v: notifier.open_settings()), ("BACK", lambda v: None)],
                            size=(0.9, 0.45))
                return
            notifier.send("[SYSTEM] Test", "If you can read this in your notification bar, alerts work.")
            self.popup("[ TEST ]", "Test notification sent.\\nPull down your notification bar to look.")
        except Exception as e:
            self.popup("[ NOTIFICATIONS ]", "Could not send: %s" % e)

    def beat(self):
        try:
            with open(os.path.join(self.user_data_dir, "alive.txt"), "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass

    def on_resume(self):
        self.beat()
        try:
            self.g.reload()  # the background service may have changed the save while the app was paused
            self.check_cycle()
        except Exception:
            pass

    def on_stop(self):
        loader.confirm()

    def check_updates(self, auto=False):
        def work():
            try:
                msg, changed = updater.check()
            except Exception as e:
                msg, changed = "Update check failed: %s" % e, False
            Clock.schedule_once(lambda dt: self.update_done(msg, changed, auto), 0)
        threading.Thread(target=work, daemon=True).start()

    def update_done(self, msg, changed, auto):
        self.update_text = msg
        if changed or not auto:
            self.popup("[ UPDATE ]", msg)

    def admin_revert(self):
        loader.discard()
        self.update_text = "Reverted to built-in code. Restart the app."
        self.popup("[ UPDATE ]", "Live updates removed.\nClose the app and open it again to use the built-in code.")

    # ---------- helpers ----------
    def vibrate(self, ms=400):
        try:
            notifier.vibrate(ms)
        except Exception:
            pass

    def popup(self, title, text, color=(0.25, 0.85, 1, 1)):
        if "LEVEL UP" in text:
            title, color = "[ LEVEL UP ]", (1, 0.85, 0.3, 1)
            text = text.replace("LEVEL UP!", "[b]LEVEL UP![/b]")
            self.vibrate()
        lab = Label(text=text, markup=True, color=(0.7, 1, 1, 1), halign="center")
        lab.bind(width=lambda w, v: setattr(w, "text_size", (v - 20, None)))
        Popup(title=title, content=lab, size_hint=(0.88, 0.45), title_color=color,
              separator_color=color, background_color=(0.02, 0.05, 0.12, 1)).open()

    def screen(self, name):
        return self.root_widget.ids.sm.get_screen(name)

    def refresh(self):
        d = self.g.d
        need = exp_needed(d["level"])
        self.name_text = "[b]%s[/b]  <%s>" % (d["name"], d["title"])
        pend = self.g.pending_trial_rank()
        self.level_text = "LEVEL  %d" % d["level"] + ("   (Promotion Trial: Rank %s)" % pend if pend else "")
        self.rank_text = "RANK  %s" % self.g.current_rank()
        self.exp_text = "EXP  %d / %d" % (d["exp"], need)
        self.exp_pct = d["exp"] * 100.0 / need
        hm = hp_max(d["level"])
        self.hp_text = "HP  %d / %d" % (d["hp"], hm)
        self.hp_pct = d["hp"] * 100.0 / hm
        self.gold_text = "GOLD  %d" % d["gold"]
        a = d["attrs"]
        tot = sum(a.values()) or 1
        cols = {"Physical": "ff6b6b", "Mental": "6bb6ff", "Spiritual": "c08bff"}
        self.stats_text = "\n\n".join(
            "[color=%s]%s Attributes[/color]\n[size=28sp][b]%d[/b][/size]   (%d%%)" % (cols[k], k, a[k], round(a[k] * 100.0 / tot))
            for k in CATS)
        self.extra_text = "Streak: %d days   |   Pending punishments: %d\nBuild 1.7 (%s)" % (d["streak"], len(d["punishments"]), updater.code_label())
        self.log_text = ""
        self.build_quests()
        self.build_shop()
        self.build_tasks()
        self.build_journal()
        self.build_planner()
        self.build_log()

    def mkbtn(self, text, cb, dis=False, color=(0.05, 0.18, 0.35, 1)):
        b = Button(text=text, size_hint_y=None, height=dp(64), background_normal="", disabled=dis,
                   background_color=color, color=(0.6, 0.95, 1, 1), halign="center")
        b.bind(width=lambda w, v: setattr(w, "text_size", (v - 16, None)))
        if cb:
            b.bind(on_release=cb)
        return b

    def build_shop(self):
        box = self.screen("shop").ids.shop_box
        box.clear_widgets()
        d = self.g.d
        box.add_widget(Label(text="[b]ITEMS[/b]", markup=True, size_hint_y=None, height=dp(28), color=(1, 0.85, 0.3, 1)))
        for key, (name, desc, cost) in SHOP.items():
            box.add_widget(self.mkbtn("%s - %s\nCost: %d gold" % (name, desc, cost), lambda w, k=key: self.buy(k)))
        box.add_widget(Label(text="[b]MY REWARDS  (real life, you set the price)[/b]", markup=True, size_hint_y=None, height=dp(28), color=(1, 0.85, 0.3, 1)))
        for r in d["rewards"]:
            box.add_widget(self.task_row("%s\nCost: %d gold" % (r["name"], r["cost"]), lambda r=r: self.confirm_reward(r),
                                         lambda r=r: (self.g.remove_reward(r["id"]), self.refresh())))
        box.add_widget(self.mkbtn("+ ADD REWARD", lambda w: self.add_reward_dialog()))
        box.add_widget(Label(text="[b]TITLES (tap to equip)[/b]", markup=True, size_hint_y=None, height=dp(28), color=(1, 0.85, 0.3, 1)))
        for name, desc, cond in TITLES:
            if name in d["titles"]:
                mark = "[EQUIPPED]  " if name == d["title"] else ""
                box.add_widget(self.mkbtn("%s%s\n%s" % (mark, name, desc), lambda w, n=name: self.equip(n),
                                          color=(0.05, 0.3, 0.2, 1) if mark else (0.05, 0.18, 0.35, 1)))
            else:
                box.add_widget(self.mkbtn("???  LOCKED\n%s" % desc, None, dis=True))

    def buy(self, key):
        msg = self.g.buy(key)
        self.refresh()
        self.popup("[ SHOP ]", msg)

    def equip(self, name):
        self.g.d["title"] = name
        self.g.save()
        self.refresh()

    def build_quests(self):
        box = self.screen("quests").ids.quest_box
        box.clear_widgets()
        d = self.g.d
        for i, q in enumerate(d["quests"]):
            mark = "[X]" if q["done"] else "[  ]"
            tgt = q.get("target", 1)
            if tgt > 1:
                label = "%s  %s   %g / %g %s\n(+%d EXP | fail: -%d EXP)" % (
                    mark, q["name"], q.get("progress", 0), tgt, q.get("unit", ""), q["reward"], q["penalty"])
            else:
                label = "%s  %s   (+%d EXP | fail: -%d EXP)" % (mark, q["name"], q["reward"], q["penalty"])
            b = Button(text=label,
                       size_hint_y=None, height=dp(60), background_normal="", disabled=q["done"],
                       background_color=(0.05, 0.3, 0.2, 1) if q["done"] else (0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), halign="center")
            b.bind(width=lambda w, v: setattr(w, "text_size", (v - 16, None)))
            b.bind(on_release=lambda w, idx=i: self.quest_tapped(idx))
            box.add_widget(b)
        for i, p in enumerate(d["punishments"]):
            b = Button(text="PENALTY: %s\n(tap when completed)" % p, size_hint_y=None, height=dp(70),
                       background_normal="", background_color=(0.4, 0.05, 0.08, 1), halign="center",
                       color=(1, 0.8, 0.8, 1))
            b.bind(width=lambda w, v: setattr(w, "text_size", (v - 16, None)))
            b.bind(on_release=lambda w, idx=i: self.finish_punishment(idx))
            box.add_widget(b)

    def update_timer(self):
        r = int(self.g.remaining())
        self.timer_text = "TIME LEFT  %02d:%02d:%02d" % (r // 3600, r % 3600 // 60, r % 60)

    def check_cycle(self):
        try:  # heartbeat so the background service stays quiet while the app is open
            with open(os.path.join(self.user_data_dir, 'alive.txt'), 'w') as f:
                f.write(str(__import__('time').time()))
        except Exception:
            pass
        msgs = self.g.tick()
        self.refresh()
        if msgs:
            self.popup("[ DAILY REPORT ]", "\n\n".join(msgs), (1, 0.3, 0.3, 1))
        if self.g.arrived:
            self.g.arrived = False
            self.g.d["unseen_arrival"] = False
            self.notify("QUEST ARRIVED", "Daily quests issued. You have 24 hours. Failure has consequences.")
            if not msgs:
                self.popup("[ QUEST ARRIVED ]", "Daily quests issued.\nComplete them within 24 hours\nor face the Penalty Zone.")
        d = self.g.d
        if self.g.d.get("unseen_arrival"):  # a quest arrived while the app was closed
            self.g.d["unseen_arrival"] = False
            self.g.save()
            if not msgs:
                self.popup("[ QUEST ARRIVED ]", "A new Daily Quest has arrived.\nComplete it within 24 hours\nor face the Penalty Zone.")
        left = self.g.warning_due()
        if left is not None:
            txt = "%s left to finish your daily quests!\nUnfinished: %s" % (hours_text(left), self.g.unfinished_text())
            self.notify("[SYSTEM] Warning", txt)
            self.popup("[ WARNING ]", txt, (1, 0.3, 0.3, 1))
        due = self.g.due_todos()
        if due:
            self.refresh()
            self.notify("REMINDER", "; ".join(t["text"] for t in due))
            self.popup("[ REMINDER ]", "Time to do:\n[b]%s[/b]\n\nTap it in the TASKS tab when it is done." %
                       "\n".join(t["text"] for t in due))

    # ---------- player actions ----------
    def log_habit(self, text):
        text = text.strip()
        if not text:
            return
        self._after_log = None
        self.ask_done(text)

    def ask_done(self, text):
        self.dialog("[ SYSTEM ]", "Did you already do this?\n[b]%s[/b]" % text,
                    [("YES, I DID IT", lambda v: self.process_habit(text, back=lambda: self.ask_done(text))),
                     ("NOT YET  (add to to-do)", lambda v: self.ask_reminder(text, back=lambda: self.ask_done(text))),
                     ("BACK", lambda v: self.restore_log_text(text))], size=(0.9, 0.55))

    def restore_log_text(self, text):
        self.screen("log").ids.habit_in.text = text

    def _back_button(self, box, pop, back):
        b = Button(text="BACK", background_normal="", background_color=(0.25, 0.1, 0.1, 1),
                   color=(1, 0.8, 0.8, 1), size_hint_y=None, height=dp(44))
        b.bind(on_release=lambda w: (pop.dismiss(), back() if back else None))
        box.add_widget(b)

    def process_habit(self, text, back=None):
        h = self.g.detect(text)
        if h is None:
            self.ask_classify(text, back)
            return
        cat = norm_cat(h.get("stat", ""))
        if h["value"] > 0 and not cat:
            self.ask_category(text, lambda c: self._log_known(h, text, c), back)
            return
        self.show_result(self.g.apply_habit(text, h["value"], cat))

    def show_result(self, msgs):
        self.result_text = msgs[0]
        cb, self._after_log = self._after_log, None
        if cb:
            cb()
        self.refresh()
        if self.root_widget.ids.sm.current != "log":
            self.popup("[ LOGGED ]", "\n".join(msgs))
        elif len(msgs) > 1:
            self.popup("[ SYSTEM ]", "\n".join(msgs[1:]))

    def ask_classify(self, text, back=None):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Unknown habit. Classify it:\n[b]%s[/b]" % text, markup=True,
                             color=(0.7, 1, 1, 1)))
        pop = Popup(title="[ SYSTEM ]", content=box, size_hint=(0.9, 0.75), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))
        for label, val in (("EXCELLENT  +40", 40), ("GOOD  +20", 20), ("NEUTRAL  0", 0), ("BAD  -10", -10), ("SEVERE  -40", -40)):
            b = Button(text=label, background_normal="", background_color=(0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), size_hint_y=None, height=dp(44))
            b.bind(on_release=lambda w, v=val: self.classified(pop, text, v, back))
            box.add_widget(b)
        self._back_button(box, pop, back)
        pop.open()

    def classified(self, pop, text, val, back=None):
        pop.dismiss()
        if val > 0:
            self.ask_category(text, lambda c: self._log_new(text, val, c), back=lambda: self.ask_classify(text, back))
        else:
            self._log_new(text, val, "")

    def _log_new(self, text, val, cat):
        self.g.add_rule(text, val, cat)
        self.show_result(self.g.apply_habit(text, val, cat))

    def _log_known(self, h, text, cat):
        h["stat"] = cat
        self.show_result(self.g.apply_habit(text, h["value"], cat))

    def ask_category(self, text, callback, back=None):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Which kind of habit is this?\n[b]%s[/b]" % text, markup=True, color=(0.7, 1, 1, 1)))
        pop = Popup(title="[ SYSTEM ]", content=box, size_hint=(0.9, 0.7), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))
        for cat in CATS:
            b = Button(text=cat.upper(), background_normal="", background_color=(0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), size_hint_y=None, height=dp(48))
            b.bind(on_release=lambda w, c=cat: (pop.dismiss(), callback(c)))
            box.add_widget(b)
        self._back_button(box, pop, back)
        pop.open()

    def quest_tapped(self, i):
        if self.g.d["quests"][i].get("target", 1) > 1:
            self.ask_amount(i)
        else:
            self.finish_quest(i)

    def ask_amount(self, i):
        q = self.g.d["quests"][i]
        target, done = q.get("target", 1), q.get("progress", 0)
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(Label(text="[b]%s[/b]\n%g / %g %s done" % (q["name"], done, target, q.get("unit", "")),
                             markup=True, color=(0.7, 1, 1, 1)))
        inp = TextInput(hint_text="Amount to add (e.g. 20)", input_filter="float", multiline=False,
                        size_hint_y=None, height=dp(44), background_color=(0.02, 0.05, 0.12, 1),
                        foreground_color=(0.7, 1, 1, 1), cursor_color=(0.3, 0.9, 1, 1))
        box.add_widget(inp)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        pop = Popup(title="[ ADD PROGRESS ]", content=box, size_hint=(0.9, 0.5), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))

        def add(*a):
            try:
                n = float(inp.text)
            except ValueError:
                return
            pop.dismiss()
            self.apply_progress(i, n)

        def full(*a):
            pop.dismiss()
            self.apply_progress(i, target - done)
        for text, cb in (("ADD", add), ("COMPLETE ALL", full)):
            b = Button(text=text, background_normal="", background_color=(0.05, 0.18, 0.35, 1), color=(0.6, 0.95, 1, 1))
            b.bind(on_release=cb)
            row.add_widget(b)
        inp.bind(on_text_validate=add)
        box.add_widget(row)
        pop.open()

    def apply_progress(self, i, amount):
        msgs = self.g.add_progress(i, amount)
        self.refresh()
        if msgs:
            self.popup("[ QUEST ]", "\n".join(msgs))

    def finish_quest(self, i):
        msgs = self.g.complete_quest(i)
        self.refresh()
        if msgs:
            self.popup("[ QUEST ]", "\n".join(msgs))

    def finish_punishment(self, i):
        self.g.complete_punishment(i)
        self.refresh()

    # ---------- routine + to-do ----------
    def dialog(self, title, text, buttons, hint=None, size=(0.9, 0.5), multiline=False, height=dp(44),
               text_in="", readonly=False):
        """Popup with optional text box. Each button callback gets the typed text; return False to keep it open."""
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(Label(text=text, markup=True, color=(0.7, 1, 1, 1), halign="center"))
        inp = None
        if hint is not None:
            inp = TextInput(hint_text=hint, text=text_in, readonly=readonly, multiline=multiline, size_hint_y=None,
                            height=height,
                            background_color=(0.02, 0.05, 0.12, 1), foreground_color=(0.7, 1, 1, 1),
                            cursor_color=(0.3, 0.9, 1, 1))
            box.add_widget(inp)
        pop = Popup(title=title, content=box, size_hint=size, title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))

        def press(w, cb):
            if cb(inp.text if inp is not None else "") is not False:
                pop.dismiss()
        for label, cb in buttons:
            b = Button(text=label, size_hint_y=None, height=dp(48), background_normal="",
                       background_color=(0.05, 0.18, 0.35, 1), color=(0.6, 0.95, 1, 1))
            b.bind(on_release=lambda w, cb=cb: press(w, cb))
            box.add_widget(b)
        pop.open()

    def ask_reminder(self, text, back=None, prefill=""):
        def save(v, tomorrow):
            due = due_from(v, tomorrow)
            if due is None:
                self.popup("[ REMINDER ]", "Type a time like 07:30 or 6:15pm.")
                return False
            self.save_todo(text, due)
        self.dialog("[ TO-DO ]", "When should I remind you?\n[b]%s[/b]" % text,
                    [("REMIND ME  (next time it hits)", lambda v: save(v, False)),
                     ("REMIND TOMORROW", lambda v: save(v, True)),
                     ("NO REMINDER", lambda v: self.save_todo(text, None)),
                     ("BACK", lambda v: back() if back else None)],
                    hint="Time, e.g. 07:30 or 6:15pm", text_in=prefill, size=(0.92, 0.8))

    def save_todo(self, text, due):
        self.g.add_todo(text, due)
        self.refresh()
        when = "no reminder" if not due else "reminder " + time.strftime("%b %d, %H:%M", time.localtime(due))
        self.popup("[ TO-DO ]", "Saved: [b]%s[/b]\n(%s)\nFind it in the TASKS tab." % (text, when))

    def header(self, text):
        return Label(text="[b]%s[/b]" % text, markup=True, size_hint_y=None, height=dp(30), color=(1, 0.85, 0.3, 1))

    def task_row(self, text, on_tap, on_del, disabled=False, color=(0.05, 0.18, 0.35, 1), extra=None):
        row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(4))
        main = Button(text=text, background_normal="", background_color=color, color=(0.6, 0.95, 1, 1),
                      disabled=disabled, halign="center")
        main.bind(width=lambda w, v: setattr(w, "text_size", (v - 16, None)))
        main.bind(on_release=lambda w: on_tap())
        x = Button(text="X", size_hint_x=None, width=dp(48), background_normal="",
                   background_color=(0.4, 0.05, 0.08, 1), color=(1, 0.8, 0.8, 1))
        x.bind(on_release=lambda w: on_del())
        row.add_widget(main)
        if extra:
            ex = Button(text=extra[0], size_hint_x=None, width=dp(66), background_normal="",
                        background_color=(0.1, 0.3, 0.5, 1), color=(0.6, 0.95, 1, 1))
            ex.bind(on_release=lambda w: extra[1]())
            row.add_widget(ex)
        row.add_widget(x)
        return row

    def build_tasks(self):
        box = self.screen("tasks").ids.task_box
        box.clear_widgets()
        d, now = self.g.d, time.time()
        box.add_widget(self.mkbtn("OPEN JOURNAL BOOK", lambda w: self.open_journal()))
        box.add_widget(self.mkbtn("OPEN TOMORROW PLANNER", lambda w: self.open_planner()))
        box.add_widget(self.header("ROUTINE  (tap = log it, once a day)"))
        for r in d["routines"]:
            done = self.g.routine_done_today(r)
            box.add_widget(self.task_row(("[X]  " if done else "[  ]  ") + r["text"],
                                         lambda r=r: self.tap_routine(r),
                                         lambda r=r: (self.g.remove_routine(r["id"]), self.refresh()),
                                         disabled=done, color=(0.05, 0.3, 0.2, 1) if done else (0.05, 0.18, 0.35, 1)))
        box.add_widget(self.mkbtn("+ ADD ROUTINE", lambda w: self.dialog(
            "[ ROUTINE ]", "Something you do every day.\nIt logs with one tap.",
            [("ADD", self.save_routine), ("CANCEL", lambda v: None)], hint="e.g. Meditate, Brush teeth")))
        box.add_widget(self.header("TO-DO  (tap when you have done it)"))
        for t in d["todos"]:
            due = t.get("due")
            when = "No reminder" if not due else "Remind: " + time.strftime("%b %d, %H:%M", time.localtime(due))
            late = bool(due) and due <= now
            box.add_widget(self.task_row("%s\n%s" % (t["text"], when), lambda t=t: self.tap_todo(t),
                                         lambda t=t: (self.g.remove_todo(t["id"]), self.refresh()),
                                         color=(0.4, 0.1, 0.12, 1) if late else (0.05, 0.18, 0.35, 1)))
        box.add_widget(self.mkbtn("+ ADD TO-DO", lambda w: self.dialog(
            "[ TO-DO ]", "What do you need to do?",
            [("NEXT", self.todo_next), ("CANCEL", lambda v: None)], hint="e.g. Run 5 km")))
        self.build_quits(box)

    def go(self, name):
        self.root_widget.ids.sm.current = name

    def build_quits(self, box):
        box.add_widget(self.header("QUIT TRACKER  (days clean)"))
        now = time.time()
        for q in self.g.d["quits"]:
            best = max(q.get("best", 0), now - q["since"])
            box.add_widget(self.task_row("%s\n%s clean   (best %s)" % (q["name"], days_text(now - q["since"]), days_text(best)),
                                         lambda q=q: self.dialog("[ QUIT TRACKER ]", "Did you slip on [b]%s[/b]?\nThis restarts the counter." % q["name"],
                                                                 [("YES, I SLIPPED", lambda v: (self.g.slip_quit(q["id"]), self.refresh())),
                                                                  ("BACK", lambda v: None)], size=(0.9, 0.4)),
                                         lambda q=q: (self.g.remove_quit(q["id"]), self.refresh()),
                                         color=(0.2, 0.12, 0.4, 1)))
        box.add_widget(self.mkbtn("+ ADD SOMETHING TO QUIT", lambda w: self.dialog(
            "[ QUIT TRACKER ]", "What do you want to quit?\nLogging a bad habit with this name restarts it.",
            [("ADD", self.save_quit), ("BACK", lambda v: None)], hint="e.g. TikTok")))

    def save_quit(self, v):
        if not v.strip():
            return False
        self.g.add_quit(v)
        self.refresh()

    def build_log(self):
        box = self.screen("log").ids.log_box
        box.clear_widgets()
        if not self.g.d["log"]:
            box.add_widget(Label(text="No habits logged yet.", size_hint_y=None, height=dp(50), color=(0.6, 0.95, 1, 1)))
        for i, e in enumerate(self.g.d["log"][:60]):
            box.add_widget(self.mkbtn(log_line(e), lambda w, i=i: self.log_entry_menu(i)))

    def log_entry_menu(self, i):
        e = self.g.d["log"][i]
        self.dialog("[ LOG ]", log_line(e), [("UNDO  (reverse the EXP)", lambda v: self.undo_entry(i)),
                                              ("RENAME", lambda v: self.rename_entry(i)), ("BACK", lambda v: None)], size=(0.92, 0.6))

    def undo_entry(self, i):
        msg = self.g.undo_log(i)
        self.refresh()
        self.popup("[ LOG ]", msg)

    def rename_entry(self, i):
        e = self.g.d["log"][i]
        if isinstance(e, str):
            self.popup("[ LOG ]", "Entries from older versions can only be removed.")
            return

        def save(v):
            if not v.strip():
                return False
            self.g.rename_log(i, v)
            self.refresh()
        self.dialog("[ LOG ]", "Rename this entry (EXP stays the same).", [("SAVE", save), ("BACK", lambda v: self.log_entry_menu(i))],
                    hint="", text_in=e["text"])

    def add_reward_dialog(self):
        def save(v):
            name, sep, cost = v.rpartition("|")
            if not sep or not name.strip() or not cost.strip().isdigit() or int(cost) <= 0:
                self.popup("[ REWARD ]", "Type it like:  Movie night | 300")
                return False
            self.g.add_reward(name, int(cost))
            self.refresh()
        self.dialog("[ REWARD ]", "Add a real-life reward and its price in gold.\nExample:  1 hour of gaming | 200",
                    [("ADD", save), ("BACK", lambda v: None)], hint="Name | price", size=(0.92, 0.55))

    def confirm_reward(self, r):
        self.dialog("[ REWARD ]", "Spend [b]%d gold[/b] on:\n[b]%s[/b] ?" % (r["cost"], r["name"]),
                    [("YES, CLAIM IT", lambda v: self.claim_reward(r)), ("BACK", lambda v: None)], size=(0.9, 0.4))

    def claim_reward(self, r):
        msg = self.g.redeem_reward(r["id"])
        self.refresh()
        self.popup("[ REWARD ]", msg)

    def open_history(self):
        self.build_history()
        self.go("history")

    def build_history(self):
        import datetime
        box = self.screen("history").ids.hist_box
        box.clear_widgets()
        d, hist, c = self.g.d, self.g.d["history"], self.g.d["counts"]
        light = (0.6, 0.95, 1, 1)
        box.add_widget(Label(text="Habits logged: %d     Quests done: %d\nStreak: %d days (best %d)     Deaths: %d     Rewards claimed: %d" % (
            c["habits"], c["quests"], d["streak"], d["best_streak"], c["deaths"], len(d["redeemed"])),
            size_hint_y=None, height=dp(56), color=light))
        today = datetime.date.today()
        days = [today - datetime.timedelta(days=i) for i in range(13, -1, -1)]
        vals = [hist.get(x.isoformat(), {}).get("exp", 0) for x in days]
        top = float(max(vals + [1]))
        box.add_widget(self.header("EXP PER DAY  (last 14 days)"))
        for x, v in zip(days, vals):
            row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
            row.add_widget(Label(text=x.strftime("%b %d"), size_hint_x=None, width=dp(64), color=light))
            row.add_widget(Factory.Bar(value=v / top))
            row.add_widget(Label(text=str(v), size_hint_x=None, width=dp(48), color=light))
            box.add_widget(row)
        week = {k: 0 for k in CATS}
        for i in range(7):
            for k, v in hist.get((today - datetime.timedelta(days=i)).isoformat(), {}).get("attrs", {}).items():
                if k in week:
                    week[k] += v
        box.add_widget(self.header("ATTRIBUTE GROWTH  (last 7 days)"))
        box.add_widget(Label(text="Physical +%d     Mental +%d     Spiritual +%d" % (week["Physical"], week["Mental"], week["Spiritual"]),
                             size_hint_y=None, height=dp(32), color=light))
        box.add_widget(self.header("CALENDAR  (green = every quest done)"))
        first = today - datetime.timedelta(days=27)
        grid = GridLayout(cols=7, size_hint_y=None, height=dp(40) * 6, spacing=dp(2))
        for n in "MTWTFSS":
            grid.add_widget(Label(text=n, size_hint_y=None, height=dp(24), color=light))
        for _ in range(first.weekday()):
            grid.add_widget(Label(text=""))
        for i in range(28):
            day = first + datetime.timedelta(days=i)
            h = hist.get(day.isoformat())
            bg = (0.1, 0.1, 0.18, 1)
            if h and h.get("perfect"):
                bg = (0.1, 0.55, 0.3, 1)
            elif h and (h.get("habits") or h.get("quests")):
                bg = (0.15, 0.3, 0.65, 1)
            grid.add_widget(Factory.Cell(text=str(day.day), bg=bg))
        box.add_widget(grid)

    def export_backup(self):
        text = self.g.export_text()

        def copy(v):
            Clipboard.copy(text)
            self.popup("[ BACKUP ]", "Copied! Paste it into a notes app or send it to yourself.")
            return False

        def share(v):
            try:
                notifier.share_text(text)
            except Exception as e:
                self.popup("[ BACKUP ]", "Could not open the share menu: %s\nUse COPY instead." % e)
            return False
        self.dialog("[ BACKUP ]", "Your whole save as text (%d characters).\nKeep it somewhere safe." % len(text),
                    [("COPY", copy), ("SHARE / SAVE TO...", share), ("CLOSE", lambda v: None)],
                    hint="", text_in=text, readonly=True, multiline=True, height=dp(120), size=(0.95, 0.75))

    def restore_backup(self):
        def go(v):
            if not v.strip():
                return False
            self.dialog("[ RESTORE ]", "This replaces ALL current progress with the backup.\nContinue?",
                        [("YES, RESTORE", lambda _: self.do_restore(v)), ("BACK", lambda _: self.restore_backup())], size=(0.9, 0.45))
        self.dialog("[ RESTORE ]", "Paste your backup text below.", [("RESTORE", go), ("BACK", lambda v: None)],
                    hint="SYSTEMSAVE1:...", multiline=True, height=dp(200), size=(0.95, 0.8))

    def do_restore(self, text):
        try:
            self.g.import_text(text)
        except ValueError as e:
            self.popup("[ RESTORE ]", str(e))
            return
        self.refresh()
        self.popup("[ RESTORE ]", "Backup restored.")

    def toggle_scaling(self):
        self.g.d["scale_quests"] = not self.g.d.get("scale_quests", True)
        self.g.save()
        self.popup("[ ADMIN ]", "Quest scaling with rank is now %s.\n(Applies to quests issued from the next day.)" %
                   ("ON" if self.g.d["scale_quests"] else "OFF"))

    def open_planner(self):
        self.g.clean_plans()
        self.refresh()
        self.go("planner")

    def add_plan_dialog(self, again=False):
        def save(v):
            if not v.strip():
                return False
            self.g.add_plan(tomorrow_str(), v)
            self.refresh()
            self.add_plan_dialog(again=True)  # stay in add mode so you can plan several things quickly
        intro = "Added! Add another, or press BACK when you are done." if again else "What will you do tomorrow?"
        self.dialog("[ PLANNER ]", intro + "\nStart with a time if you like:\n7:30 Gym    or    6pm Study",
                    [("ADD", save), ("BACK", lambda v: None)], hint="e.g. 7:30 Gym", size=(0.92, 0.6))

    def build_planner(self):
        box = self.screen("planner").ids.planner_box
        box.clear_widgets()
        for label, date in (("TOMORROW", tomorrow_str()), ("TODAY", today_str())):
            box.add_widget(self.header("%s  (%s)" % (label, time.strftime("%b %d", time.strptime(date, "%Y-%m-%d")))))
            items = self.g.plans_for(date)
            carried = self.g.carried_plans() if date == today_str() else []
            if not items and not carried:
                box.add_widget(Label(text="Nothing planned.", size_hint_y=None, height=dp(36), color=(0.5, 0.7, 0.8, 1)))
            for p in carried + items:
                text = ("[X]  " if p["done"] else "[  ]  ") + ("(carried)  " if p in carried else "") + (p["time"] + "   " if p["time"] else "") + p["text"]
                box.add_widget(self.task_row(text, lambda p=p: (self.g.toggle_plan(p["id"]), self.refresh()),
                                             lambda p=p: (self.g.remove_plan(p["id"]), self.refresh()),
                                             extra=("TO-DO", lambda p=p: self.ask_reminder(p["text"], prefill=p["time"])),
                                             color=(0.05, 0.3, 0.2, 1) if p["done"] else (0.05, 0.18, 0.35, 1)))

    def open_journal(self):
        self.refresh()
        self.go("journal")

    def write_journal(self):
        def save(v):
            if not v.strip():
                return False
            first = self.g.add_journal(v)
            self.refresh()
            if first:
                self._after_log = None
                self.process_habit("Finished journal entry")  # also shows up in the LOG tab
            else:
                self.popup("[ JOURNAL ]", "Entry saved.\n(Journal EXP is given once per day.)")
        self.dialog("[ JOURNAL ]", "Write your entry.", [("SAVE", save), ("BACK", lambda v: None)],
                    hint="Today I...", multiline=True, height=dp(220), size=(0.95, 0.85))

    def build_journal(self):
        box = self.screen("journal").ids.journal_box
        box.clear_widgets()
        entries = sorted(self.g.d["journal"], key=lambda e: e["ts"], reverse=True)
        if not entries:
            box.add_widget(Label(text="No entries yet.", size_hint_y=None, height=dp(60), color=(0.6, 0.95, 1, 1)))
        for e in entries:
            lines = e["text"].strip().splitlines() or [""]
            label = "%s\n%s" % (time.strftime("%b %d, %Y  %H:%M", time.localtime(e["ts"])), lines[0][:60])
            box.add_widget(self.mkbtn(label, lambda w, e=e: self.read_journal(e)))

    def read_journal(self, e):
        self.dialog("[ JOURNAL ]", time.strftime("%b %d, %Y  %H:%M", time.localtime(e["ts"])),
                    [("CLOSE", lambda v: None), ("DELETE", lambda v: self.delete_journal(e))],
                    hint="", text_in=e["text"], readonly=True, multiline=True, height=dp(240), size=(0.95, 0.85))

    def delete_journal(self, e):
        self.dialog("[ JOURNAL ]", "Delete this entry for good?",
                    [("YES, DELETE", lambda v: (self.g.remove_journal(e["id"]), self.refresh())),
                     ("BACK", lambda v: self.read_journal(e))], size=(0.9, 0.4))

    def save_routine(self, v):
        if not v.strip():
            return False
        self.g.add_routine(v)
        self.refresh()

    def todo_next(self, v):
        if not v.strip():
            return False
        self.ask_reminder(v.strip())

    def tap_routine(self, r):
        self.dialog("[ ROUTINE ]", "Log this routine as done?\n[b]%s[/b]" % r["text"],
                    [("YES, LOG IT", lambda v: self.do_routine(r)), ("BACK", lambda v: None)], size=(0.9, 0.4))

    def do_routine(self, r):
        self._after_log = lambda: self.g.mark_routine(r["id"])
        self.process_habit(r["text"], back=lambda: self.tap_routine(r))

    def tap_todo(self, t):
        self.dialog("[ TO-DO ]", "Mark as done and log it?\n[b]%s[/b]" % t["text"],
                    [("YES, LOG IT", lambda v: self.do_todo(t)), ("BACK", lambda v: None)], size=(0.9, 0.4))

    def do_todo(self, t):
        self._after_log = lambda: self.g.remove_todo(t["id"])
        self.process_habit(t["text"], back=lambda: self.tap_todo(t))

    # ---------- GPS run tracker ----------
    def open_run(self):
        from engine import RunTracker
        self.tracker = RunTracker()
        self.running = False
        self.gps_fixes, self.gps_acc, self.gps_status = 0, None, ""
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        self.run_label = Label(text="0.00 km\n00:00\nGo outside with open sky,\nthen press START", font_size="18sp", halign="center",
                               color=(0.7, 1, 1, 1))
        box.add_widget(self.run_label)
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        self.run_pop = Popup(title="[ RUN TRACKER ]", content=box, size_hint=(0.92, 0.6), auto_dismiss=False,
                             title_color=(0.25, 0.85, 1, 1), separator_color=(0.25, 0.85, 1, 1),
                             background_color=(0.02, 0.05, 0.12, 1))
        for text, cb in (("START", self.start_run), ("FINISH", self.finish_run), ("CANCEL", self.cancel_run)):
            b = Button(text=text, background_normal="", background_color=(0.05, 0.18, 0.35, 1), color=(0.6, 0.95, 1, 1))
            b.bind(on_release=cb)
            row.add_widget(b)
        box.add_widget(row)
        self.run_pop.open()

    def start_run(self, *a):
        if self.running:
            return
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION"],
                                lambda perms, grants: Clock.schedule_once(
                                    lambda dt: self._start_gps() if all(grants) else self.popup(
                                        "[ GPS ]", "Location permission is needed to track your run."), 0))
        except ImportError:  # not on Android
            self._start_gps()

    def _start_gps(self):
        try:
            from plyer import gps
            gps.configure(on_location=self.on_gps, on_status=self.on_gps_status)
            gps.start(minTime=1000, minDistance=0)
        except Exception as e:
            self.popup("[ GPS ]", "GPS is not available here.\n%s" % e)
            return
        self.running = True
        self.run_t0 = time.time()
        self.keep_awake(True)
        Clock.schedule_interval(self.run_tick, 1)

    def on_gps(self, **kw):  # called from the GPS thread: only update numbers here
        lat, lon = kw.get("lat"), kw.get("lon")
        if lat is not None and lon is not None:
            self.gps_fixes += 1
            self.gps_acc = kw.get("accuracy")
            self.tracker.update(float(lat), float(lon), kw.get("accuracy"))

    def on_gps_status(self, *args, **kw):
        if len(args) >= 2:
            self.gps_status = "%s: %s" % (args[0], args[1])

    def run_tick(self, dt):
        if not self.running:
            return False
        s = int(time.time() - self.run_t0)
        acc = "-" if self.gps_acc is None else "%d m" % self.gps_acc
        if self.tracker.last:
            note = "Tracking"
        elif self.gps_fixes:
            note = "Signal too weak - move to open sky"
        else:
            note = "Waiting for GPS (can take 1 minute)"
        self.run_label.text = "%.2f km\n%02d:%02d\n%s\nFixes: %d   Accuracy: %s\n%s" % (
            self.tracker.meters / 1000.0, s // 60, s % 60, note, self.gps_fixes, acc, self.gps_status)

    def stop_gps(self):
        if self.running:
            try:
                from plyer import gps
                gps.stop()
            except Exception:
                pass
        self.running = False
        Clock.unschedule(self.run_tick)
        self.keep_awake(False)

    def finish_run(self, *a):
        km = self.tracker.meters / 1000.0
        self.stop_gps()
        self.run_pop.dismiss()
        if km < 0.01:
            self.popup("[ RUN ]", "No distance was recorded.")
            return
        i, msgs = self.g.add_run_km(km)
        self.refresh()
        if i is None:
            self.popup("[ RUN ]", "Tracked %.2f km, but there is no open quest measured in km." % km)
        else:
            self.popup("[ RUN ]", "Added %.2f km to %s\n%s" % (km, self.g.d["quests"][i]["name"], "\n".join(msgs)))

    def cancel_run(self, *a):
        self.stop_gps()
        self.run_pop.dismiss()

    def keep_awake(self, on):
        try:
            from android.runnable import run_on_ui_thread
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            flag = autoclass("android.view.WindowManager$LayoutParams").FLAG_KEEP_SCREEN_ON

            @run_on_ui_thread
            def go():
                w = activity.getWindow()
                w.addFlags(flag) if on else w.clearFlags(flag)
            go()
        except Exception:
            pass

    # ---------- admin ----------
    def open_admin(self):
        if self.admin_unlocked:
            self.load_admin()
            return
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        pin = TextInput(hint_text="Admin PIN", password=True, multiline=False, size_hint_y=None, height=dp(44),
                        background_color=(0.02, 0.05, 0.12, 1), foreground_color=(0.7, 1, 1, 1),
                        cursor_color=(0.3, 0.9, 1, 1))
        ok = Button(text="UNLOCK", size_hint_y=None, height=dp(44), background_normal="",
                    background_color=(0.05, 0.18, 0.35, 1), color=(0.6, 0.95, 1, 1))
        box.add_widget(pin)
        box.add_widget(ok)
        pop = Popup(title="[ ADMIN ACCESS ]", content=box, size_hint=(0.85, 0.35),
                    title_color=(0.25, 0.85, 1, 1), separator_color=(0.25, 0.85, 1, 1),
                    background_color=(0.02, 0.05, 0.12, 1))

        def check(*a):
            if pin.text == self.g.d["pin"]:
                self.admin_unlocked = True
                pop.dismiss()
                self.load_admin()
            else:
                pin.text = ""
                pin.hint_text = "Wrong PIN"
        ok.bind(on_release=check)
        pin.bind(on_text_validate=check)
        pop.open()

    def load_admin(self):
        ids = self.screen("admin").ids
        ids.habits_in.text = habits_to_text(self.g.d["habits"])
        ids.quests_in.text = quests_to_text(self.g.d["templates"])
        ids.name_in.text = self.g.d["name"]
        self.root_widget.ids.sm.current = "admin"

    def lock_admin(self):
        self.admin_unlocked = False
        self.root_widget.ids.sm.current = "status"

    def admin_exp(self, txt, sign):
        if not txt.strip().isdigit():
            return
        n = int(txt)
        msgs = self.g.add_exp(n) if sign > 0 else (self.g.lose_exp(n) or [])
        self.g.save()
        self.refresh()
        if msgs:
            self.popup("[ SYSTEM ]", "\n".join(msgs))

    def admin_level(self, txt):
        if txt.strip().isdigit():
            self.g.set_level(int(txt))
            self.g.check_titles()
            self.g.save()
            self.refresh()

    def admin_add_quest(self, name, target, unit, reward, penalty, punish, category=""):
        name = name.strip()
        if not name:
            self.popup("[ ADMIN ]", "Enter a quest name first.")
            return
        try:
            t, r, p = float(target or 1), int(reward or 30), int(penalty or 20)
        except ValueError:
            self.popup("[ ADMIN ]", "Target, reward and penalty must be numbers.")
            return
        self.g.add_template(name, t, unit.strip(), r, p, punish.strip() or "Penalty Zone: 30 push-ups", category)
        ids = self.screen("admin").ids
        for k in ("q_name", "q_target", "q_unit", "q_reward", "q_penalty", "q_punish", "q_cat"):
            ids[k].text = ""
        ids.quests_in.text = quests_to_text(self.g.d["templates"])
        self.refresh()
        self.popup("[ ADMIN ]", "Quest added: %s\nIt appears in today's quests now and in every new day." % name)

    def admin_gold(self, txt):
        if txt.strip().isdigit():
            self.g.d["gold"] += int(txt)
            self.g.save()
            self.refresh()

    def admin_heal(self):
        self.g.heal(10 ** 6)
        self.g.save()
        self.refresh()

    def admin_save(self, habits, quests):
        h, q = text_to_habits(habits), text_to_quests(quests)
        if h:
            self.g.d["habits"] = h
        if q:
            self.g.d["templates"] = q
        self.g.save()
        self.popup("[ ADMIN ]", "Rules and quest templates saved.\nNew quests apply next cycle (or re-issue now).")

    def admin_reissue(self):
        import time
        self.g.new_cycle(time.time())
        self.g.save()
        self.refresh()

    def admin_profile(self, name, pin):
        if name.strip():
            self.g.d["name"] = name.strip()
        if pin.strip():
            self.g.d["pin"] = pin.strip()
        self.g.save()
        self.refresh()
        self.popup("[ ADMIN ]", "Profile saved.")

    def admin_reset(self):
        pin, name = self.g.d["pin"], self.g.d["name"]
        self.g.d = self.g.default()
        self.g.d["pin"], self.g.d["name"] = pin, name
        self.g.new_cycle(self.g.d["cycle_start"])
        self.g.save()
        self.refresh()
        self.popup("[ ADMIN ]", "System reset. Level 1, Rank E.")


def run():
    SoloSystemApp().run()


if __name__ == "__main__":
    run()
