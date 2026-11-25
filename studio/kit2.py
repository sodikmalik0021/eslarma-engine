"""Kit v2: richer storybook-watercolor drawing (bashar.uz-level detail) — trees, perspective streets, crowds, local props,
plus a watercolor post-process for rendered layers."""
import math, random, subprocess
import numpy as np, cv2
from scenes import INK, SW, SH, poly, rect, man, woman
from car2 import car_defs, sedan34
from car3d import car3d

PAL = dict(leaf=["#7f9a5b", "#93ad6a", "#a9bf7d", "#6c8a4e"], trunk="#7a6352", wall=["#ebe4d6", "#e2d8c6", "#d8cdb9"],
           roof="#b77a5c", road="#c9c3b8", side="#ddd6c9", coat="#3f5270", sky_day="#dfe6e3")

def tree(x, y, s=1.0, seed=0, n=34):
    r = random.Random(seed); g = ""
    g += f'<path d="M{x-7*s},{y} L{x-4*s},{y-150*s} L{x+4*s},{y-150*s} L{x+8*s},{y}z" fill="{PAL["trunk"]}" stroke="{INK}" stroke-width="{1.4}"/>'
    for k in range(3):
        bx = x + r.uniform(-30, 30) * s
        g += f'<path d="M{x},{y-110*s} Q{(x+bx)/2},{y-150*s} {bx},{y-185*s}" stroke="{PAL["trunk"]}" stroke-width="{4*s}" fill="none"/>'
    blobs = []
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0, 1) ** 0.6
        bx = x + math.cos(a) * 85 * s * d; by = y - 200 * s + math.sin(a) * 70 * s * d
        rr = r.uniform(20, 36) * s; blobs.append((by, bx, rr))
    for by, bx, rr in sorted(blobs):  # back to front
        shade = 0 if by < y - 215 * s and bx < x else (3 if by > y - 180 * s else r.choice([1, 2]))
        g += f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{rr:.1f}" fill="{PAL["leaf"][shade]}" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.45"/>'
    for k in range(10):  # leaf highlights
        bx = x + r.uniform(-70, 40) * s; by = y - 200 * s + r.uniform(-60, 10) * s
        g += f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{7*s:.1f}" ry="{4*s:.1f}" fill="#c4d39a" opacity="0.8"/>'
    return f'<ellipse cx="{x}" cy="{y+3*s}" rx="{70*s}" ry="{10*s}" fill="#000" opacity="0.10"/>' + g

def facade(x, y, w, h, col, floors=3, cols=4, door=True, columns=False):
    g = rect(x, y - h, w, h, col, sw=1.6) + rect(x - 6, y - h - 14, w + 12, 16, "#cfc4b2", sw=1.4)
    fh = h / floors
    for f in range(floors):
        for c in range(cols):
            wx = x + w * (c + 0.5) / cols - w / cols * 0.22; wy = y - h + f * fh + fh * 0.25
            g += rect(wx, wy, w / cols * 0.44, fh * 0.5, "#8fa3b5", sw=1.2) + f'<line x1="{wx}" y1="{wy+fh*0.25}" x2="{wx+w/cols*0.44}" y2="{wy+fh*0.25}" stroke="{INK}" stroke-width="0.8"/>'
    if columns:
        for c in range(cols + 1):
            cx = x + w * c / cols; g += rect(cx - 9, y - h * 0.72, 18, h * 0.72, "#f3eee4", sw=1.2)
    if door: g += rect(x + w / 2 - 26, y - 110, 52, 110, "#6b5545", sw=1.4)
    return g

def street(vx, vy, seed=1):
    """One-point perspective street: road, sidewalks, building rows and tree lines."""
    r = random.Random(seed); g = ""
    g += poly([(0, vy), (SW, vy), (SW, SH), (0, SH)], PAL["side"], sw=0)
    g += poly([(SW * 0.18, SH), (SW * 0.82, SH), (vx + 14, vy), (vx - 14, vy)], PAL["road"], sw=1.2)
    for k in range(9):  # receding buildings both sides
        t0, t1 = (k / 9) ** 1.8, ((k + 1) / 9) ** 1.8
        for side in (-1, 1):
            xa = vx + side * (40 + 640 * (1 - t0)); xb = vx + side * (40 + 640 * (1 - t1))
            ya, yb = vy + (SH - vy) * (1 - t0) * 0.55, vy + (SH - vy) * (1 - t1) * 0.55
            ha, hb = 900 * (1 - t0) + 60, 900 * (1 - t1) + 60
            col = r.choice(PAL["wall"])
            g += poly([(xa, ya), (xb, yb), (xb, yb - hb), (xa, ya - ha)], col, sw=1.1)
            for wv in range(4):  # window rows in perspective
                fy0, fy1 = 0.18 + wv * 0.2, 0.30 + wv * 0.2
                for c in range(2):
                    u0, u1 = 0.18 + c * 0.42, 0.42 + c * 0.42
                    px = lambda u: xa + (xb - xa) * u
                    pyb = lambda u, f: (ya + (yb - ya) * u) - (ha + (hb - ha) * u) * f
                    q = [(px(u0), pyb(u0, fy0)), (px(u1), pyb(u1, fy0)), (px(u1), pyb(u1, fy1)), (px(u0), pyb(u0, fy1))]
                    g += poly(q, "#93a7b8", sw=0.8)
            g += f'<line x1="{xa:.0f}" y1="{ya:.0f}" x2="{xa:.0f}" y2="{ya-ha:.0f}" stroke="#a7a093" stroke-width="1.2"/>'
    for k in range(7):
        t = (k / 7) ** 1.6
        for side in (-1, 1):
            tx = vx + side * (60 + 520 * (1 - t)); ty = vy + (SH - vy) * (1 - t) * 0.62
            g += tree(tx, ty, 0.35 + 1.5 * (1 - t), seed=seed * 10 + k * 2 + (side > 0))
    return g

def crowd(x0, y0, x1, y1, n, s0=0.35, s1=0.55, seed=3, mix=0.5, coat="#e8e3d8"):
    r = random.Random(seed); pts = sorted((r.uniform(y0, y1), r.uniform(x0, x1)) for _ in range(n)); g = ""
    for y, x in pts:
        s = s0 + (s1 - s0) * (y - y0) / max(y1 - y0, 1)
        g += man(x, y, s, back=True, walk=r.uniform(-0.8, 0.8), coat=r.choice([coat, "#556078", "#6b6f78"])) if r.random() > mix * 0.3 else woman(x, y, s)
    return g

def sedan(x, y, s=1.0, col="#f2efe8", ribbon=False):
    g = f'<ellipse cx="{x}" cy="{y+4*s}" rx="{150*s}" ry="{14*s}" fill="#000" opacity="0.15"/>'
    g += f'<path d="M{x-150*s},{y-25*s} q0,{-40*s} {40*s},{-48*s} l{40*s},{-46*s} q{70*s},{-12*s} {140*s},0 l{40*s},{46*s} q{40*s},{8*s} {40*s},{48*s} l0,{25*s}z" fill="{col}" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M{x-60*s},{y-73*s} l{30*s},{-36*s} q{60*s},{-9*s} {120*s},0 l{30*s},{36*s}z" fill="#9db1c4" stroke="{INK}" stroke-width="1.5"/>'
    g += rect(x - 140 * s, y - 42 * s, 26 * s, 12 * s, "#f6e7a8", sw=1) + rect(x + 114 * s, y - 42 * s, 26 * s, 12 * s, "#f6e7a8", sw=1)
    for wx in (-95, 95):
        g += f'<circle cx="{x+wx*s}" cy="{y-12*s}" r="{24*s}" fill="#2f2f36" stroke="{INK}" stroke-width="1.5"/><circle cx="{x+wx*s}" cy="{y-12*s}" r="{10*s}" fill="#b9bcc4"/>'
    if ribbon:
        g += f'<path d="M{x-60*s},{y-73*s} L{x+60*s},{y-30*s}" stroke="#d24b5a" stroke-width="{5*s}"/>'
        for k in range(5): g += f'<circle cx="{x-30*s+k*14*s}" cy="{y-112*s}" r="{8*s}" fill="#d24b5a" stroke="{INK}" stroke-width="0.8"/>'
    return g

def karnay(x, y, s=1.0, ang=-35):
    a = math.radians(ang); L = 260 * s
    ex, ey = x + math.cos(a) * L, y + math.sin(a) * L
    g = man(x, y + 230 * s, s * 0.8, back=False, coat="#3f5270")
    g += f'<line x1="{x}" y1="{y}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#c99a3e" stroke-width="{7*s}" stroke-linecap="round"/>'
    g += f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="{16*s}" ry="{9*s}" fill="#e0b55a" stroke="{INK}" stroke-width="1.2" transform="rotate({ang} {ex:.1f} {ey:.1f})"/>'
    return g

def brick_wall(x, y, w, h, tilt=0.0, seed=4):
    r = random.Random(seed); g = ""; bh = 26; bw = 60
    for row in range(int(h / bh)):
        off = (row % 2) * bw / 2; yy = y - (row + 1) * bh; dx = tilt * row * bh
        for c in range(-1, int(w / bw) + 1):
            bx = x + c * bw + off + dx
            if bx < x + dx - 1 or bx + bw > x + w + dx + 1: continue
            g += rect(bx, yy, bw - 3, bh - 3, r.choice(["#b9614a", "#c46f55", "#ad5843", "#c97c62"]), sw=0.9)
    return g

def teapot(x, y, s=1.0):
    return (f'<ellipse cx="{x}" cy="{y-28*s}" rx="{34*s}" ry="{28*s}" fill="#f4f1ea" stroke="{INK}" stroke-width="1.5"/>'
            f'<path d="M{x+30*s},{y-34*s} q{28*s},{-6*s} {38*s},{-26*s}" stroke="{INK}" stroke-width="{5*s}" fill="none"/>'
            f'<path d="M{x-32*s},{y-40*s} q{-24*s},{4*s} {-16*s},{24*s}" stroke="{INK}" stroke-width="{3*s}" fill="none"/>'
            f'<ellipse cx="{x}" cy="{y-56*s}" rx="{12*s}" ry="{5*s}" fill="#5c7fa3" stroke="{INK}" stroke-width="1"/>'
            f'<path d="M{x-28*s},{y-30*s} q{28*s},{12*s} {56*s},0" stroke="#5c7fa3" stroke-width="{3*s}" fill="none"/>')

def watercolor_post(png_in, png_out=None, seed=5, strength=1.0):
    """Watercolor look for a rendered RGBA layer: pigment granulation, darker wet edges, soft bleed, paper grain."""
    im = cv2.imread(png_in, cv2.IMREAD_UNCHANGED).astype(np.float32)
    if im.shape[2] == 3: im = np.dstack([im, np.full(im.shape[:2], 255, np.float32)])
    rgb, a = im[..., :3], im[..., 3:4] / 255
    rng = np.random.default_rng(seed)
    h, w = rgb.shape[:2]
    gran = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.3)
    blot = cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (h // 24, w // 24)).astype(np.float32), (0, 0), 1.5), (w, h))
    bleed = cv2.GaussianBlur(rgb, (0, 0), 2.2)
    out = rgb * 0.7 + bleed * 0.3
    lum = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    edges = cv2.GaussianBlur(cv2.Canny(lum.astype(np.uint8), 30, 90).astype(np.float32) / 255, (0, 0), 1.6)
    out *= (1 - 0.10 * strength * edges[..., None])
    out *= (1 + 0.045 * strength * gran[..., None] + 0.025 * strength * blot[..., None] / (blot.std() + 1e-6))
    out = np.clip(out, 0, 255)
    cv2.imwrite(png_out or png_in, np.dstack([out, a * 255]).astype(np.uint8))

_car_n = [0]
def car(x, y, s=1.0, yaw=24, side=1, **kw):
    """Perspective-correct sedan (3D model projected): front + one side always meet properly.
    side=1 shows the car's left side (car on the right of the frame), side=-1 the right side."""
    return car3d(x, y, s, yaw, side, **kw)
