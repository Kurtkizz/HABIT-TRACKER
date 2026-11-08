import os
import time
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from engine import Game, CATS, norm_cat, SHOP, TITLES, hp_max, rank_for, exp_needed, habits_to_text, text_to_habits, quests_to_text, text_to_quests

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
            height: dp(40)

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
        Panel:
            ScrollView:
                L:
                    text: app.log_text
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
                    halign: 'left'
                    valign: 'top'
                    padding: dp(8), dp(8)

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
            text: 'STATUS'
            on_release: sm.current = 'status'
        SB:
            text: 'LOG'
            on_release: sm.current = 'log'
        SB:
            text: 'QUESTS'
            on_release: sm.current = 'quests'
        SB:
            text: 'SHOP'
            on_release: sm.current = 'shop'
        SB:
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

    admin_unlocked = False

    def build(self):
        self.title = "The System"
        self.g = Game(os.path.join(self.user_data_dir, "system.json"))
        self.root_widget = Builder.load_string(KV)
        Clock.schedule_once(lambda dt: self.check_cycle(), 0.5)
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
            from plyer import notification
            notification.notify(title=title, message=text, app_name="The System", timeout=10)
        except Exception:
            pass

    # ---------- helpers ----------
    def popup(self, title, text, color=(0.25, 0.85, 1, 1)):
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
        self.level_text = "LEVEL  %d" % d["level"]
        self.rank_text = "RANK  %s" % rank_for(d["level"])
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
        self.extra_text = "Streak: %d days   |   Pending punishments: %d\nBuild 1.2" % (d["streak"], len(d["punishments"]))
        self.log_text = "\n".join(d["log"]) or "No habits logged yet."
        self.build_quests()
        self.build_shop()

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
            self.popup("[ WARNING ]", "\n\n".join(msgs), (1, 0.3, 0.3, 1))
        if self.g.arrived:
            self.g.arrived = False
            self.notify("QUEST ARRIVED", "Daily quests issued. You have 24 hours. Failure has consequences.")
            if not msgs:
                self.popup("[ QUEST ARRIVED ]", "Daily quests issued.\nComplete them within 24 hours\nor face the Penalty Zone.")
        d = self.g.d
        if 0 < self.g.remaining() < 7200 and self.g.warned != d["cycle_start"] and any(not q["done"] for q in d["quests"]):
            self.g.warned = d["cycle_start"]
            self.notify("WARNING", "Less than 2 hours left to finish your daily quests!")

    # ---------- player actions ----------
    def log_habit(self, text):
        text = text.strip()
        if not text:
            return
        h = self.g.detect(text)
        if h is None:
            self.ask_classify(text)
            return
        cat = norm_cat(h.get("stat", ""))
        if h["value"] > 0 and not cat:
            self.ask_category(text, lambda c: self._log_known(h, text, c))
            return
        self.show_result(self.g.apply_habit(text, h["value"], cat))

    def show_result(self, msgs):
        self.result_text = msgs[0]
        self.refresh()
        if len(msgs) > 1:
            self.popup("[ SYSTEM ]", "\n".join(msgs[1:]))

    def ask_classify(self, text):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Unknown habit. Classify it:\n[b]%s[/b]" % text, markup=True,
                             color=(0.7, 1, 1, 1)))
        pop = Popup(title="[ SYSTEM ]", content=box, size_hint=(0.9, 0.75), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))
        for label, val in (("EXCELLENT  +40", 40), ("GOOD  +20", 20), ("NEUTRAL  0", 0), ("BAD  -10", -10), ("SEVERE  -40", -40)):
            b = Button(text=label, background_normal="", background_color=(0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), size_hint_y=None, height=dp(44))
            b.bind(on_release=lambda w, v=val: self.classified(pop, text, v))
            box.add_widget(b)
        pop.open()

    def classified(self, pop, text, val):
        pop.dismiss()
        if val > 0:
            self.ask_category(text, lambda c: self._log_new(text, val, c))
        else:
            self._log_new(text, val, "")

    def _log_new(self, text, val, cat):
        self.g.add_rule(text, val, cat)
        self.show_result(self.g.apply_habit(text, val, cat))

    def _log_known(self, h, text, cat):
        h["stat"] = cat
        self.show_result(self.g.apply_habit(text, h["value"], cat))

    def ask_category(self, text, callback):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Which kind of habit is this?\n[b]%s[/b]" % text, markup=True, color=(0.7, 1, 1, 1)))
        pop = Popup(title="[ SYSTEM ]", content=box, size_hint=(0.9, 0.6), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))
        for cat in CATS:
            b = Button(text=cat.upper(), background_normal="", background_color=(0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), size_hint_y=None, height=dp(48))
            b.bind(on_release=lambda w, c=cat: (pop.dismiss(), callback(c)))
            box.add_widget(b)
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


if __name__ == "__main__":
    SoloSystemApp().run()
