"""2D animation layer: walking actors (sprite cycles) and ambient effects drawn per frame in scene space."""
import math, os, subprocess, functools
import numpy as np, cv2
from scenes import man, woman, car, defs, SW, SH
import figures as FG

SPR = "/tmp/sprites"; os.makedirs(SPR, exist_ok=True)

@functools.lru_cache(maxsize=None)
def sprite(kind, s, phase_i, back, n=12):
    """RGBA sprite of a figure at walk phase; anchor = feet at (w/2, h-20)."""
    w, h = (int(420 * s), int(260 * s)) if kind.startswith("car") else ((int(640 * s), int(440 * s)) if kind.startswith("camel") else (int(260 * s), int(400 * s)))
    ph = 2 * math.pi * phase_i / n
    x, y = w / 2, h - 20 * s
    bob = abs(math.sin(ph)) * 5 * s
    back_view = back not in (False, "side", "side_left")
    if kind.startswith("camel"):  # walking camel (kit3), back="left" faces left
        from kit3 import camel
        wk = math.sin(ph) if kind in ("camel", "camel_led") else 0
        if kind.startswith("camel_led"):  # man leading the camel on a rein (nafs held in hand)
            g = camel(-90 * s, -bob * 0.4, s, walk=wk) + man(210 * s, -bob, s * 1.02, back=False, walk=wk)
            g += f'<path d="M{132*s},{-342*s} Q{175*s},{-200*s} {242*s},{-150*s}" fill="none" stroke="#6b4a35" stroke-width="{5*s}"/>'
            body = f'<g transform="translate({x},{y}) scale({-1 if back == "left" else 1},1)">{g}</g>'
        else:
            body = camel(x, y - bob * 0.5, s, walk=wk, flip=(back == "left"))
    elif kind.startswith("car"):  # moving sedan: tiny body bounce (wheels drawn by scenes.car)
        body = car(x, y - (abs(math.sin(ph)) * 2 * s if kind == "car" else 0), s * 1.0, col=back if isinstance(back, str) and back.startswith("#") else "#355078")
    elif kind == "man":
        body = man(x, y - bob, s, back=back_view, walk=math.sin(ph))
    elif kind in ("man_still", "man_dua"):
        body = man(x, y - math.sin(ph) * 1.5 * s, s, back=back_view, walk=0)
    else:
        body = woman(x, y - bob * 0.6, s)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{defs()}{body}</svg>'
    p = f"{SPR}/v1_{kind}_{s:.2f}_{phase_i}_{back}"
    open(p + ".svg", "w").write(svg)
    subprocess.run(["rsvg-convert", p + ".svg", "-o", p + ".png"], check=True)
    return cv2.imread(p + ".png", cv2.IMREAD_UNCHANGED)

def paste(img, spr, cx, cy):
    h, w = spr.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h + 20)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, img.shape[1]), min(y0 + h, img.shape[0])
    if xa >= xb or ya >= yb: return
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0]
    a = s[..., 3:4].astype(np.float32) / 255
    img[ya:yb, xa:xb] = (img[ya:yb, xa:xb] * (1 - a) + s[..., :3] * a).astype(img.dtype)

def paste_rgba(img, spr, cx, cy):
    h, w = spr.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h + 20)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, img.shape[1]), min(y0 + h, img.shape[0])
    if xa >= xb or ya >= yb: return
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = s[..., 3:4] / 255
    dst = img[ya:yb, xa:xb]
    da = dst[..., 3:4] / 255
    oa = a + da * (1 - a)
    rgb = (s[..., :3] * a + dst[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6)
    img[ya:yb, xa:xb, :3] = rgb; img[ya:yb, xa:xb, 3:4] = oa * 255

def ease(t): return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0), 1))

class Particles:
    def __init__(self, kind, n, seed, region=(0, 0, SW, SH)):
        r = np.random.default_rng(seed); x0, y0, x1, y1 = region
        self.kind, self.region = kind, region
        self.p = np.c_[r.uniform(x0, x1, n), r.uniform(y0, y1, n), r.uniform(0.6, 1.4, n), r.uniform(0, 6.28, n)]

    def draw(self, img, t):
        x0, y0, x1, y1 = self.region; W_, H_ = x1 - x0, y1 - y0
        for px, py, sp, ph in self.p:
            if self.kind == "rain":
                y = y0 + (py - y0 + t * 1400 * sp) % H_; x = px - (y - py) * 0.12
                cv2.line(img, (int(x), int(y)), (int(x - 10), int(y + 55)), (220, 205, 200), 2, cv2.LINE_AA)
            elif self.kind == "dust":
                x = px + 30 * math.sin(t * 0.6 * sp + ph); y = y0 + (py - y0 - t * 25 * sp) % H_
                a = 0.5 + 0.5 * math.sin(t * 2 * sp + ph)
                cv2.circle(img, (int(x), int(y)), int(3 + 2 * sp), (150, 225, 255), -1, cv2.LINE_AA) if a > 0.3 else None
            elif self.kind == "leaves":
                x = x0 + (px - x0 + t * 90 * sp) % W_; y = y0 + (py - y0 + t * 60 * sp) % H_ + 25 * math.sin(t * 1.5 + ph)
                ang = t * 90 * sp + ph * 57
                box = cv2.boxPoints(((x, y), (22, 10), ang)).astype(np.int32)
                cv2.fillPoly(img, [box], (85, 138, 95), cv2.LINE_AA)
            elif self.kind == "birds":
                x = x0 + (px - x0 + t * 120 * sp) % W_; y = py + 15 * math.sin(t + ph); f = 14 * math.sin(t * 8 * sp + ph)
                pts = np.array([[x - 22, y - f], [x, y], [x + 22, y - f]], np.int32)
                cv2.polylines(img, [pts], False, (72, 58, 59), 3, cv2.LINE_AA)
            elif self.kind == "snow":
                x = px + 25 * math.sin(t * 0.9 * sp + ph); y = y0 + (py - y0 + t * 110 * sp) % H_
                cv2.circle(img, (int(x), int(y)), int(3 + 3 * sp), (250, 248, 246), -1, cv2.LINE_AA)
            elif self.kind == "petals":
                x = x0 + (px - x0 + t * 55 * sp) % W_; y = y0 + (py - y0 + t * 85 * sp) % H_ + 18 * math.sin(t * 2 + ph)
                ang = t * 120 * sp + ph * 57
                box = cv2.boxPoints(((x, y), (16, 9), ang)).astype(np.int32)
                cv2.fillPoly(img, [box], (196, 170, 242) if sp > 1 else (170, 120, 222), cv2.LINE_AA)
            elif self.kind == "stars":
                a = 0.5 + 0.5 * math.sin(t * 3 * sp + ph)
                c = int(170 + 85 * a); cv2.circle(img, (int(px), int(py)), 2 + int(2 * a), (c, c, 255), -1, cv2.LINE_AA)

def flicker(img, t, pts):
    """warm glow pulsing around lanterns (scene coords)."""
    for i, (x, y, r) in enumerate(pts):
        k = 0.10 + 0.06 * math.sin(t * 7.3 + i * 1.7) + 0.04 * math.sin(t * 13.1 + i)
        x0, y0, x1, y1 = max(int(x - r), 0), max(int(y - r), 0), min(int(x + r), img.shape[1]), min(int(y + r), img.shape[0])
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.clip(1 - np.hypot(xx - x, yy - y) / r, 0, 1)[..., None] ** 2
        img[y0:y1, x0:x1] = np.clip(img[y0:y1, x0:x1] + d * k * np.array([110, 200, 255], np.float32), 0, 255)

def cloud_drift(base, t, speed=12, band=(0, 900)):
    """shift the sky band horizontally for drifting clouds."""
    y0, y1 = band; dx = int(t * speed) % base.shape[1]
    out = base.copy(); out[y0:y1] = np.roll(base[y0:y1], dx, axis=1)
    return out

def apply(scene_img, spec, t_local, t_abs):
    """scene_img: float32 BGR at scene resolution. spec: dict from plan scene 'anim'."""
    img = scene_img
    if spec.get("clouds"): img = cloud_drift(img, t_abs, *spec["clouds"])
    else: img = img.copy()
    if spec.get("flicker"):
        rgb = img[..., :3].copy(); flicker(rgb, t_abs, spec["flicker"]); img[..., :3] = rgb
    for (cx, cy, r, sp) in spec.get("clocks", []):  # rotating clock hands (scene coords); sp = minute-hand turns/s
        rgb = np.ascontiguousarray(img[..., :3])
        for L, wdt, k in ((0.78 * r, max(3, r // 18), sp), (0.5 * r, max(5, r // 12), sp / 12)):
            ang = 2 * math.pi * (t_local * k) - math.pi / 2
            cv2.line(rgb, (int(cx), int(cy)), (int(cx + L * math.cos(ang)), int(cy + L * math.sin(ang))), (72, 58, 59), int(wdt), cv2.LINE_AA)
        cv2.circle(rgb, (int(cx), int(cy)), int(max(5, r // 14)), (72, 58, 59), -1, cv2.LINE_AA)
        img[..., :3] = rgb
    for a in spec.get("actors", []):
        dur = a.get("dur", 1.0)
        k = ease(t_local / dur) if a.get("ease", True) else min(t_local / dur, 1)
        x = a["x0"] + (a["x1"] - a["x0"]) * k; y = a["y0"] + (a["y1"] - a["y0"]) * k
        s = a["s0"] + (a.get("s1", a["s0"]) - a["s0"]) * k
        moving = abs(a["x1"] - a["x0"]) + abs(a["y1"] - a["y0"]) > 1 and k < 0.999
        kind = a.get("kind", "man")
        if kind == "man" and not moving: kind = "man_still"
        if kind == "woman" and not moving: kind = "woman_still"
        if kind == "car" and not moving: kind = "car_still"
        if kind in ("camel", "camel_led") and not moving: kind = kind + "_still"
        pi = int(t_abs * (10 if moving else 2)) % 12
        spr = sprite(kind, round(s * 20) / 20, pi, a.get("view", a.get("back", True)))
        if img.shape[2] == 4: paste_rgba(img, spr, x, y)
        else: paste(img, spr.astype(np.float32), x, y)
    for p in spec.get("_particles", []): p.draw(img, t_abs)
    return img

def build_particles(spec, seed):
    out = []
    for kind, n, region in spec.get("particles", []):
        out.append(Particles(kind, n, seed + len(out), tuple(region)))
    spec["_particles"] = out
