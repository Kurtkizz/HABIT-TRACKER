import json, math, os, re, time

DAY = 86400
RANKS = [(1, "E"), (10, "D"), (20, "C"), (35, "B"), (50, "A"), (70, "S"),
         (90, "SS"), (120, "SSS"), (160, "Transcendent"), (200, "Absolute Apex")]
STATS = ["STR", "AGI", "VIT", "INT", "SENSE"]

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
]


def hp_max(level):
    return 100 + 10 * level

# value > 0 = good (EXP gain), 0 = harmless/neutral, < 0 = bad (EXP loss)
DEFAULT_HABITS = [
    {"kw": ["workout", "exercise", "gym", "push-ups", "pushups", "sit-ups", "squats"], "value": 30, "stat": "STR"},
    {"kw": ["run", "running", "jog", "jogging", "walk", "walking", "cardio"], "value": 25, "stat": "AGI"},
    {"kw": ["study", "studied", "read", "reading", "learn", "coding", "practice"], "value": 25, "stat": "INT"},
    {"kw": ["meditate", "meditation", "journal", "journaling"], "value": 20, "stat": "SENSE"},
    {"kw": ["drink water", "drank water", "healthy meal", "vegetables", "cold shower", "slept early", "woke up early"], "value": 15, "stat": "VIT"},
    {"kw": ["junk food", "fast food", "soda", "overslept", "snack"], "value": 0, "stat": ""},
    {"kw": ["scrolling", "doomscroll", "tiktok", "social media", "procrastinated", "wasted time", "skipped workout"], "value": -10, "stat": ""},
    {"kw": ["stayed up late", "all-nighter", "skipped class"], "value": -15, "stat": ""},
    {"kw": ["smoke", "smoked", "smoking", "vape", "vaped", "drunk", "alcohol"], "value": -40, "stat": ""},
]

DEFAULT_QUESTS = [
    {"name": "Push-ups", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 50 extra push-ups", "target": 100, "unit": "reps"},
    {"name": "Sit-ups", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 50 extra sit-ups", "target": 100, "unit": "reps"},
    {"name": "Squats", "reward": 40, "penalty": 30, "punishment": "Penalty Zone: 50 extra squats", "target": 100, "unit": "reps"},
    {"name": "Run", "reward": 60, "penalty": 40, "punishment": "Penalty Zone: run 3 km extra", "target": 10, "unit": "km"},
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


def exp_needed(level):
    return 100 + 25 * level


def habits_to_text(habits):
    return "\n".join("%s | %d | %s" % (", ".join(h["kw"]), h["value"], h.get("stat", "")) for h in habits)


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
        stat = p[2].upper() if len(p) > 2 and p[2].upper() in STATS else ""
        out.append({"kw": [k.strip().lower() for k in p[0].split(",") if k.strip()], "value": val, "stat": stat})
    return out


def quests_to_text(qs):
    return "\n".join("%s | %d | %d | %s | %g | %s" % (q["name"], q["reward"], q["penalty"], q["punishment"],
                                                       q.get("target", 1), q.get("unit", "")) for q in qs)


def text_to_quests(text):
    out = []
    for line in text.splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) < 4 or not p[0]:
            continue
        try:
            target = float(p[4]) if len(p) > 4 and p[4] else 1.0
            out.append({"name": p[0], "reward": int(p[1]), "penalty": int(p[2]), "punishment": p[3],
                        "target": max(target, 1.0), "unit": p[5] if len(p) > 5 else ""})
        except ValueError:
            continue
    return out


class Game:
    def __init__(self, path):
        self.path = path
        self.d = {}
        self.arrived = False
        self.warned = 0
        self.load()

    def default(self):
        return {
            "name": "Player", "level": 1, "exp": 0, "pin": "0000", "streak": 0,
            "stats": {s: 1 for s in STATS},
            "habits": [dict(h) for h in DEFAULT_HABITS],
            "templates": [dict(q) for q in DEFAULT_QUESTS],
            "cycle_start": time.time(), "quests": [], "punishments": [], "log": [],
            "hp": hp_max(1), "gold": 0, "title": "Weakest Hunter", "titles": ["Weakest Hunter"],
            "best_streak": 0, "counts": {"habits": 0, "quests": 0, "deaths": 0},
        }

    def load(self):
        base = self.default()
        try:
            with open(self.path) as f:
                self.d = json.load(f)
        except Exception:
            self.d = base
        for k, v in base.items():
            self.d.setdefault(k, v)
        if not self.d["quests"]:
            self.new_cycle(self.d["cycle_start"])
        self.save()

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
            msgs.append("LEVEL UP! You are now Level %d [Rank %s]" % (self.d["level"], rank_for(self.d["level"])))
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

    def set_level(self, level):
        self.d["level"] = max(1, level)
        self.d["exp"] = 0

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
        if value > 0:
            msgs += self.add_exp(value)
            self.d["gold"] += value // 2
            if stat in self.d["stats"]:
                self.d["stats"][stat] += 1
            res = "[GOOD] +%d EXP" % value
        elif value < 0:
            self.lose_exp(-value)
            msgs += self.lose_hp(-value // 2)
            res = "[BAD] %d EXP, -%d HP" % (value, -value // 2)
        else:
            res = "[NEUTRAL] No EXP"
        self.d["log"].insert(0, "%s  %s  %s" % (time.strftime("%m-%d %H:%M"), text, res))
        del self.d["log"][100:]
        self.d["counts"]["habits"] += 1
        msgs += self.check_titles()
        self.save()
        return [res] + msgs

    def add_rule(self, text, value):
        self.d["habits"].append({"kw": [text.lower().strip()], "value": value, "stat": ""})

    # ---- daily quests ----
    def new_cycle(self, start):
        self.d["cycle_start"] = start
        self.d["quests"] = [dict(q, done=False, progress=0) for q in self.d["templates"]]
        self.arrived = True

    def complete_quest(self, i):
        q = self.d["quests"][i]
        if q["done"]:
            return []
        q["done"] = True
        q["progress"] = q.get("target", 1)
        msgs = ["Quest complete: %s  +%d EXP" % (q["name"], q["reward"])] + self.add_exp(q["reward"])
        self.d["gold"] += q["reward"] // 2
        self.d["counts"]["quests"] += 1
        self.heal(5)
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

    def add_template(self, name, target, unit, reward, penalty, punishment):
        t = {"name": name, "reward": reward, "penalty": penalty, "punishment": punishment,
             "target": max(target, 1.0), "unit": unit}
        self.d["templates"].append(t)
        self.d["quests"].append(dict(t, done=False, progress=0))
        self.save()

    def add_run_km(self, km):
        """Add tracked kilometers to the first open quest measured in km."""
        for i, q in enumerate(self.d["quests"]):
            if not q["done"] and q.get("unit", "").strip().lower() in ("km", "kilometer", "kilometers", "kilometre", "kilometres"):
                return i, self.add_progress(i, round(km, 3))
        return None, []

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
            for q in failed:
                self.lose_exp(q["penalty"])
                self.d["punishments"].append(q["punishment"])
                msgs += self.lose_hp(q["penalty"] // 2)
                msgs.append("QUEST FAILED: %s  -%d EXP\n%s" % (q["name"], q["penalty"], q["punishment"]))
            if failed:
                self.d["streak"] = 0
            else:
                self.d["streak"] += 1
                self.d["best_streak"] = max(self.d["best_streak"], self.d["streak"])
                self.d["gold"] += 20
                self.heal(20)
            self.new_cycle(self.d["cycle_start"] + DAY)
        if n:
            msgs += self.check_titles()
            self.save()
        return msgs
