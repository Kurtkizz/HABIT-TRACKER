"""Counts push-ups, sit-ups and squats from body landmarks. Pure Python, tested on a computer."""
import math

NAMES = {"pushup": "Push-ups", "situp": "Sit-ups", "squat": "Squats"}
QUEST_WORD = {"pushup": "push", "situp": "sit", "squat": "squat"}
JOINTS = {"pushup": ("shoulder", "elbow", "wrist"), "squat": ("hip", "knee", "ankle"), "situp": ("shoulder", "hip", "knee")}
# angle (degrees) at the middle joint: (extended = start/finish position, flexed = bottom of a rep)
LIMITS = {"pushup": (150, 100), "squat": (160, 110), "situp": (125, 85)}
MIN_GAP = {"pushup": 0.6, "squat": 0.8, "situp": 0.8}  # seconds between two reps
MIN_LIKELIHOOD = 0.5


def angle(a, b, c):
    """Angle at b (degrees) between the lines b-a and b-c."""
    v1, v2 = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return None
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


class RepCounter:
    """Feed it landmark dicts ({'l_knee': (x, y, likelihood), ...}); read .count / .status / .angle."""

    def __init__(self, kind):
        self.kind = kind
        self.extended, self.flexed = LIMITS[kind]
        self.count = 0
        self.stage = "unknown"
        self.angle = None
        self.status = "Get in position"
        self.last_rep = -1e9
        self._recent = []

    def adjust(self, delta):
        self.count = max(0, self.count + delta)

    def _side_angle(self, lm, side):
        pts = [lm.get(side + n) for n in JOINTS[self.kind]]
        if any(p is None or p[2] < MIN_LIKELIHOOD for p in pts):
            return None
        return angle(pts[0], pts[1], pts[2])

    def _level(self, lm):
        """Push-ups only count when the body is roughly horizontal (not standing)."""
        spans = []
        for s in ("l_", "r_"):
            sh, an = lm.get(s + "shoulder"), lm.get(s + "ankle")
            if sh and an and sh[2] >= MIN_LIKELIHOOD and an[2] >= MIN_LIKELIHOOD:
                spans.append((abs(an[0] - sh[0]), abs(an[1] - sh[1])))
        if not spans:
            return True  # ankles out of view: cannot tell, so do not block
        return sum(s[0] for s in spans) >= sum(s[1] for s in spans)

    def update(self, lm, now):
        angles = [a for a in (self._side_angle(lm, "l_"), self._side_angle(lm, "r_")) if a is not None]
        if not angles:
            self.status = "Body not found - step back so your whole body is in view"
            return self.count
        if self.kind == "pushup" and not self._level(lm):
            self.status, self.stage = "Get into push-up position", "unknown"
            return self.count
        self._recent = (self._recent + [sum(angles) / len(angles)])[-3:]
        a = self.angle = sum(self._recent) / len(self._recent)
        if a >= self.extended:
            if self.stage == "flexed" and now - self.last_rep >= MIN_GAP[self.kind]:
                self.count += 1
                self.last_rep = now
                self.status = "Rep %d!" % self.count
            elif self.stage != "flexed":
                self.status = "Ready - start"
            self.stage = "extended"
        elif a <= self.flexed and self.stage == "extended":
            self.stage = "flexed"
            self.status = "Down - now come back up"
        return self.count
