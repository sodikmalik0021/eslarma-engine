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
        if len(cur) >= 3 or end_punct or gap or nxt is None or (len(cur) >= 2 and len(" ".join(x["w"] for x in cur)) > 18):
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

def draw_subtitle(frame, chunk, t, keywords, handle):
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    f = font(40)
    y = int(H * 0.775)
    if chunk:
        fade_in = min(1, (t - chunk["s"]) / 0.18)
        fade_out = min(1, (chunk["e"] - t) / 0.15)
        a = max(0, min(fade_in, fade_out))
        tokens = [w["w"] for w in chunk["words"]]
        text = " ".join(tokens)
        tw = f.getlength(text)
        padx, ph = 44, 74
        bw = max(tw + 2 * padx, 420)
        x0 = int(W / 2 - bw / 2)
        # soft white glow pill
        pill = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pill).rounded_rectangle([x0, y - ph // 2, x0 + bw, y + ph // 2], radius=ph // 2, fill=int(215 * a))
        pill = pill.filter(ImageFilter.GaussianBlur(14))
        white = Image.new("RGB", (W, H), (250, 248, 242))
        img = Image.composite(white, img, pill)
        d = ImageDraw.Draw(img)
        cx = W / 2 - tw / 2
        for w in chunk["words"]:
            spoken = t >= w["s"] - 0.03
            key = w["w"].strip(".,!?:;«»\"'").lower() in keywords
            col = GOLD if key and spoken else GREEN
            alpha = a if spoken else 0.0  # words appear one by one, in sync with speech
            base = np.array(img.getpixel((int(cx), y)))
            c = tuple(int(base[k] + (col[k] - base[k]) * alpha) for k in range(3))
            d.text((cx, y), w["w"], font=f, fill=c, anchor="lm")
            cx += f.getlength(w["w"] + " ")
    d = ImageDraw.Draw(img)
    d.text((W / 2, y + 72), handle, font=font(26), fill=(70, 96, 80), anchor="mm")
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
        f = ImageFont.truetype(HOOK_FONT, int(84 * pop))
        lines = wrap(hook, f, W * 0.8)
        lh = int(100 * pop); y0 = int(H * 0.30 - lh * len(lines) / 2)
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

def main(plan_path):
    plan = json.load(open(plan_path))
    dur = plan["duration"]
    scenes = plan["scenes"]
    imgs = []
    for s in scenes:
        if s.get("layers"):
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
