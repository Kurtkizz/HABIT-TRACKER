import os
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

from engine import Game, SHOP, TITLES, hp_max, rank_for, exp_needed, habits_to_text, text_to_habits, quests_to_text, text_to_quests

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
                halign: 'left'
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
                text: 'Habit rules  (keywords, comma separated | EXP value | STAT)'
                size_hint_y: None
                height: dp(24)
            TI:
                id: habits_in
                size_hint_y: None
                height: dp(260)
            L:
                text: 'Daily quests  (name | reward EXP | penalty EXP | punishment)'
                size_hint_y: None
                height: dp(24)
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
            TI:
                id: name_in
                hint_text: 'Player name'
                multiline: False
                size_hint_y: None
                height: dp(44)
            TI:
                id: pin_in
                hint_text: 'New admin PIN'
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
        s = d["stats"]
        self.stats_text = "\n".join("%-6s  %d" % (k, s[k]) for k in s)
        self.extra_text = "Streak: %d days   |   Pending punishments: %d" % (d["streak"], len(d["punishments"]))
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
            b = Button(text="%s  %s   (+%d EXP | fail: -%d EXP)" % (mark, q["name"], q["reward"], q["penalty"]),
                       size_hint_y=None, height=dp(60), background_normal="", disabled=q["done"],
                       background_color=(0.05, 0.3, 0.2, 1) if q["done"] else (0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), halign="center")
            b.bind(width=lambda w, v: setattr(w, "text_size", (v - 16, None)))
            b.bind(on_release=lambda w, idx=i: self.finish_quest(idx))
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
        self.show_result(self.g.apply_habit(text, h["value"], h.get("stat", "")))

    def show_result(self, msgs):
        self.result_text = msgs[0]
        self.refresh()
        if len(msgs) > 1:
            self.popup("[ SYSTEM ]", "\n".join(msgs[1:]))

    def ask_classify(self, text):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Unknown habit. Classify it:\n[b]%s[/b]" % text, markup=True,
                             color=(0.7, 1, 1, 1)))
        pop = Popup(title="[ SYSTEM ]", content=box, size_hint=(0.9, 0.6), title_color=(0.25, 0.85, 1, 1),
                    separator_color=(0.25, 0.85, 1, 1), background_color=(0.02, 0.05, 0.12, 1))
        for label, val in (("GOOD  +20", 20), ("NEUTRAL  0", 0), ("BAD  -10", -10), ("SEVERE  -40", -40)):
            b = Button(text=label, background_normal="", background_color=(0.05, 0.18, 0.35, 1),
                       color=(0.6, 0.95, 1, 1), size_hint_y=None, height=dp(44))
            b.bind(on_release=lambda w, v=val: self.classified(pop, text, v))
            box.add_widget(b)
        pop.open()

    def classified(self, pop, text, val):
        pop.dismiss()
        self.g.add_rule(text, val)
        self.show_result(self.g.apply_habit(text, val))

    def finish_quest(self, i):
        msgs = self.g.complete_quest(i)
        self.refresh()
        if msgs:
            self.popup("[ QUEST ]", "\n".join(msgs))

    def finish_punishment(self, i):
        self.g.complete_punishment(i)
        self.refresh()

    # ---------- admin ----------
    def open_admin(self):
        if self.admin_unlocked:
            self.load_admin()
            return
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        pin = TextInput(hint_text="Admin PIN", password=True, multiline=False, size_hint_y=None, height=dp(44))
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
