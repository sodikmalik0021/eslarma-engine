"""Animate illustrated scenes into a 9:16 reel with synced subtitles and the ORIGINAL audio (stream-copied)."""
import json, subprocess, sys, math
import numpy as np, cv2
import fx, layers as L
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
GREEN, GOLD = (31, 61, 43), (196, 146, 52)

def ease(t): return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0), 1))

def load_scene(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return img

def camera(img, t, move):
    h, w = img.shape[:2]
    base = max(W / w, H / h)
    e = ease(t)
    z0, z1, dx0, dx1, dy0, dy1 = {
        "push":   (1.00, 1.10, 0, 0, 0, 0),
        "pull":   (1.10, 1.00, 0, 0, 0, 0),
        "up":     (1.08, 1.12, 0, 0, 0.05, -0.05),
        "down":   (1.08, 1.12, 0, 0, -0.05, 0.05),
        "left":   (1.10, 1.12, 0.05, -0.05, 0, 0),
        "right":  (1.10, 1.12, -0.05, 0.05, 0, 0),
    }[move]
    z = base * (z0 + (z1 - z0) * e)
    cx = w / 2 + (dx0 + (dx1 - dx0) * e) * w
    cy = h / 2 + (dy0 + (dy1 - dy0) * e) * h
    M = np.float32([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)

def paper_texture(seed=7):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    n = cv2.GaussianBlur(cv2.resize(n, (W, H)), (0, 0), 6)
    blot = cv2.GaussianBlur(rng.normal(0, 1, (H // 60, W // 60)).astype(np.float32), (0, 0), 1.2)
    blot = cv2.resize(blot, (W, H), interpolation=cv2.INTER_CUBIC)
    grain = rng.normal(0, 1, (H, W)).astype(np.float32)
    tex = 0.014 * n / (n.std() + 1e-6) + 0.012 * blot / (blot.std() + 1e-6) + 0.006 * grain
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return (1 + tex)[..., None], vig[..., None]

def chunk_words(words, keywords):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_punct = w["w"].endswith((".", ",", "?", "!", ":", ";", "»"))
        gap = nxt and nxt["s"] - w["e"] > 0.35
        if len(cur) >= 6 or end_punct or gap or nxt is None or (len(cur) >= 2 and len(" ".join(x["w"] for x in cur)) > 34):  # up to 2 lines, like bashar.uz
            chunks.append({"words": cur, "s": cur[0]["s"], "e": cur[-1]["e"]})
            cur = []
    for i, c in enumerate(chunks):  # hold until next chunk, max +0.6s
        nxt = chunks[i + 1]["s"] if i + 1 < len(chunks) else c["e"] + 0.6
        c["e"] = min(max(c["e"], c["s"] + 0.35), nxt - 0.02, c["e"] + 0.6) if i + 1 < len(chunks) else c["e"] + 0.6
    return chunks

_font = {}
def font(sz):
    if sz not in _font: _font[sz] = ImageFont.truetype(FONT, sz)
    return _font[sz]

SET = {}  # the owner's settings: sub_size, sub_y, sub_color, title_size

BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
_bold = {}


def bold(sz):
    if sz not in _bold:
        try:
            _bold[sz] = ImageFont.truetype(BOLD, sz)
        except Exception:
            _bold[sz] = font(sz)
    return _bold[sz]


def draw_subtitle(frame, chunk, t, keywords, handle):
    """bashar.uz look: big bold dark green words on a soft white glow, up to 2 centred lines;
    a spoken word is dark (keyword gold), the coming words already show in pale green"""
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    f = bold(int(SET.get("sub_size", 54)))
    y = int(H * float(SET.get("sub_y", 0.775)))
    lh = int(f.size * 1.3)
    if chunk:
        fade_in = min(1, (t - chunk["s"]) / 0.18)
        fade_out = min(1, (chunk["e"] - t) / 0.15)
        a = max(0, min(fade_in, fade_out))
        lines, cur = [], []
        for w in chunk["words"]:
            if cur and f.getlength(" ".join(x["w"] for x in cur + [w])) > 860:
                lines.append(cur); cur = []
            cur.append(w)
        lines.append(cur)
        widths = [f.getlength(" ".join(x["w"] for x in l)) for l in lines]
        top = y - lh * (len(lines) - 1) // 2
        glow = Image.new("L", (W, H), 0)
        gd = ImageDraw.Draw(glow)
        bw = max(widths) + 120
        gd.rounded_rectangle([W / 2 - bw / 2, top - lh // 2 - 18, W / 2 + bw / 2, top + lh * (len(lines) - 1) + lh // 2 + 18], radius=lh // 2 + 18, fill=int(225 * a))
        glow = glow.filter(ImageFilter.GaussianBlur(26))
        img = Image.composite(Image.new("RGB", (W, H), (250, 248, 242)), img, glow)
        d = ImageDraw.Draw(img)
        dark = tuple(int(SET["sub_color"][i:i + 2], 16) for i in (1, 3, 5)) if SET.get("sub_color") else (10, 70, 48)
        pale = (125, 150, 135)
        for li, l in enumerate(lines):
            cx, ly = W / 2 - widths[li] / 2, top + li * lh
            for w in l:
                spoken = t >= w["s"] - 0.03
                key = w["w"].strip(".,!?:;«»\"'").lower() in keywords
                col = ((196, 146, 52) if key else dark) if spoken else pale
                base = np.array(img.getpixel((min(W - 1, int(cx)), ly)))
                c = tuple(int(base[k] + (col[k] - base[k]) * a) for k in range(3))
                d.text((cx, ly), w["w"], font=f, fill=c, anchor="lm")
                cx += f.getlength(w["w"] + " ")
        hy = top + lh * (len(lines) - 1) + lh // 2 + 40
    else:
        hy = y + 72
    d = ImageDraw.Draw(img)
    d.text((W / 2, hy), handle, font=font(28), fill=(40, 80, 60), anchor="mm")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

HOOK_FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]

def draw_overlay(frame, t, dur, hook, cta):
    """Big hook title in the first seconds; small follow call-to-action at the end."""
    if not hook and not cta: return frame
    show_hook = hook and t < 2.6
    show_cta = cta and t > dur - 3.0
    if not (show_hook or show_cta): return frame
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if show_hook:
        a = min(1, t / 0.25) * min(1, (2.6 - t) / 0.35)
        pop = 1 + 0.06 * max(0, 1 - t / 0.35)
        f = ImageFont.truetype(HOOK_FONT, int(int(SET.get("title_size", 84)) * pop))
        lines = wrap(hook, f, W * 0.8)
        lh = int(int(SET.get("title_size", 84)) * 1.19 * pop); y0 = int(H * 0.30 - lh * len(lines) / 2)
        bw = max(f.getlength(l) for l in lines) + 90
        d.rounded_rectangle([W / 2 - bw / 2, y0 - 40, W / 2 + bw / 2, y0 + lh * len(lines) + 30], radius=40, fill=(250, 246, 236, int(225 * a)))
        for i, l in enumerate(lines):
            d.text((W / 2, y0 + i * lh + lh / 2), l, font=f, fill=(31, 61, 43, int(255 * a)), anchor="mm")
        d.rounded_rectangle([W / 2 - 60, y0 + lh * len(lines) + 4, W / 2 + 60, y0 + lh * len(lines) + 12], radius=4, fill=(196, 146, 52, int(255 * a)))
    if show_cta:
        a = min(1, (t - (dur - 3.0)) / 0.4)
        f = ImageFont.truetype(HOOK_FONT, 44)
        tw = f.getlength(cta) + 70
        y = int(H * 0.115)
        d.rounded_rectangle([W / 2 - tw / 2, y - 42, W / 2 + tw / 2, y + 42], radius=42, fill=(31, 61, 43, int(230 * a)))
        d.text((W / 2, y), cta, font=f, fill=(246, 228, 180, int(255 * a)), anchor="mm")
    img = Image.alpha_composite(img, lay).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

class Clip:
    """an animated painting stretched to the length of its shot; in-between frames come from optical flow"""
    def __init__(self, path):
        c, self.f = cv2.VideoCapture(path), []
        while True:
            ok, fr = c.read()
            if not ok: break
            self.f.append(fr)
        if len(self.f) < 8: raise RuntimeError("empty clip " + path)
        self.key, self.pair = None, None
        h, w = self.f[0].shape[:2]
        self.grid = np.stack(np.meshgrid(np.arange(w), np.arange(h)), -1).astype(np.float32)
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_FAST)

    def at(self, lt):
        x = min(max(lt, 0), 1) * (len(self.f) - 1)
        i = min(int(x), len(self.f) - 2); a = x - i
        fr = self.f[i]
        if fr.shape[0] < 1500 and a > 0.02:
            if self.key != i:
                g = [cv2.cvtColor(self.f[j], cv2.COLOR_BGR2GRAY) for j in (i, i + 1)]
                self.key, self.pair = i, (self.dis.calc(g[0], g[1], None), self.dis.calc(g[1], g[0], None))
            p = cv2.remap(self.f[i], self.grid - self.pair[0] * a, None, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            q = cv2.remap(self.f[i + 1], self.grid - self.pair[1] * (1 - a), None, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            fr = p * (1 - a) + q * a
        if fr.shape[:2] != (H, W):
            k = max(W / fr.shape[1], H / fr.shape[0])
            fr = cv2.resize(fr.astype(np.float32), None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
            y, x0 = (fr.shape[0] - H) // 2, (fr.shape[1] - W) // 2
            fr = fr[y:y + H, x0:x0 + W]
            fr = cv2.addWeighted(fr, 1.5, cv2.GaussianBlur(fr, (0, 0), 2.0), -0.5, 0)
        return np.clip(fr.astype(np.float32), 0, 255)


def main(plan_path):
    plan = json.load(open(plan_path))
    dur = plan["duration"]
    SET.update(plan.get("settings") or {})
    scenes = plan["scenes"]
    imgs = []
    for s in scenes:
        if s.get("video"):
            imgs.append(Clip(s["video"]))
        elif s.get("layers"):
            ls = []
            for l in s["layers"]:
                im = cv2.imread(l["png"], cv2.IMREAD_UNCHANGED)
                if im.shape[2] == 3: im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
                ls.append((im, l["depth"], l))  # uint8 in memory; float32 per frame (RAM)
            imgs.append(ls)
        else:
            imgs.append(load_scene(s["png"]).astype(np.float32))
    for i, s in enumerate(scenes):
        if s.get("anim"): fx.build_particles(s["anim"], 100 + i)
    words = plan["words"]
    keywords = {k.lower() for k in plan.get("keywords", [])}
    chunks = chunk_words(words, keywords)
    tex, vig = paper_texture()
    n = int(round(dur * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                            "-pix_fmt", "yuv420p", plan["video_only"]], stdin=subprocess.PIPE)
    XF = 0.6
    def shot(i, t):
        s = scenes[i]; lt = (t - s["start"]) / max(s["end"] - s["start"], 0.1)
        if s.get("video"):
            fr = imgs[i].at((t - s["start"]) / max(s["end"] + (XF if i + 1 < len(scenes) else 0) - s["start"], 0.1))
            for p in s.get("_screen_particles", []):
                p.draw(fr, t)
            return fr
        if s.get("layers"):
            lay = []
            for img, depth, spec in imgs[i]:
                img = img.astype(np.float32)
                if spec.get("anim"):
                    img = fx.apply(img, spec["anim"], t - s["start"], t)
                lay.append((img, depth))
            fr = L.composite(lay, lt, s["move"], W, H, s.get("cam"))
            for p in s.get("_screen_particles", []):
                p.draw(fr, t)
            return fr
        src = fx.apply(imgs[i], s["anim"], t - s["start"], t) if s.get("anim") else imgs[i]
        return camera(src, lt, s["move"]).astype(np.float32)

    for i, s in enumerate(scenes):
        for l in s.get("layers", []):
            if l.get("anim"): fx.build_particles(l["anim"], 300 + i)
        if s.get("screen_particles"):
            s["_screen_particles"] = [fx.Particles(k, n, 500 + i * 7 + j, tuple(r)) for j, (k, n, r) in enumerate(s["screen_particles"])]
    for fi in range(n):
        t = fi / FPS
        idx = max(i for i, s in enumerate(scenes) if s["start"] <= t + 1e-6) if t >= scenes[0]["start"] else 0
        s = scenes[idx]
        fr = shot(idx, t)
        if idx > 0 and t - s["start"] < XF:
            prev = shot(idx - 1, t)
            a = ease((t - s["start"]) / XF)
            fr = prev * (1 - a) + fr * a
        fr = np.clip(fr * tex * vig, 0, 255).astype(np.uint8)
        ch = next((c for c in chunks if c["s"] - 0.05 <= t <= c["e"]), None)
        fr = draw_subtitle(fr, ch, t, keywords, plan["handle"])
        fr = draw_overlay(fr, t, dur, plan.get("hook"), plan.get("cta"))
        enc.stdin.write(fr.tobytes())
    enc.stdin.close(); enc.wait()
    # mux: original audio stream copied bit-for-bit
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", plan["video_only"], "-i", plan["source"],
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
                    "-movflags", "+faststart", plan["output"]], check=True)
    print("done", plan["output"])

if __name__ == "__main__":
    main(sys.argv[1])
