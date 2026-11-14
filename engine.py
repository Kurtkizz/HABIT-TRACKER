import base64, datetime, json, math, os, re, time, zlib

DAY = 86400
WARN_HOURS = (3, 1)  # quest warnings: 3 hours and 1 hour before the 24h run out
RANKS = [(1, "E"), (10, "D"), (20, "C"), (35, "B"), (50, "A"), (70, "S"),
         (90, "SS"), (120, "SSS"), (160, "Transcendent"), (200, "Absolute Apex")]
STATS = ["STR", "AGI", "VIT", "INT", "SENSE"]  # legacy, kept so old saves still load
CATS = ["Physical", "Mental", "Spiritual"]
_LEGACY = {"STR": "Physical", "AGI": "Physical", "VIT": "Physical", "INT": "Mental", "SENSE": "Spiritual",
           "P": "Physical", "M": "Mental", "S": "Spiritual"}


def today_str():
    return datetime.date.today().isoformat()


def tomorrow_str():
    return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


def parse_plan(text):
    """'7:30 Gym', '6pm Study', '6:15pm Read' -> ('07:30', 'Gym'). No time -> ('', text)."""
    m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*(.+)$", text, re.I)
    if not m:
        m = re.match(r"^\s*(\d{1,2}):(\d{2})()\s+(.+)$", text)
    if not m:
        return "", text.strip()
    h, mi, ap, rest = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower(), m.group(4).strip()
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59 or not rest:
        return "", text.strip()
    return "%02d:%02d" % (h, mi), rest


def hours_text(secs):
    secs = max(0, int(secs))
    return "%dh %02dm" % (secs // 3600, secs % 3600 // 60)


def due_from(text, tomorrow=False, now=None):
    """'7:30', '0730', '6:15pm' -> timestamp of the next time it happens (or tomorrow). None if invalid."""
    m = re.match(r"^\s*(\d{1,2})(?::?(\d{2}))?\s*(am|pm)?\s*$", (text or "").lower())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    now_dt = datetime.datetime.fromtimestamp(time.time() if now is None else now)
    due = now_dt.replace(hour=h, minute=mi, second=0, microsecond=0)
    if tomorrow:
        due += datetime.timedelta(days=1)
    elif due <= now_dt:
        due += datetime.timedelta(days=1)
    return due.timestamp()


def norm_cat(x):
    x = (x or "").strip()
    for c in CATS:
        if x.lower() in (c.lower(), c.lower() + " attributes"):
            return c
    return _LEGACY.get(x.upper(), "")


def guess_cat(name):
    n = name.lower()
    for words, cat in ((("push", "sit", "squat", "run", "walk", "jog", "gym", "workout", "exercise", "swim", "bike"), "Physical"),
                       (("read", "study", "learn", "code", "write", "practice"), "Mental"),
                       (("meditat", "pray", "journal", "gratitude", "breath"), "Spiritual")):
        if any(w in n for w in words):
            return cat
    return ""

# name, description, gold cost (items are used immediately on purchase)
SHOP = {
    "potion": ("Healing Potion", "Restore 50 HP", 100),
    "pardon": ("Penalty Pardon", "Clear one pending punishment", 150),
    "skip": ("Quest Skip Scroll", "Complete one open quest (no reward)", 200),
}

# name, how to unlock, condition
TITLES = [
    ("Weakest Hunter", "Where every Hunter begins", lambda d: True),
    ("Habit Forger", "Log 10 habits", lambda d: d["counts"]["habits"] >= 10),
    ("Quest Slayer", "Complete 25 quests", lambda d: d["counts"]["quests"] >= 25),
    ("Iron Will", "Reach a 7-day streak", lambda d: d["best_streak"] >= 7),
    ("Returned from Death", "Die once and come back", lambda d: d["counts"]["deaths"] >= 1),
    ("D-Rank Hunter", "Reach Level 10", lambda d: d["level"] >= 10),
    ("S-Rank Hunter", "Reach Level 70", lambda d: d["level"] >= 70),
    ("Shadow Monarch", "Reach Level 160", lambda d: d["level"] >= 160),
    ("Absolute Being", "Reach Level 200", lambda d: d["level"] >= 200),
    ("Body Forger", "Reach 25 Physical points", lambda d: d["attrs"]["Physical"] >= 25),
    ("Sage", "Reach 25 Mental points", lambda d: d["attrs"]["Mental"] >= 25),
    ("Spirit Walker", "Reach 25 Spiritual points", lambda d: d["attrs"]["Spiritual"] >= 25),
    ("Master", "Reach 100% in a mastery", lambda d: any(m["percent"] >= 100 for m in d.get("mastery", []))),
    ("Balanced Hunter", "Reach 15 points in all three attributes", lambda d: min(d["attrs"].values()) >= 15),
]


def hp_max(level):
    return 100 + 10 * level

# value > 0 = good (EXP gain), 0 = harmless/neutral, < 0 = bad (EXP loss)
DEFAULT_HABITS = [
    {"kw": ["workout", "exercise", "gym", "push-ups", "pushups", "sit-ups", "squats"], "value": 30, "stat": "Physical"},
    {"kw": ["run", "running", "jog", "jogging", "walk", "walking", "cardio"], "value": 25, "stat": "Physical"},
    {"kw": ["study", "studied", "read", "reading", "learn", "coding", "practice"], "value": 25, "stat": "Mental"},
    {"kw": ["meditate", "meditation", "journal", "journaling"], "value": 20, "stat": "Spiritual"},
    {"kw": ["drink water", "drank water", "healthy meal", "vegetables", "cold shower", "slept early", "woke up early"], "value": 15, "stat": "Physical"},
    {"kw": ["junk food", "fast food", "soda", "overslept", "snack"], "value": 0, "stat": ""},
    {"kw": ["scrolling", "doomscroll", "tiktok", "social media", "procrastinated", "wasted time", "skipped workout"], "value": -10, "stat": ""},
    {"kw": ["stayed up late", "all-nighter", "skipped class"], "value": -15, "stat": ""},
    {"kw": ["smoke", "smoked", "smoking", "vape", "vaped", "drunk", "alcohol"], "value": -40, "stat": ""},
]

DEFAULT_QUESTS = [
    {"name": "Push-ups", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 25 extra push-ups", "target": 50, "step": 5, "unit": "reps", "stat": "Physical"},
    {"name": "Sit-ups", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 25 extra sit-ups", "target": 50, "step": 5, "unit": "reps", "stat": "Physical"},
    {"name": "Squats", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 25 extra squats", "target": 50, "step": 5, "unit": "reps", "stat": "Physical"},
    {"name": "Run", "reward": 60, "penalty": 40, "punishment": "Penalty Zone: run 1 km extra", "target": 3, "step": 0.5, "unit": "km", "stat": "Physical"},
    {"name": "Read", "reward": 30, "penalty": 20, "punishment": "Penalty Zone: read 5 extra pages tomorrow", "target": 10, "unit": "pages", "stat": "Mental"},
    {"name": "Study", "reward": 35, "penalty": 25, "punishment": "Penalty Zone: 15 extra minutes of study tomorrow", "target": 30, "unit": "minutes", "stat": "Mental"},
    {"name": "Write a page", "reward": 25, "penalty": 15, "punishment": "Penalty Zone: write two pages tomorrow", "target": 1, "unit": "", "stat": "Mental"},
    {"name": "Meditate", "reward": 30, "penalty": 20, "punishment": "Penalty Zone: 10 extra minutes of silence tomorrow", "target": 10, "unit": "minutes", "stat": "Spiritual"},
    {"name": "Gratitude: list 3 things", "reward": 20, "penalty": 10, "punishment": "Penalty Zone: list 6 things tomorrow", "target": 3, "unit": "things", "stat": "Spiritual"},
    {"name": "Journal", "reward": 25, "penalty": 15, "punishment": "Penalty Zone: write two journal entries tomorrow", "target": 1, "unit": "", "stat": "Spiritual"},
]


def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two GPS points."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class RunTracker:
    """Turns raw GPS fixes into a distance, ignoring bad fixes and vehicle speeds."""
    MAX_SPEED = 7.0     # m/s (~25 km/h). Faster than this is a vehicle or a GPS jump: not counted
    MIN_STEP = 3.0      # meters. Smaller moves are GPS drift
    MAX_ACCURACY = 30.0  # meters. Fixes less accurate than this are ignored

    def __init__(self):
        self.meters = 0.0
        self.last = None
        self.start = None

    def update(self, lat, lon, accuracy=None, now=None):
        now = time.time() if now is None else now
        if self.start is None:
            self.start = now
        if accuracy is not None and accuracy > self.MAX_ACCURACY:
            return self.meters
        if self.last is None:
            self.last = (lat, lon, now)
            return self.meters
        d = haversine(self.last[0], self.last[1], lat, lon)
        if d < self.MIN_STEP:
            return self.meters
        speed = d / max(now - self.last[2], 0.001)
        self.last = (lat, lon, now)
        if speed <= self.MAX_SPEED:
            self.meters += d
        return self.meters


def rank_for(level):
    r = RANKS[0][1]
    for lv, name in RANKS:
        if level >= lv:
            r = name
    return r


def rank_index(level):
    idx = 0
    for i, (lv, _) in enumerate(RANKS):
        if level >= lv:
            idx = i
    return idx


def log_line(e):
    if isinstance(e, str):  # entries saved by older versions
        return e
    return "%s  %s\n%s" % (time.strftime("%m-%d %H:%M", time.localtime(e["ts"])), e["text"], e["res"])


def days_text(secs):
    secs = max(0, int(secs))
    return "%dd %02dh" % (secs // 86400, secs % 86400 // 3600)


MASTERY_RANKS = [(0, "Novice"), (10, "Apprentice"), (25, "Adept"), (50, "Expert"), (75, "Master"), (100, "Grandmaster")]


def mastery_rank(percent):
    r = MASTERY_RANKS[0][1]
    for lo, name in MASTERY_RANKS:
        if percent >= lo:
            r = name
    return r


def exp_needed(level):
    return 100 + 25 * level


def habits_to_text(habits):
    return "\n".join("%s | %d | %s" % (", ".join(h["kw"]), h["value"], norm_cat(h.get("stat", ""))) for h in habits)


def text_to_habits(text):
    out = []
    for line in text.splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) < 2 or not p[0]:
            continue
        try:
            val = int(p[1])
        except ValueError:
            continue
        stat = norm_cat(p[2]) if len(p) > 2 else ""
        out.append({"kw": [k.strip().lower() for k in p[0].split(",") if k.strip()], "value": val, "stat": stat})
    return out


def quests_to_text(qs):
    return "\n".join("%s | %d | %d | %s | %g | %s | %s | %g" % (q["name"], q["reward"], q["penalty"], q["punishment"],
                                                              q.get("target", 1), q.get("unit", ""), q.get("stat", ""),
                                                              q.get("step", 0)) for q in qs)


def text_to_quests(text):
    out = []
    for line in text.splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) < 4 or not p[0]:
            continue
        try:
            target = float(p[4]) if len(p) > 4 and p[4] else 1.0
            out.append({"name": p[0], "reward": int(p[1]), "penalty": int(p[2]), "punishment": p[3],
                        "target": max(target, 1.0), "unit": p[5] if len(p) > 5 else "",
                        "stat": norm_cat(p[6]) if len(p) > 6 and p[6] else guess_cat(p[0]),
                        "step": max(float(p[7]), 0.0) if len(p) > 7 and p[7] else 0})
        except ValueError:
            continue
    return out


class Game:
    def __init__(self, path, write=True):
        self.path = path
        self.d = {}
        self.arrived = False
        self.warned = 0
        self.load(save=write)

    def default(self):
        return {
            "name": "Player", "level": 1, "exp": 0, "pin": "0000", "streak": 0,
            "attrs": {c: 0 for c in CATS},
            "habits": [dict(h) for h in DEFAULT_HABITS],
            "templates": [dict(q) for q in DEFAULT_QUESTS],
            "cycle_start": time.time(), "quests": [], "punishments": [], "log": [],
            "hp": hp_max(1), "gold": 0, "title": "Weakest Hunter", "titles": ["Weakest Hunter"],
            "routines": [], "todos": [], "next_id": 1, "journal": [], "plans": [],
            "rank_cleared": 0, "quests_v2": True, "quests_v3": True, "mastery": [], "scale_quests": True, "history": {}, "rewards": [], "redeemed": [], "quits": [],
            "unseen_arrival": False, "warn": {"cycle": 0, "sent": []},
            "best_streak": 0, "counts": {"habits": 0, "quests": 0, "deaths": 0},
        }

    def load(self, save=True):
        base = self.default()
        try:
            with open(self.path) as f:
                self.d = json.load(f)
        except Exception:
            self.d = base
        if "attrs" not in self.d:  # migrate old STR/AGI/... saves
            s = self.d.get("stats", {})
            self.d["attrs"] = {"Physical": max(0, s.get("STR", 1) + s.get("AGI", 1) + s.get("VIT", 1) - 3),
                               "Mental": max(0, s.get("INT", 1) - 1), "Spiritual": max(0, s.get("SENSE", 1) - 1)}
        if "rank_cleared" not in self.d:  # old saves keep the rank they already had
            self.d["rank_cleared"] = rank_index(self.d.get("level", 1))
        for key in ("templates", "quests"):
            for q in self.d.get(key, []):
                if "stat" not in q:
                    q["stat"] = guess_cat(q.get("name", ""))
        if not self.d.get("quests_v2"):  # one-time: add the default Mental and Spiritual quests
            have = {t["name"].lower() for t in self.d.get("templates", [])}
            for q in DEFAULT_QUESTS:
                if q.get("stat") in ("Mental", "Spiritual") and q["name"].lower() not in have:
                    self.d.setdefault("templates", []).append(dict(q))
                    if self.d.get("quests"):
                        self.d["quests"].append(self.make_quest(q))
            self.d["quests_v2"] = True
        needs_v3 = not self.d.get("quests_v3")  # (checked before the defaults below fill the key in)
        for k, v in base.items():
            self.d.setdefault(k, v)
        if not self.d["quests"]:
            self.new_cycle(self.d["cycle_start"])
        if needs_v3:  # one-time: beginner push-ups / sit-ups / squats / run that grow every 10 levels
            fresh = {q["name"].lower(): q for q in DEFAULT_QUESTS}
            alias = {"100 push-ups": "push-ups", "100 sit-ups": "sit-ups", "100 squats": "squats", "run 10 km": "run"}
            for key in ("templates", "quests"):
                for q in self.d.get(key, []):
                    n = alias.get(q["name"].lower(), q["name"].lower())
                    if n in ("push-ups", "sit-ups", "squats", "run") and q.get("unit", "").lower() in ("reps", "km"):
                        src = fresh[n]
                        q.update(name=src["name"], step=src["step"], punishment=src["punishment"])
                        if key == "templates":
                            q["target"] = src["target"]
                        else:  # today's copy keeps its progress
                            q["target"] = self.make_quest(src)["target"]
                            q["progress"] = min(q.get("progress", 0), q["target"])
            self.d["quests_v3"] = True
        if save:
            self.save()

    def reload(self):
        self.load(save=False)

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.d, f, indent=2)
        os.replace(tmp, self.path)

    # ---- EXP / level ----
    def add_exp(self, amount):
        msgs = []
        self.d["exp"] += amount
        while self.d["exp"] >= exp_needed(self.d["level"]):
            self.d["exp"] -= exp_needed(self.d["level"])
            self.d["level"] += 1
            self.d["hp"] = hp_max(self.d["level"])
            msgs.append("LEVEL UP! You are now Level %d [Rank %s]" % (self.d["level"], self.current_rank()))
        if msgs and self.ensure_trial():
            msgs.append("PROMOTION TRIAL unlocked: finish it to reach Rank %s" % RANKS[self.d["rank_cleared"] + 1][1])
        return msgs

    def lose_exp(self, amount):
        self.d["exp"] = max(0, self.d["exp"] - amount)

    def lose_hp(self, n):
        self.d["hp"] -= n
        if self.d["hp"] <= 0:
            self.d["hp"] = hp_max(self.d["level"]) // 2
            self.d["exp"] = 0
            self.d["counts"]["deaths"] += 1
            return ["YOU HAVE DIED. EXP wiped. HP restored to half."]
        return []

    def heal(self, n):
        self.d["hp"] = min(hp_max(self.d["level"]), self.d["hp"] + n)

    def check_titles(self):
        msgs = []
        for name, desc, cond in TITLES:
            if name not in self.d["titles"] and cond(self.d):
                self.d["titles"].append(name)
                msgs.append("NEW TITLE UNLOCKED: [%s]" % name)
        return msgs

    def buy(self, key):
        name, desc, cost = SHOP[key]
        d = self.d
        if d["gold"] < cost:
            return "Not enough gold."
        if key == "potion":
            if d["hp"] >= hp_max(d["level"]):
                return "HP is already full."
            self.heal(50)
        elif key == "pardon":
            if not d["punishments"]:
                return "No punishment to pardon."
            d["punishments"].pop(0)
        elif key == "skip":
            for q in d["quests"]:
                if not q["done"]:
                    q["done"] = True
                    q["progress"] = q.get("target", 1)
                    break
            else:
                return "No open quest."
        d["gold"] -= cost
        self.save()
        return "Purchased: %s" % name

    def total_exp(self):
        return sum(exp_needed(l) for l in range(1, self.d["level"])) + self.d["exp"]

    def set_total_exp(self, total):
        total, lv = max(0, total), 1
        while total >= exp_needed(lv):
            total -= exp_needed(lv)
            lv += 1
        self.d["level"], self.d["exp"] = lv, total

    def current_rank(self):
        return RANKS[min(rank_index(self.d["level"]), self.d.get("rank_cleared", 0))][1]

    def pending_trial_rank(self):
        i = self.d.get("rank_cleared", 0) + 1
        return RANKS[i][1] if i < len(RANKS) and rank_index(self.d["level"]) >= i else None

    def ensure_trial(self):
        """Reaching a new rank's level only counts once its Promotion Trial is done."""
        i = self.d.get("rank_cleared", 0) + 1
        if i >= len(RANKS) or rank_index(self.d["level"]) < i:
            return False
        if any(q.get("trial") for q in self.d["quests"]):
            return False
        self.d["quests"].append({
            "name": "Promotion Trial: Rank %s (any push-ups, sit-ups, squats)" % RANKS[i][1],
            "reward": 100 + 50 * i, "penalty": 40, "target": 100 + 50 * i, "unit": "reps", "stat": "Physical",
            "punishment": "Penalty Zone: the trial returns tomorrow, plus 30 extra squats",
            "trial": True, "rank_idx": i, "done": False, "progress": 0})
        return True

    def make_quest(self, t):
        """Today's copy of a quest template. A quest with a "step" grows by that much every 10 levels."""
        q = dict(t, done=False, progress=0)
        if self.d.get("scale_quests", True) and q.get("step") and q.get("target", 1) > 1:
            q["target"] = q["target"] + q["step"] * (self.d["level"] // 10)
        return q

    def set_level(self, level):
        self.d["level"] = max(1, level)
        self.d["exp"] = 0
        self.d["rank_cleared"] = rank_index(self.d["level"])  # admin override: no trial needed
        self.d["quests"] = [q for q in self.d["quests"] if not q.get("trial")]

    # ---- habits ----
    def detect(self, text):
        t = text.lower()
        best, best_len = None, 0
        for h in self.d["habits"]:
            for kw in h["kw"]:
                if len(kw) > best_len and re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", t):
                    best, best_len = h, len(kw)
        return best

    def apply_habit(self, text, value, stat=""):
        msgs = []
        before = (self.total_exp(), self.d["hp"], self.d["gold"], self.d["counts"]["deaths"])
        cat, pts = "", 0
        if value > 0:
            msgs += self.add_exp(value)
            self.d["gold"] += value // 2
            cat = norm_cat(stat)
            pts = 2 if value >= 40 else 1
            if cat:
                self.d["attrs"][cat] += pts
                res = "[GOOD] +%d EXP, %s +%d" % (value, cat, pts)
            else:
                res = "[GOOD] +%d EXP" % value
        elif value < 0:
            self.lose_exp(-value)
            msgs += self.lose_hp(-value // 2)
            res = "[BAD] %d EXP, -%d HP" % (value, -value // 2)
        else:
            res = "[NEUTRAL] No EXP"
        d_exp = self.total_exp() - before[0]
        entry = {"ts": time.time(), "text": text, "res": res, "d_exp": d_exp, "d_hp": self.d["hp"] - before[1],
                 "d_gold": self.d["gold"] - before[2], "cat": cat if (value > 0 and cat) else "",
                 "pts": pts if (value > 0 and cat) else 0, "locked": self.d["counts"]["deaths"] > before[3]}
        self.d["log"].insert(0, entry)
        del self.d["log"][100:]
        self.d["counts"]["habits"] += 1
        self.record(exp=max(0, d_exp), habits=1, attr=entry["cat"], pts=entry["pts"])
        if value < 0:  # a bad habit restarts any matching quit counter
            for qt in self.d["quits"]:
                if qt["name"].lower() in text.lower():
                    self.slip_quit(qt["id"], save=False)
        msgs += self.check_titles()
        self.save()
        return [res] + msgs

    def add_rule(self, text, value, stat=""):
        self.d["habits"].append({"kw": [text.lower().strip()], "value": value, "stat": norm_cat(stat)})

    # ---- daily quests ----
    def new_cycle(self, start):
        self.d["cycle_start"] = start
        self.d["quests"] = [self.make_quest(q) for q in self.d["templates"]]
        self.ensure_trial()
        self.arrived = True

    def complete_quest(self, i):
        q = self.d["quests"][i]
        if q["done"]:
            return []
        q["done"] = True
        q["progress"] = q.get("target", 1)
        msgs = ["Quest complete: %s  +%d EXP" % (q["name"], q["reward"])] + self.add_exp(q["reward"])
        self.d["gold"] += q["reward"] // 2
        cat = norm_cat(q.get("stat", ""))
        if cat:
            self.d["attrs"][cat] += 2
            msgs.append("%s +2" % cat)
        self.d["counts"]["quests"] += 1
        self.heal(5)
        self.record(exp=q["reward"], quests=1, attr=cat, pts=2 if cat else 0)
        if q.get("trial"):
            self.d["rank_cleared"] = max(self.d["rank_cleared"], q["rank_idx"])
            msgs.append("PROMOTION! You are now Rank %s" % RANKS[self.d["rank_cleared"]][1])
            if self.ensure_trial():
                msgs.append("Next Promotion Trial unlocked: Rank %s" % RANKS[self.d["rank_cleared"] + 1][1])
        msgs += self.check_titles()
        self.save()
        return msgs

    def add_progress(self, i, amount):
        q = self.d["quests"][i]
        if q["done"] or amount <= 0:
            return []
        target = q.get("target", 1)
        q["progress"] = min(target, q.get("progress", 0) + amount)
        if q["progress"] >= target:
            return self.complete_quest(i)
        self.save()
        return []

    def add_template(self, name, target, unit, reward, penalty, punishment, category=""):
        t = {"name": name, "reward": reward, "penalty": penalty, "punishment": punishment,
             "target": max(target, 1.0), "unit": unit,
             "stat": norm_cat(category) or guess_cat(name)}
        self.d["templates"].append(t)
        self.d["quests"].append(self.make_quest(t))
        self.save()

    def add_run_km(self, km):
        """Add tracked kilometers to the first open quest measured in km."""
        for i, q in enumerate(self.d["quests"]):
            if not q["done"] and q.get("unit", "").strip().lower() in ("km", "kilometer", "kilometers", "kilometre", "kilometres"):
                return i, self.add_progress(i, round(km, 3))
        return None, []

    # ---- warnings / summaries ----
    def warning_due(self, now=None):
        """Seconds left if a 3h / 1h warning is due now (each is given once per cycle), else None."""
        now = time.time() if now is None else now
        left = self.d["cycle_start"] + DAY - now
        w = self.d.setdefault("warn", {"cycle": 0, "sent": []})
        if w.get("cycle") != self.d["cycle_start"]:
            w["cycle"], w["sent"] = self.d["cycle_start"], []
        if left <= 0 or all(q["done"] for q in self.d["quests"]):
            return None
        crossed = [h for h in WARN_HOURS if left <= h * 3600 and h not in w["sent"]]
        if not crossed:
            return None
        w["sent"] = sorted(set(w["sent"]) | set(crossed))
        self.save()
        return left

    def unfinished_text(self):
        parts = []
        for q in self.d["quests"]:
            if q["done"]:
                continue
            t = q.get("target", 1)
            parts.append(("%s %g/%g %s" % (q["name"], q.get("progress", 0), t, q.get("unit", ""))).strip() if t > 1 else q["name"])
        return ", ".join(parts)

    def quest_names(self):
        return ", ".join(q["name"] for q in self.d["quests"])

    def add_reps_by_name(self, word, n):
        """Add counted reps (from the camera) to the first open rep quest whose name has `word`."""
        for i, q in enumerate(self.d["quests"]):
            if not q["done"] and not q.get("trial") and word in q["name"].lower() and q.get("target", 1) > 1:
                return i, self.add_progress(i, n)
        return None, []

    def widget_text(self):
        d = self.d
        return "%s   Lv %d   Rank %s\nEXP %d/%d    HP %d/%d\nQuests %d/%d done    %s left\nStreak %d days    Gold %d" % (
            d["name"], d["level"], self.current_rank(), d["exp"], exp_needed(d["level"]), d["hp"], hp_max(d["level"]),
            sum(1 for q in d["quests"] if q["done"]), len(d["quests"]), hours_text(self.remaining()), d["streak"], d["gold"])

    def complete_by_keyword(self, kw):
        for i, q in enumerate(self.d["quests"]):
            if not q["done"] and not q.get("trial") and kw in q["name"].lower():
                return self.complete_quest(i)
        return []

    # ---- mastery ----
    def add_mastery(self, name, minutes=60, goal_days=365, cat="Mental"):
        self.d["mastery"].append({"id": self._new_id(), "name": name.strip(), "minutes": max(1, int(minutes)),
                                  "goal_days": max(1, int(goal_days)), "cat": norm_cat(cat) or "Mental",
                                  "percent": 0.0, "total_min": 0, "days": 0, "streak": 0, "best": 0,
                                  "day": "", "today": 0, "met": False})
        self.save()

    def remove_mastery(self, mid):
        self.d["mastery"] = [m for m in self.d["mastery"] if m["id"] != mid]
        self.save()

    def roll_mastery(self):
        """New day: today's minutes reset; the streak only survives if yesterday was completed."""
        today = today_str()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        for m in self.d["mastery"]:
            if m["day"] != today:
                if not (m["day"] == yesterday and m["met"]):
                    m["streak"] = 0
                m["day"], m["today"], m["met"] = today, 0, False

    def practice(self, mid, minutes):
        """Add practice minutes. Each day the percent grows by 100/goal_days when the daily minutes are
        reached (a little more for extra minutes, up to 1.5x). Finishing the daily minutes pays EXP."""
        self.roll_mastery()
        m = next((x for x in self.d["mastery"] if x["id"] == mid), None)
        if m is None or minutes <= 0:
            return []
        base = 100.0 / m["goal_days"]

        def credit(mins):
            return min(base * 1.5, mins * base / m["minutes"])
        old_percent, before = m["percent"], credit(m["today"])
        m["today"] += minutes
        m["total_min"] += minutes
        m["percent"] = min(100.0, m["percent"] + credit(m["today"]) - before)
        msgs = []
        if not m["met"] and m["today"] >= m["minutes"]:
            m["met"] = True
            m["days"] += 1
            m["streak"] += 1
            m["best"] = max(m["best"], m["streak"])
            msgs += self.add_exp(30)
            self.d["gold"] += 15
            self.d["attrs"][m["cat"]] += 2
            self.record(exp=30, attr=m["cat"], pts=2)
            msgs.insert(0, "MASTERY: %s - today's practice complete!  +30 EXP, %s +2" % (m["name"], m["cat"]))
        if old_percent < 100 <= m["percent"]:
            msgs.append("MASTERY ACHIEVED: %s. You are a Grandmaster!" % m["name"])
        msgs += self.check_titles()
        self.save()
        return msgs

    # ---- history ----
    def _day(self, date):
        return self.d["history"].setdefault(date, {"exp": 0, "habits": 0, "quests": 0, "perfect": False,
                                                   "attrs": {c: 0 for c in CATS}})

    def record(self, exp=0, habits=0, quests=0, attr="", pts=0, date=None):
        h = self._day(date or today_str())
        h["exp"] += exp
        h["habits"] += habits
        h["quests"] += quests
        if attr in CATS:
            h["attrs"][attr] = h["attrs"].get(attr, 0) + pts
        cutoff = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
        for k in [k for k in self.d["history"] if k < cutoff]:
            del self.d["history"][k]

    # ---- undo / edit the log ----
    def undo_log(self, idx):
        e = self.d["log"][idx]
        if isinstance(e, str):
            self.d["log"].pop(idx)
            self.save()
            return "Entry removed. (It is from an older version, so its EXP could not be reversed.)"
        if e.get("locked"):
            return "That entry caused a death, so it cannot be undone."
        self.set_total_exp(self.total_exp() - e["d_exp"])
        self.d["gold"] = max(0, self.d["gold"] - e["d_gold"])
        self.d["hp"] = max(1, min(hp_max(self.d["level"]), self.d["hp"] - e["d_hp"]))
        if e.get("cat"):
            self.d["attrs"][e["cat"]] = max(0, self.d["attrs"][e["cat"]] - e["pts"])
        self.d["counts"]["habits"] = max(0, self.d["counts"]["habits"] - 1)
        h = self.d["history"].get(datetime.date.fromtimestamp(e["ts"]).isoformat())
        if h:
            h["exp"] = max(0, h["exp"] - max(0, e["d_exp"]))
            h["habits"] = max(0, h["habits"] - 1)
            if e.get("cat"):
                h["attrs"][e["cat"]] = max(0, h["attrs"].get(e["cat"], 0) - e["pts"])
        self.d["log"].pop(idx)
        self.save()
        return "Entry undone. EXP, gold, HP and attribute points were reversed."

    def rename_log(self, idx, text):
        e = self.d["log"][idx]
        if isinstance(e, dict) and text.strip():
            e["text"] = text.strip()
            self.save()

    # ---- quit tracker ----
    def add_quit(self, name):
        self.d["quits"].append({"id": self._new_id(), "name": name.strip(), "since": time.time(), "best": 0})
        self.save()

    def slip_quit(self, qid, save=True):
        now = time.time()
        for q in self.d["quits"]:
            if q["id"] == qid:
                q["best"] = max(q.get("best", 0), now - q["since"])
                q["since"] = now
        if save:
            self.save()

    def remove_quit(self, qid):
        self.d["quits"] = [q for q in self.d["quits"] if q["id"] != qid]
        self.save()

    # ---- real-life rewards ----
    def add_reward(self, name, cost):
        self.d["rewards"].append({"id": self._new_id(), "name": name.strip(), "cost": int(cost)})
        self.save()

    def remove_reward(self, rid):
        self.d["rewards"] = [r for r in self.d["rewards"] if r["id"] != rid]
        self.save()

    def redeem_reward(self, rid):
        for r in self.d["rewards"]:
            if r["id"] == rid:
                if self.d["gold"] < r["cost"]:
                    return "Not enough gold (%d needed, you have %d)." % (r["cost"], self.d["gold"])
                self.d["gold"] -= r["cost"]
                self.d["redeemed"].append({"ts": time.time(), "name": r["name"], "cost": r["cost"]})
                self.save()
                return "Reward claimed: %s. Enjoy it, you earned it!" % r["name"]
        return "Reward not found."

    # ---- backup / restore ----
    def export_text(self):
        raw = json.dumps(self.d).encode("utf-8")
        return "SYSTEMSAVE1:" + base64.b64encode(zlib.compress(raw, 9)).decode("ascii")

    def import_text(self, text):
        text = "".join(text.split())
        if not text.startswith("SYSTEMSAVE1:"):
            raise ValueError("That is not a System backup.")
        try:
            d = json.loads(zlib.decompress(base64.b64decode(text.split(":", 1)[1])).decode("utf-8"))
        except Exception:
            raise ValueError("The backup text is damaged or incomplete.")
        if not isinstance(d, dict) or "level" not in d or "exp" not in d:
            raise ValueError("That backup does not contain a valid save.")
        self.d = d
        self.save()
        self.load()  # fills in anything an older backup is missing

    def carried_plans(self):
        return [p for p in self.d["plans"] if p["date"] < today_str() and not p["done"]]

    # ---- planner (not part of the log: no EXP) ----
    def add_plan(self, date, text):
        when, task = parse_plan(text)
        if not task:
            return
        self.d["plans"].append({"id": self._new_id(), "date": date, "time": when, "text": task, "done": False})
        self.save()

    def plans_for(self, date):
        items = [p for p in self.d["plans"] if p["date"] == date]
        return sorted(items, key=lambda p: (p["time"] == "", p["time"], p["id"]))

    def toggle_plan(self, pid):
        for p in self.d["plans"]:
            if p["id"] == pid:
                p["done"] = not p["done"]
        self.save()

    def remove_plan(self, pid):
        self.d["plans"] = [p for p in self.d["plans"] if p["id"] != pid]
        self.save()

    def clean_plans(self):
        """Drop plans older than yesterday."""
        keep = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        before = len(self.d["plans"])
        self.d["plans"] = [p for p in self.d["plans"] if p["date"] >= keep]
        if len(self.d["plans"]) != before:
            self.save()

    # ---- journal ----
    def journaled_today(self):
        today = time.strftime("%Y-%m-%d")
        return any(time.strftime("%Y-%m-%d", time.localtime(e["ts"])) == today for e in self.d["journal"])

    def add_journal(self, text):
        """Saves an entry. Returns True if it is the first entry today (that one earns EXP)."""
        first = not self.journaled_today()
        self.d["journal"].append({"id": self._new_id(), "ts": time.time(), "text": text.strip()})
        self.save()
        return first

    def remove_journal(self, jid):
        self.d["journal"] = [e for e in self.d["journal"] if e["id"] != jid]
        self.save()

    # ---- routine + to-do ----
    def _new_id(self):
        n = self.d["next_id"]
        self.d["next_id"] = n + 1
        return n

    def add_routine(self, text):
        self.d["routines"].append({"id": self._new_id(), "text": text.strip(), "last_done": ""})
        self.save()

    def remove_routine(self, rid):
        self.d["routines"] = [r for r in self.d["routines"] if r["id"] != rid]
        self.save()

    def routine_done_today(self, r):
        return r.get("last_done") == time.strftime("%Y-%m-%d")

    def mark_routine(self, rid):
        for r in self.d["routines"]:
            if r["id"] == rid:
                r["last_done"] = time.strftime("%Y-%m-%d")
        self.save()

    def todos_sorted(self):
        order = {"hard": 0, "mid": 1, "easy": 2}
        return sorted(self.d["todos"], key=lambda t: (order.get(t.get("level", "mid"), 1), t.get("due") is None, t.get("due") or 0, t["id"]))

    def add_todo(self, text, due=None, level="mid"):
        self.d["todos"].append({"id": self._new_id(), "text": text.strip(), "due": due, "notified": False, "level": level})
        self.save()

    def remove_todo(self, tid):
        self.d["todos"] = [t for t in self.d["todos"] if t["id"] != tid]
        self.save()

    def due_todos(self, now=None):
        """To-dos whose reminder time has come (each is returned once)."""
        now = time.time() if now is None else now
        due = [t for t in self.d["todos"] if t.get("due") and t["due"] <= now and not t.get("notified")]
        for t in due:
            t["notified"] = True
        if due:
            self.save()
        return due

    def complete_punishment(self, i):
        if 0 <= i < len(self.d["punishments"]):
            self.d["punishments"].pop(i)
            self.save()

    def remaining(self):
        return max(0, self.d["cycle_start"] + DAY - time.time())

    def tick(self):
        """Resolve expired 24h cycles. Returns list of messages."""
        msgs, now, n = [], time.time(), 0
        while now - self.d["cycle_start"] >= DAY and n < 30:
            n += 1
            failed = [q for q in self.d["quests"] if not q["done"]]
            cdate = datetime.date.fromtimestamp(self.d["cycle_start"]).isoformat()
            for q in failed:  # the penalty shrinks with how far you got
                tgt = q.get("target", 1)
                frac = min(1.0, q.get("progress", 0) / float(tgt)) if tgt else 0.0
                pen = int(round(q["penalty"] * (1 - frac)))
                self.lose_exp(pen)
                msgs += self.lose_hp(pen // 2)
                if frac < 0.5:
                    self.d["punishments"].append(q["punishment"])
                    msgs.append("QUEST FAILED: %s  -%d EXP\n%s" % (q["name"], pen, q["punishment"]))
                else:
                    msgs.append("QUEST NOT FINISHED: %s  -%d EXP (you got %d%%, no punishment)" % (q["name"], pen, frac * 100))
            if failed:
                self.d["streak"] = 0
            else:
                self.d["streak"] += 1
                self.d["best_streak"] = max(self.d["best_streak"], self.d["streak"])
                self.d["gold"] += 20
                self.heal(20)
                bonus = min(50, 5 * self.d["streak"])
                msgs += self.add_exp(bonus)
                self.record(exp=bonus, date=cdate)
                self._day(cdate)["perfect"] = True
                msgs.append("STREAK %d days: +%d EXP" % (self.d["streak"], bonus))
            self.new_cycle(self.d["cycle_start"] + DAY)
        if n:
            msgs += self.check_titles()
            self.save()
        return msgs
