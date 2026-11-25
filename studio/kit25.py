"""2.5D kit (no side effects on import): reusable depth layers + literal props for word-matched shots.
Same palette/look as the approved sample (make_l25.py). Figures: scenes.man / scenes.woman only (no fingers)."""
import math, os, random
from scenes import *
from layers import svg_layer, render_layer

OUT = "l25"

def R(name, body, bg=None):
    os.makedirs(OUT, exist_ok=True)
    p = f"{OUT}/{name}.png"
    render_layer(svg_layer(body, bg=bg), p)
    return p

def L(png, depth, **anim):
    d = {"png": png, "depth": depth}
    if anim: d["anim"] = anim
    return d

# ---------------- skies ----------------
# Sky = 2 layers: opaque gradient (+sun/moon/stars, static) and a transparent cloud layer that drifts.
# (Drifting the sun together with the clouds cut the sun glow into rectangles — fixed 2026-11-19.)
def sky_layers(name, kind="nightsky", seed=1, sun=None, moon=None, stars=False):
    b = ""
    if sun: b += f'<circle cx="{sun[0]}" cy="{sun[1]}" r="420" fill="url(#glow)"/><circle cx="{sun[0]}" cy="{sun[1]}" r="85" fill="#ffe3a1" stroke="{INK}" stroke-width="2"/>'
    if moon: b += f'<circle cx="{moon[0]}" cy="{moon[1]}" r="260" fill="url(#glow)" opacity="0.6"/><path d="M{moon[0]-40},{moon[1]-70} a80,80 0 1 0 70,120 a62,62 0 1 1 -70,-120z" fill="#f6e7b8" stroke="{INK}" stroke-width="2"/>'
    if stars:
        r = random.Random(seed)
        for _ in range(40): b += f'<circle cx="{r.uniform(0,SW)}" cy="{r.uniform(0,900)}" r="{r.uniform(1.5,3.5)}" fill="#f6eed5" opacity="0.8"/>'
    col = "#efe2d0" if kind == "dawnsky" else ("#f4f4f2" if kind == "daysky" else "#d9d6e6")
    c = clouds(300, 5, col=col, seed=seed) + clouds(560, 4, col=col, seed=seed + 7, op=0.4)
    return R(name + "s", b, bg=kind), R(name + "c", c)

def sky_anim(a, speed=12):
    return [L(a[0], 0.15), L(a[1], 0.25, clouds=[speed, [0, 900]])]

# ---------------- far layers ----------------
def hills(y, col="#b9aa9f", col2="#a39a92"):
    return (f'<path d="M0,{y} q300,-110 620,-35 q330,65 622,-55 L{SW},{y+600} L0,{y+600}z" fill="{col}" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M0,{y+120} q260,-60 560,0 q360,70 682,-30 L{SW},{y+700} L0,{y+700}z" fill="{col2}" stroke="{INK}" stroke-width="2"/>')

def village(y, seed=2, scale=1.0, lit=True):
    r = random.Random(seed); g = ""
    for i in range(16):
        x = r.uniform(-40, SW); w = r.uniform(60, 120)*scale; h = r.uniform(50, 90)*scale
        yy = y + r.uniform(-20, 20)
        g += rect(x, yy - h, w, h, r.choice([WALL, WALL2, "#e2dbd0"]), sw=1.5)
        if lit and r.random() < 0.5: g += f'<rect x="{x+w*0.4}" y="{yy-h*0.6}" width="{w*0.18}" height="{h*0.25}" fill="#ffd98a" stroke="{INK}" stroke-width="1"/>'
    return g

def dome(x, y, s=1.0, minaret=True):
    g = rect(x-200*s, y-260*s, 400*s, 260*s, WALL)
    g += f'<path d="M{x-170*s},{y-260*s} a{170*s},{190*s} 0 0 1 {340*s},0z" fill="#dcd3c6" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<line x1="{x}" y1="{y-450*s}" x2="{x}" y2="{y-520*s}" stroke="{INK}" stroke-width="3"/><circle cx="{x}" cy="{y-530*s}" r="{10*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    if minaret:
        g += rect(x+260*s, y-620*s, 70*s, 620*s, WALL2) + f'<path d="M{x+255*s},{y-620*s} l{40*s},{-90*s} l{40*s},{90*s}z" fill="#dcd3c6" stroke="{INK}" stroke-width="2"/>'
    for k in (-110, 0, 110):
        g += f'<path d="M{x+k*s-30*s},{y} l0,{-110*s} a{30*s},{30*s} 0 0 1 {60*s},0 l0,{110*s}z" fill="#ffe3a1" stroke="{INK}" stroke-width="2"/>'
    return g

# ---------------- grounds / sets ----------------
def ground(y, col="#d6cfc6"):
    return poly([(0, y), (SW, y), (SW, SH), (0, SH)], col, sw=1.5)

def house_row(y, seed=0, doors=True, lit=True):
    """row of cream houses with blue doors standing on ground line y."""
    r = random.Random(seed); g = ""; x = -30
    while x < SW:
        w = r.uniform(260, 380); h = r.uniform(520, 700)
        g += rect(x, y - h, w, h, r.choice([WALL, WALL2, "#e2dbd0"]))
        g += window(x + 30, y - h + 70, 80, 120)
        if doors: g += door(x + w*0.5, y - 330, 120, 330, r.choice([DOOR, WOOD, DOOR]))
        if lit: g += lantern(x + w*0.5 - 40, y - 400, 0.7)
        g += pot(x + w*0.5 + 150, y, 0.8, seed=int(x))
        x += w
    return g

def road(vx, vy, wb=1100, col="#7b7787"):
    g = poly([(SW/2-wb/2, SH), (SW/2+wb/2, SH), (vx+18, vy), (vx-18, vy)], col)
    g += f'<path d="M{SW/2},{SH} L{vx},{vy}" stroke="#e9d9a0" stroke-width="10" stroke-dasharray="60 50" opacity="0.8"/>'
    return g

def dirt_road(vx, vy, wb=900):
    return poly([(SW/2-wb/2, SH), (SW/2+wb/2, SH), (vx+14, vy), (vx-14, vy)], "#cbb79a", sw=1.8)

def room_wall(col="#e9e2d6", floor=1650, sky="dawnsky", win=True):
    b = poly([(0,0),(SW,0),(SW,SH),(0,SH)], col, sw=0) + poly([(0,floor),(SW,floor),(SW,SH),(0,SH)], "#a9786a")
    if win:
        b += f'<path d="M820,1050 l0,-420 a170,170 0 0 1 340,0 l0,420z" fill="url(#{sky})" stroke="{INK}" stroke-width="5"/>'
        b += f'<line x1="990" y1="460" x2="990" y2="1050" stroke="{INK}" stroke-width="4"/>'
    return b

# ---------------- foreground framing ----------------
def fg_vines(side="left", seed=5, flowers=True):
    r = random.Random(seed); g = ""
    xs = (-20, 260) if side == "left" else (SW - 260, SW + 20)
    for _ in range(26):
        x, y = r.uniform(*xs), r.uniform(-20, 520)
        g += f'<ellipse cx="{x}" cy="{y}" rx="34" ry="16" fill="#5f8a55" stroke="{INK}" stroke-width="1.5" transform="rotate({r.uniform(-60,60)} {x} {y})"/>'
    if flowers:
        for _ in range(8):
            x, y = r.uniform(xs[0] + 40, xs[1] - 20), r.uniform(40, 500)
            g += f'<circle cx="{x}" cy="{y}" r="13" fill="#d04a7a" stroke="{INK}" stroke-width="1.2"/>'
    return g

def fg_bush(x0, x1, y0, y1, seed=9):
    r = random.Random(seed); g = ""
    for _ in range(30):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        g += f'<ellipse cx="{x}" cy="{y}" rx="40" ry="18" fill="#5f8a55" stroke="{INK}" stroke-width="1.5" transform="rotate({r.uniform(-70,70)} {x} {y})"/>'
    for _ in range(10):
        x, y = r.uniform(x0 + 30, x1 - 30), r.uniform(y0 + 20, y1 - 30)
        g += f'<circle cx="{x}" cy="{y}" r="16" fill="{r.choice(["#d04a7a","#f2a1b8","#c43d55"])}" stroke="{INK}" stroke-width="1.2"/>'
    return g

def fg_arch(col=WALL2):
    """stone arch edges framing the shot (foreground)."""
    return (f'<path d="M0,0 L0,{SH} L120,{SH} L120,700 Q120,260 {SW/2},200 Q{SW-120},260 {SW-120},700 L{SW-120},{SH} L{SW},{SH} L{SW},0z" '
            f'fill="{col}" stroke="{INK}" stroke-width="3"/>')

def fg_frame(seed=1):
    return fg_vines("left", seed) + pot(110, 2190, 2.6, seed + 7) + pot(1150, 2200, 2.4, seed + 8)

# ---------------- props ----------------
def bread(x, y, s=1.0):
    """round Uzbek non: golden disc with stamped centre."""
    g = f'<ellipse cx="{x}" cy="{y}" rx="{70*s}" ry="{30*s}" fill="#d9a35b" stroke="{INK}" stroke-width="2"/>'
    g += f'<ellipse cx="{x}" cy="{y-2*s}" rx="{38*s}" ry="{15*s}" fill="#e8c48a" stroke="{INK}" stroke-width="1.2"/>'
    for k in range(6):
        a = k * math.pi / 3
        g += f'<circle cx="{x+22*s*math.cos(a)}" cy="{y-2*s+8*s*math.sin(a)}" r="{2.5*s}" fill="#8a6a55"/>'
    return g

def bowl(x, y, s=1.0, col="#6d86ab", food="#c98b4f"):
    return (f'<ellipse cx="{x}" cy="{y-18*s}" rx="{44*s}" ry="{12*s}" fill="{food}" stroke="{INK}" stroke-width="1.5"/>'
            f'<path d="M{x-46*s},{y-18*s} q{46*s},{50*s} {92*s},0z" fill="{col}" stroke="{INK}" stroke-width="2"/>')

def teapot(x, y, s=1.0):
    g = f'<path d="M{x-40*s},{y} q-10,{-70*s} {40*s},{-75*s} q{50*s},{5*s} {40*s},{75*s}z" fill="#e8e6e0" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M{x+38*s},{y-40*s} q{30*s},{-5*s} {40*s},{-35*s}" stroke="{INK}" stroke-width="{6*s}" fill="none"/>'
    g += f'<circle cx="{x}" cy="{y-80*s}" r="{8*s}" fill="#6d86ab" stroke="{INK}" stroke-width="1.5"/>'
    return g

def dastarxon(cx, cy, w=760, h=260, items=True):
    g = f'<ellipse cx="{cx}" cy="{cy}" rx="{w/2}" ry="{h/2}" fill="#b4483f" stroke="{INK}" stroke-width="3"/>'
    g += f'<ellipse cx="{cx}" cy="{cy}" rx="{w/2-30}" ry="{h/2-18}" fill="none" stroke="#e2b84f" stroke-width="4" stroke-dasharray="14 10"/>'
    if items:
        g += bread(cx - 170, cy - 10, 1.1) + bread(cx + 180, cy + 5, 1.0) + bowl(cx, cy + 20, 1.2)
        g += teapot(cx - 20, cy - 40, 0.9) + bowl(cx + 300, cy - 30, 0.7, "#e8e6e0", "#d04a7a") + bowl(cx - 310, cy - 20, 0.7, "#e8e6e0", "#5f8a55")
    return g

def calendar(x, y, s=1.0, title="JUMA", crossed=6):
    """wall calendar: header + 7 day boxes, first `crossed` boxes struck through, last one highlighted."""
    w, h = 420 * s, 360 * s
    g = rect(x, y, w, h, "#f6f1e6", rx=10) + rect(x, y, w, 80*s, "#3f6b4c", rx=10)
    g += f'<text x="{x+w/2}" y="{y+56*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{46*s}" fill="#f6e7b8" text-anchor="middle">{title}</text>'
    for k in range(7):
        bx = x + 22*s + (k % 4) * 96*s; by = y + 110*s + (k // 4) * 115*s
        last = k == 6
        g += rect(bx, by, 80*s, 95*s, "#e2b84f" if last else "#ece6dc", sw=1.8)
        g += f'<text x="{bx+40*s}" y="{by+62*s}" font-family="Inter, sans-serif" font-weight="700" font-size="{38*s}" fill="{INK}" text-anchor="middle">{k+1}</text>'
        if k < crossed:
            g += f'<path d="M{bx+10*s},{by+10*s} L{bx+70*s},{by+85*s} M{bx+70*s},{by+10*s} L{bx+10*s},{by+85*s}" stroke="#b4483f" stroke-width="{5*s}"/>'
    g += f'<circle cx="{x+w/2}" cy="{y-14*s}" r="{8*s}" fill="{INK}"/>'
    return g

def blossom_tree(x, y, s=1.0, seed=3, col=("#f2a1b8", "#f6c6d4", "#e06b8f")):
    r = random.Random(seed)
    g = f'<path d="M{x-28*s},{y} q{10*s},{-220*s} {-10*s},{-420*s} l{38*s},0 q{-10*s},{200*s} {30*s},{420*s}z" fill="{WOOD}" stroke="{INK}" stroke-width="2.5"/>'
    for bx, by, bw in ((-140, -520, 26), (150, -560, 24), (-60, -640, 20), (90, -470, 22)):
        g += f'<path d="M{x}, {y-400*s} Q{x+bx*s*0.5},{y+(by+60)*s} {x+bx*s},{y+by*s}" stroke="{WOOD}" stroke-width="{bw*s*0.6}" fill="none" stroke-linecap="round"/>'
    for _ in range(170):
        a = r.uniform(0, 2*math.pi); d = r.uniform(0, 1) ** 0.6
        px, py = x + math.cos(a) * 330*s*d, y - 560*s + math.sin(a) * 210*s*d
        g += f'<circle cx="{px}" cy="{py}" r="{r.uniform(10,19)*s}" fill="{r.choice(col)}" stroke="{INK}" stroke-width="1"/>'
    return g

def snow_cap(x, y, w):
    return f'<path d="M{x-8},{y} q{w*0.25},{-28} {w*0.5},{-6} q{w*0.25},{-24} {w+16},{4} l0,14 l{-w-16},0z" fill="#fbfbf8" stroke="{INK}" stroke-width="1.5"/>'

def clock_face(x, y, r):
    g = f'<circle cx="{x}" cy="{y}" r="{r+18}" fill="#8a6a55" stroke="{INK}" stroke-width="3"/><circle cx="{x}" cy="{y}" r="{r}" fill="#f6f1e6" stroke="{INK}" stroke-width="2.5"/>'
    for k in range(12):
        a = k * math.pi / 6
        g += f'<line x1="{x+0.82*r*math.cos(a)}" y1="{y+0.82*r*math.sin(a)}" x2="{x+0.95*r*math.cos(a)}" y2="{y+0.95*r*math.sin(a)}" stroke="{INK}" stroke-width="{5 if k%3==0 else 2.5}"/>'
    return g

def clock_tower(x, y, s=1.0):
    """tower standing on y; returns (svg, (cx, cy, r)) for the animated hands."""
    w, h = 300*s, 1050*s
    g = rect(x - w/2, y - h, w, h, WALL2)
    g += f'<path d="M{x-w/2-20},{y-h} L{x},{y-h-230*s} L{x+w/2+20},{y-h}z" fill="#6d86ab" stroke="{INK}" stroke-width="2.5"/>'
    g += door(x - 60*s, y - 300*s, 120*s, 300*s, WOOD)
    cy = y - h + 200*s; r = 105*s
    return g + clock_face(x, cy, r), (x, cy, r)

def phone(x, y, s=1.0, lit=True):
    """smartphone held in a simple mitten hand (no fingers)."""
    g = f'<circle cx="{x}" cy="{y}" r="{230*s}" fill="url(#glow)" opacity="0.7"/>' if lit else ""
    g += rect(x - 85*s, y - 160*s, 170*s, 320*s, "#2e2a3a", rx=int(26*s), sw=3)
    g += rect(x - 70*s, y - 135*s, 140*s, 255*s, "#9fc6e6" if lit else "#4d5770", rx=int(10*s), sw=1.5)
    for k in range(3): g += rect(x - 52*s, y - 110*s + k*62*s, 104*s, 44*s, "#e9f2f8", rx=int(8*s), sw=1)
    g += f'<path d="M{x-110*s},{y+40*s} q{-10*s},{150*s} {70*s},{200*s} l{120*s},0 q{60*s},{-60*s} {30*s},{-190*s} q{-60*s},{20*s} {-110*s},{10*s}z" fill="#d9a98a" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<path d="M{x-70*s},{y+240*s} l{-30*s},{200*s} l{200*s},0 l{-20*s},{-200*s}z" fill="#556078" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<ellipse cx="{x-88*s}" cy="{y+10*s}" rx="{24*s}" ry="{58*s}" fill="#d9a98a" stroke="{INK}" stroke-width="2.5" transform="rotate(-12 {x-88*s} {y+10*s})"/>'  # thumb over the edge
    return g

def cart(x, y, s=1.0):
    """old wooden arava with two big wheels (no car)."""
    g = poly([(x-170*s, y-170*s), (x+170*s, y-170*s), (x+150*s, y-90*s), (x-150*s, y-90*s)], WOOD)
    g += f'<line x1="{x+150*s}" y1="{y-130*s}" x2="{x+330*s}" y2="{y-60*s}" stroke="{INK}" stroke-width="{8*s}"/>'
    for wx in (-90, 90):
        g += f'<circle cx="{x+wx*s}" cy="{y-70*s}" r="{70*s}" fill="none" stroke="{INK}" stroke-width="{8*s}"/>'
        for k in range(6):
            a = k * math.pi / 3
            g += f'<line x1="{x+wx*s}" y1="{y-70*s}" x2="{x+wx*s+66*s*math.cos(a)}" y2="{y-70*s+66*s*math.sin(a)}" stroke="{WOOD}" stroke-width="{5*s}"/>'
    return g

def wheat(x0, x1, y0, y1, seed=4):
    r = random.Random(seed); g = poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "#d9b56a", sw=0)
    for _ in range(220):
        x = r.uniform(x0, x1); y = r.uniform(y0 + 20, y1); hh = r.uniform(40, 90) * (0.6 + (y - y0) / (y1 - y0))
        g += f'<line x1="{x}" y1="{y}" x2="{x+r.uniform(-8,8)}" y2="{y-hh}" stroke="#a9853f" stroke-width="2"/><ellipse cx="{x}" cy="{y-hh}" rx="5" ry="13" fill="#e8c46a" stroke="#8a6a3a" stroke-width="1"/>'
    return g

def hoe(x, y, s=1.0):
    return (f'<line x1="{x}" y1="{y}" x2="{x+120*s}" y2="{y-260*s}" stroke="{WOOD}" stroke-width="{10*s}" stroke-linecap="round"/>'
            + poly([(x-30*s, y-5*s), (x+30*s, y+5*s), (x+20*s, y+40*s), (x-40*s, y+30*s)], "#7a7f93"))

def wedding_arch(x, y, s=1.0):
    g = f'<path d="M{x-260*s},{y} L{x-260*s},{y-520*s} Q{x},{y-760*s} {x+260*s},{y-520*s} L{x+260*s},{y}" fill="none" stroke="{WOOD}" stroke-width="{26*s}"/>'
    r = random.Random(11); pts = []
    for k in range(12): pts.append((x - 260*s, y - 80*s - k * 40*s)); pts.append((x + 260*s, y - 80*s - k * 40*s))
    for k in range(17):
        t = k / 16; px = (1-t)**2*(x-260*s) + 2*(1-t)*t*x + t*t*(x+260*s); py = (1-t)**2*(y-520*s) + 2*(1-t)*t*(y-760*s) + t*t*(y-520*s)
        pts.append((px, py))
    for px, py in pts:
        g += f'<circle cx="{px+r.uniform(-14,14)}" cy="{py+r.uniform(-14,14)}" r="{r.uniform(14,22)*s}" fill="{r.choice(["#f2a1b8","#f4f1ea","#d04a7a","#5f8a55"])}" stroke="{INK}" stroke-width="1"/>'
    return g

def institute(x, y, s=1.0, label="INSTITUT"):
    w, h = 900*s, 560*s
    g = rect(x - w/2, y - h, w, h, WALL)
    g += poly([(x - w/2 - 30, y - h), (x + w/2 + 30, y - h), (x, y - h - 200*s)], WALL2)
    g += f'<text x="{x}" y="{y-h+60*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{48*s}" fill="{INK}" text-anchor="middle">{label}</text>'
    for k in range(6):
        cx = x - w/2 + 90*s + k * 144*s
        g += rect(cx - 22*s, y - h + 90*s, 44*s, h - 130*s, "#f4f1ea", sw=2)
    g += rect(x - w/2 - 40, y - 40*s, w + 80, 40*s, WALL2)
    g += door(x - 70*s, y - 300*s, 140*s, 260*s, DOOR)
    return g

def grad_cap(x, y, s=1.0):
    return poly([(x-45*s, y), (x, y-18*s), (x+45*s, y), (x, y+18*s)], "#2e2a3a", sw=1.5) + f'<line x1="{x+30*s}" y1="{y+4*s}" x2="{x+36*s}" y2="{y+40*s}" stroke="#e2b84f" stroke-width="{3*s}"/>'

def workshop(x, y, w, label, col=DOOR, s=1.0):
    """a shop/workplace front with a signboard."""
    h = 640*s
    g = rect(x, y - h, w, h, WALL)
    g += rect(x + 20, y - h + 30, w - 40, 90*s, "#3f6b4c", rx=8)
    g += f'<text x="{x+w/2}" y="{y-h+92*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{min(52*s, (w-60)/max(len(label),1)*1.6)}" fill="#f6e7b8" text-anchor="middle">{label}</text>'
    g += door(x + w/2 - 70*s, y - 330*s, 140*s, 330*s, col)
    return g

def bed(x, y, s=1.0, person=True):
    g = rect(x - 330*s, y - 120*s, 660*s, 120*s, WOOD) + rect(x - 330*s, y - 300*s, 60*s, 300*s, WOOD) + rect(x + 270*s, y - 230*s, 60*s, 230*s, WOOD)
    g += rect(x - 300*s, y - 170*s, 600*s, 60*s, "#f4f1ea")
    if person:
        g += f'<ellipse cx="{x-200*s}" cy="{y-200*s}" rx="{38*s}" ry="{30*s}" fill="#d9a98a" stroke="{INK}" stroke-width="2"/>'
        g += f'<path d="M{x-238*s},{y-205*s} a{38*s},{26*s} 0 0 1 {76*s},0z" fill="#f4f1ea" stroke="{INK}" stroke-width="2"/>'
        g += f'<path d="M{x-160*s},{y-175*s} q{200*s},{-90*s} {440*s},{-20*s} l0,{40*s} l{-440*s},0z" fill="#6d86ab" stroke="{INK}" stroke-width="2.5"/>'
    else:
        g += f'<ellipse cx="{x-200*s}" cy="{y-190*s}" rx="{70*s}" ry="{28*s}" fill="#f4f1ea" stroke="{INK}" stroke-width="2"/>'
    return g

def broken_window(x, y, w=200, h=260):
    g = rect(x, y, w, h, "#4d5770")
    g += f'<path d="M{x+w*0.45},{y+h*0.4} l{-w*0.3},{-h*0.3} M{x+w*0.45},{y+h*0.4} l{w*0.4},{-h*0.25} M{x+w*0.45},{y+h*0.4} l{w*0.35},{h*0.45} M{x+w*0.45},{y+h*0.4} l{-w*0.35},{h*0.5}" stroke="#e9f2f8" stroke-width="3"/>'
    return g

def ball(x, y, s=1.0):
    return f'<circle cx="{x}" cy="{y}" r="{30*s}" fill="#e06b8f" stroke="{INK}" stroke-width="2"/><path d="M{x-30*s},{y} q{30*s},{-20*s} {60*s},0" stroke="#f4f1ea" stroke-width="{4*s}" fill="none"/>'

def cup_water(x, y, s=1.0):
    g = poly([(x-30*s,y-80*s),(x+30*s,y-80*s),(x+23*s,y),(x-23*s,y)], "#cfe0ec", sw=2*s)
    g += poly([(x-27*s,y-52*s),(x+27*s,y-52*s),(x+23*s,y),(x-23*s,y)], "#7fa7c9", sw=1.2*s)
    return g

def heart(x, y, s=1.0, col="#d04a7a"):
    return f'<path d="M{x},{y+60*s} C{x-120*s},{y-20*s} {x-60*s},{y-110*s} {x},{y-40*s} C{x+60*s},{y-110*s} {x+120*s},{y-20*s} {x},{y+60*s}z" fill="{col}" stroke="{INK}" stroke-width="2.5"/>'

def gift_box(x, y, s=1.0):
    g = rect(x - 90*s, y - 150*s, 180*s, 150*s, "#3f6b4c") + rect(x - 100*s, y - 190*s, 200*s, 45*s, "#4f7d5c")
    g += rect(x - 14*s, y - 190*s, 28*s, 190*s, "#e2b84f", sw=1.5)
    g += f'<path d="M{x},{y-190*s} q{-70*s},{-80*s} {-80*s},{-20*s} q{30*s},{20*s} {80*s},{20*s} q{70*s},{-80*s} {80*s},{-20*s} q{-30*s},{20*s} {-80*s},{20*s}z" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    return g

def quran_rehal(x, y, s=1.0):
    g = poly([(x-150*s, y), (x+150*s, y-120*s), (x+170*s, y-100*s), (x-130*s, y+20*s)], WOOD)
    g += poly([(x+150*s, y), (x-150*s, y-120*s), (x-170*s, y-100*s), (x+130*s, y+20*s)], "#7a5a47")
    g += poly([(x-140*s, y-110*s), (x, y-60*s), (x, y-200*s), (x-140*s, y-250*s)], "#f4efe4", sw=2)
    g += poly([(x+140*s, y-110*s), (x, y-60*s), (x, y-200*s), (x+140*s, y-250*s)], "#f4efe4", sw=2)
    for k in range(5):
        g += f'<line x1="{x-120*s}" y1="{y-215*s+k*24*s}" x2="{x-20*s}" y2="{y-175*s+k*24*s}" stroke="#9a948a" stroke-width="{2*s}"/>'
        g += f'<line x1="{x+20*s}" y1="{y-175*s+k*24*s}" x2="{x+120*s}" y2="{y-215*s+k*24*s}" stroke="#9a948a" stroke-width="{2*s}"/>'
    return g

# ---------------- workshop props (reel 0008) ----------------
def workbench(x, y, w=700, s=1.0):
    g = rect(x - w/2, y - 200*s, w, 40*s, WOOD) + rect(x - w/2 + 30, y - 160*s, 34*s, 160*s, "#7a5a47") + rect(x + w/2 - 30 - 34*s, y - 160*s, 34*s, 160*s, "#7a5a47")
    return g

def planks(x, y, n=6, s=1.0):
    g = ""
    for k in range(n):
        g += rect(x + k * 14*s, y - 420*s + k * 6*s, 34*s, 420*s - k * 6*s, ["#c9a26b", "#b98d57", "#d6b27a"][k % 3], sw=1.6)
    return g

def logs(x, y, s=1.0):
    g = ""
    for row, n in enumerate((4, 3, 2)):
        for k in range(n):
            cx = x + (k - n / 2 + 0.5) * 92*s; cy = y - 46*s - row * 80*s
            g += f'<circle cx="{cx}" cy="{cy}" r="{46*s}" fill="#b98d57" stroke="{INK}" stroke-width="2"/><circle cx="{cx}" cy="{cy}" r="{24*s}" fill="none" stroke="#8a6a55" stroke-width="2"/>'
    return g

def drill(x, y, s=1.0, glow=False):
    """cordless power drill, side view, nose to the right; (x,y) = bottom of the handle."""
    g = f'<circle cx="{x+40*s}" cy="{y-150*s}" r="{230*s}" fill="url(#glow)"/>' if glow else ""
    g += rect(x - 50*s, y - 30*s, 120*s, 50*s, "#2e2a3a", rx=int(10*s), sw=2.5)                     # battery
    g += poly([(x - 30*s, y - 30*s), (x + 30*s, y - 30*s), (x + 45*s, y - 150*s), (x - 10*s, y - 150*s)], "#e2b84f", sw=2.5)  # grip
    g += rect(x - 70*s, y - 220*s, 210*s, 90*s, "#e2b84f", rx=int(30*s), sw=2.5)                     # body
    g += rect(x - 40*s, y - 205*s, 90*s, 60*s, "#2e2a3a", rx=int(14*s), sw=1.5)                      # motor vents panel
    for k in range(4): g += f'<line x1="{x-30*s+k*22*s}" y1="{y-198*s}" x2="{x-30*s+k*22*s}" y2="{y-152*s}" stroke="#7a7f93" stroke-width="{3*s}"/>'
    g += rect(x + 140*s, y - 200*s, 50*s, 50*s, "#3b3a48", rx=int(6*s), sw=2)                       # chuck
    g += poly([(x + 190*s, y - 182*s), (x + 300*s, y - 177*s), (x + 190*s, y - 168*s)], "#9aa0ad", sw=1.5)  # bit
    g += rect(x + 10*s, y - 128*s, 20*s, 26*s, "#2e2a3a", rx=int(4*s), sw=1.2)                      # trigger
    return g

def open_box(x, y, s=1.0):
    g = rect(x - 130*s, y - 150*s, 260*s, 150*s, "#c9a26b")
    g += poly([(x - 130*s, y - 150*s), (x - 200*s, y - 230*s), (x - 60*s, y - 230*s), (x, y - 150*s)], "#d6b27a", sw=2)
    g += poly([(x + 130*s, y - 150*s), (x + 200*s, y - 230*s), (x + 60*s, y - 230*s), (x, y - 150*s)], "#d6b27a", sw=2)
    g += f'<path d="M{x-100*s},{y-60*s} q{100*s},{-40*s} {200*s},0" stroke="#e2b84f" stroke-width="{10*s}" fill="none"/>'
    return g

def manual(x, y, s=1.0, icons=True):
    g = poly([(x-150*s,y),(x,y+25*s),(x,y-170*s),(x-150*s,y-195*s)], "#f4efe4", sw=2.5)
    g += poly([(x+150*s,y),(x,y+25*s),(x,y-170*s),(x+150*s,y-195*s)], "#f4efe4", sw=2.5)
    if icons:
        g += f'<circle cx="{x-75*s}" cy="{y-110*s}" r="{30*s}" fill="none" stroke="#3f6b4c" stroke-width="{4*s}"/><path d="M{x-90*s},{y-110*s} l{12*s},{14*s} l{24*s},{-26*s}" stroke="#3f6b4c" stroke-width="{4*s}" fill="none"/>'
        g += f'<path d="M{x+40*s},{y-140*s} l{40*s},0 l{-20*s},{40*s}z" fill="#e2b84f" stroke="{INK}" stroke-width="1.5"/>'
        for k in range(3):
            g += f'<line x1="{x+25*s}" y1="{y-80*s+k*22*s}" x2="{x+125*s}" y2="{y-70*s+k*22*s}" stroke="#9a948a" stroke-width="{3*s}"/>'
            g += f'<line x1="{x-125*s}" y1="{y-60*s+k*20*s}" x2="{x-25*s}" y2="{y-50*s+k*20*s}" stroke="#9a948a" stroke-width="{3*s}"/>'
    return g

def globe(x, y, s=1.0):
    g = f'<circle cx="{x}" cy="{y-120*s}" r="{80*s}" fill="#7fa7c9" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<path d="M{x-50*s},{y-170*s} q{30*s},{-10*s} {40*s},{20*s} q{-10*s},{30*s} {-40*s},{30*s}z M{x+10*s},{y-110*s} q{40*s},{-10*s} {50*s},{20*s} q{-20*s},{40*s} {-40*s},{30*s}z" fill="#5f8a55" stroke="{INK}" stroke-width="1.5"/>'
    g += f'<path d="M{x-90*s},{y-120*s} a{90*s},{90*s} 0 0 0 {180*s},0" fill="none" stroke="{WOOD}" stroke-width="{6*s}"/>'
    g += rect(x - 8*s, y - 30*s, 16*s, 30*s, WOOD) + rect(x - 60*s, y - 10*s, 120*s, 14*s, WOOD)
    return g

def factory(x, y, s=1.0, label="ZAVOD"):
    w, h = 900*s, 420*s
    g = ""
    for k, cx in enumerate((x - 280*s, x - 120*s)):
        g += rect(cx - 35*s, y - h - 380*s, 70*s, 380*s + h, WALL3)
        g += rect(cx - 35*s, y - h - 360*s, 70*s, 30*s, "#b4483f", sw=1.5)
    g += rect(x - w/2, y - h, w, h, WALL2)
    for k in range(4):
        g += poly([(x - w/2 + k*w/4, y - h), (x - w/2 + (k+1)*w/4, y - h), (x - w/2 + (k+1)*w/4, y - h - 110*s)], WALL3)
    g += rect(x - 260*s, y - h + 50*s, 520*s, 80*s, "#3f6b4c", rx=8)
    g += f'<text x="{x}" y="{y-h+108*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{54*s}" fill="#f6e7b8" text-anchor="middle">{label}</text>'
    for k in range(5): g += window(x - w/2 + 60*s + k * 170*s, y - h + 190*s, 90*s, 120*s, shut=False)
    g += door(x - 90*s, y - 160*s, 180*s, 160*s, "#7a7f93")
    return g

def smoke_puffs(x, y, s=1.0, n=5):
    return "".join(f'<circle cx="{x+k*30*s}" cy="{y-k*70*s}" r="{(30+k*14)*s}" fill="#e8e4ec" opacity="{0.8-k*0.12}" stroke="{INK}" stroke-width="1.2"/>' for k in range(n))

def chair(x, y, s=1.0, col="#b98d57"):
    g = rect(x - 60*s, y - 120*s, 120*s, 20*s, col) + rect(x - 60*s, y - 260*s, 18*s, 260*s, col) + rect(x + 42*s, y - 120*s, 18*s, 120*s, col)
    g += rect(x - 60*s, y - 260*s, 18*s, 140*s, col) + rect(x - 60*s, y - 250*s, 18*s, 10*s, col)
    g += rect(x - 52*s, y - 100*s, 14*s, 100*s, col)
    return g

def sparkle(x, y, s=1.0, col="#ffe3a1"):
    return f'<path d="M{x},{y-40*s} L{x+10*s},{y-10*s} L{x+40*s},{y} L{x+10*s},{y+10*s} L{x},{y+40*s} L{x-10*s},{y+10*s} L{x-40*s},{y} L{x-10*s},{y-10*s}z" fill="{col}" stroke="{INK}" stroke-width="1.5"/>'

def bubble(x, y, rx=230, ry=190, tail=(1, 1)):
    g = f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#f6f1e6" stroke="{INK}" stroke-width="4"/>'
    g += f'<circle cx="{x+tail[0]*rx*0.35}" cy="{y+ry+40}" r="30" fill="#f6f1e6" stroke="{INK}" stroke-width="3"/><circle cx="{x+tail[0]*rx*0.5}" cy="{y+ry+100}" r="16" fill="#f6f1e6" stroke="{INK}" stroke-width="3"/>'
    return g

def coins(x, y, s=1.0):
    g = ""
    for k in range(5): g += f'<ellipse cx="{x}" cy="{y-k*16*s}" rx="{60*s}" ry="{18*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    g += f'<ellipse cx="{x+90*s}" cy="{y}" rx="{60*s}" ry="{18*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    return g

def cross(x, y, r, w=18):
    return f'<path d="M{x-r},{y-r} L{x+r},{y+r} M{x+r},{y-r} L{x-r},{y+r}" stroke="#b4483f" stroke-width="{w}" stroke-linecap="round"/>'

def raised_arms(x, y, s=1.0, coat="#556078"):
    """du'a arms for a front-facing man actor standing with feet at (x,y): two sleeves raised, open palms (mittens)."""
    h = 300 * s; g = ""
    for sd in (-1, 1):
        sx, sy = x + sd * 34*s, y - h*0.78
        ex, ey = x + sd * 70*s, y - h*0.95
        g += f'<path d="M{sx},{sy} L{ex},{ey}" stroke="{coat}" stroke-width="{20*s}" stroke-linecap="round"/>'
        g += f'<ellipse cx="{ex+sd*4*s}" cy="{ey-16*s}" rx="{13*s}" ry="{20*s}" fill="#d9a98a" stroke="{INK}" stroke-width="1.8"/>'
    return g

# ---------------- reel 0011 props ----------------
def rays(x, y, n=9, length=1500, spread=70, col="#fff1c4", op=0.32):
    """soft light rays fanning down from (x,y) (a 'nur' metaphor, no figures)."""
    g = ""
    for k in range(n):
        a = math.radians(90 - spread / 2 + spread * k / max(n - 1, 1))
        w = 0.05
        x1, y1 = x + length * math.cos(a - w), y + length * math.sin(a - w)
        x2, y2 = x + length * math.cos(a + w), y + length * math.sin(a + w)
        g += f'<polygon points="{x},{y} {x1:.0f},{y1:.0f} {x2:.0f},{y2:.0f}" fill="{col}" opacity="{op}"/>'
    return g

def orbs(seed, n, x0, y0, x1, y1):
    r = random.Random(seed); g = ""
    for _ in range(n):
        x, y, rr = r.uniform(x0, x1), r.uniform(y0, y1), r.uniform(14, 30)
        g += f'<circle cx="{x}" cy="{y}" r="{rr*4}" fill="url(#glow)"/><circle cx="{x}" cy="{y}" r="{rr}" fill="#fff4cf" stroke="#e2b84f" stroke-width="1.5"/>'
    return g

def fork_road(y, x=621, light_left=True):
    """road from the bottom splitting into two paths: left -> up-left, right -> up-right."""
    g = poly([(x - 260, SH), (x + 260, SH), (x + 60, y + 150), (x - 60, y + 150)], "#e6e0d6", sw=1.8)
    g += poly([(x - 60, y + 150), (x + 10, y + 150), (x - 330, y - 120), (x - 390, y - 120)], "#efe8da" if light_left else "#8d86a3", sw=1.8)
    g += poly([(x - 10, y + 150), (x + 60, y + 150), (x + 390, y - 120), (x + 330, y - 120)], "#6e6a86", sw=1.8)
    return g

def signpost(x, y, s=1.0):
    g = rect(x - 10*s, y - 330*s, 20*s, 330*s, WOOD)
    g += poly([(x - 10*s, y - 320*s), (x - 190*s, y - 320*s), (x - 220*s, y - 285*s), (x - 190*s, y - 250*s), (x - 10*s, y - 250*s)], "#f6e7b8", sw=2)
    g += poly([(x + 10*s, y - 230*s), (x + 190*s, y - 230*s), (x + 220*s, y - 195*s), (x + 190*s, y - 160*s), (x + 10*s, y - 160*s)], "#6e6a86", sw=2)
    return g

def scale(x, y, s=1.0, tilt=0):
    """balance scale (tarozi); tilt>0 lowers the right pan."""
    g = rect(x - 90*s, y - 20*s, 180*s, 20*s, WOOD) + rect(x - 12*s, y - 420*s, 24*s, 400*s, WOOD)
    dy = tilt * 40*s
    g += f'<line x1="{x-220*s}" y1="{y-400*s+dy*-1}" x2="{x+220*s}" y2="{y-400*s+dy}" stroke="{INK}" stroke-width="{10*s}" stroke-linecap="round"/>'
    for sd, d in ((-1, -dy), (1, dy)):
        px, py = x + sd * 220*s, y - 400*s + d
        g += f'<path d="M{px},{py} L{px-70*s},{py+180*s} M{px},{py} L{px+70*s},{py+180*s}" stroke="{INK}" stroke-width="2.5"/>'
        g += f'<path d="M{px-90*s},{py+180*s} q{90*s},{60*s} {180*s},0z" fill="#e2b84f" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<circle cx="{x}" cy="{y-430*s}" r="{18*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    return g

def exam_sheet(x, y, s=1.0):
    g = poly([(x - 200*s, y - 280*s), (x + 200*s, y - 300*s), (x + 220*s, y + 160*s), (x - 180*s, y + 180*s)], "#f8f4ea", sw=2.5)
    g += f'<text x="{x+10*s}" y="{y-200*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{50*s}" fill="{INK}" text-anchor="middle" transform="rotate(-3 {x} {y})">IMTIHON</text>'
    for k in range(4):
        yy = y - 120*s + k * 70*s
        g += rect(x - 150*s, yy, 34*s, 34*s, "#ffffff", sw=2) + f'<line x1="{x-90*s}" y1="{yy+18*s}" x2="{x+150*s}" y2="{yy+12*s}" stroke="#9a948a" stroke-width="{4*s}"/>'
    g += f'<path d="M{x-145*s},{y-102*s} l12,16 l26,-30" stroke="#3f6b4c" stroke-width="5" fill="none"/>'
    return g

def hourglass(x, y, s=1.0):
    g = rect(x - 70*s, y - 20*s, 140*s, 20*s, WOOD) + rect(x - 70*s, y - 300*s, 140*s, 20*s, WOOD)
    g += f'<path d="M{x-55*s},{y-280*s} L{x+55*s},{y-280*s} L{x+6*s},{y-160*s} L{x+55*s},{y-20*s} L{x-55*s},{y-20*s} L{x-6*s},{y-160*s}z" fill="#e9f2f8" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<path d="M{x-30*s},{y-230*s} L{x+30*s},{y-230*s} L{x},{y-170*s}z M{x-45*s},{y-20*s} q{45*s},{-60*s} {90*s},0z" fill="#e2b84f"/>'
    return g

def sheep(x, y, s=1.0, flip=False):
    t = f' transform="translate({2*x},0) scale(-1,1)"' if flip else ""
    g = f'<g{t}>'
    for dx in (-40, -15, 15, 40): g += rect(x + dx*s - 6*s, y - 50*s, 12*s, 50*s, "#3b3a48", sw=1)
    for k in range(7):
        cx = x - 60*s + k * 20*s; cy = y - 85*s + (k % 2) * 14*s
        g += f'<circle cx="{cx}" cy="{cy}" r="{34*s}" fill="#f4f1ea" stroke="{INK}" stroke-width="1.8"/>'
    g += f'<ellipse cx="{x+85*s}" cy="{y-95*s}" rx="{26*s}" ry="{18*s}" fill="#3b3a48" stroke="{INK}" stroke-width="1.5" transform="rotate(25 {x+85*s} {y-95*s})"/>'
    return g + "</g>"

def cow(x, y, s=1.0, flip=False):
    t = f' transform="translate({2*x},0) scale(-1,1)"' if flip else ""
    g = f'<g{t}>'
    for dx in (-80, -50, 50, 80): g += rect(x + dx*s - 9*s, y - 90*s, 18*s, 90*s, "#8a6a55", sw=1.2)
    g += f'<ellipse cx="{x}" cy="{y-130*s}" rx="{120*s}" ry="{60*s}" fill="#e6ddd0" stroke="{INK}" stroke-width="2"/>'
    g += f'<ellipse cx="{x-40*s}" cy="{y-140*s}" rx="{36*s}" ry="{24*s}" fill="#8a6a55"/><ellipse cx="{x+50*s}" cy="{y-120*s}" rx="{28*s}" ry="{20*s}" fill="#8a6a55"/>'
    g += f'<ellipse cx="{x+140*s}" cy="{y-150*s}" rx="{34*s}" ry="{44*s}" fill="#e6ddd0" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M{x+118*s},{y-188*s} l{-14*s},{-22*s} M{x+160*s},{y-188*s} l{14*s},{-22*s}" stroke="{INK}" stroke-width="{5*s}" stroke-linecap="round"/>'
    g += f'<ellipse cx="{x+148*s}" cy="{y-118*s}" rx="{22*s}" ry="{14*s}" fill="#d9a98a" stroke="{INK}" stroke-width="1.5"/>'
    return g + "</g>"

def meadow(y, col="#b7c2a6"):
    g = poly([(0, y), (SW, y), (SW, SH), (0, SH)], col, sw=1.5)
    r = random.Random(int(y))
    for _ in range(60):
        x, yy = r.uniform(0, SW), r.uniform(y + 20, SH)
        g += f'<path d="M{x},{yy} l-6,-18 M{x},{yy} l0,-22 M{x},{yy} l6,-18" stroke="#5f8a55" stroke-width="2"/>'
    return g

def sky_stairs(x0, y0, x1, y1, wb, wt, n=24):
    return stairs(x0, y0, x1, y1, wb, wt, n)

def pit(x, y, w=700, h=380):
    return f'<path d="M{x-w/2},{y} q{w/2},{h*2} {w},0z" fill="#2f2b40" stroke="{INK}" stroke-width="3"/>'

# ---------------- reel 0010 props ----------------
def anger(x, y, s=1.0, seed=1):
    """red scribble cloud + zigzag = irritation/anger above a head."""
    r = random.Random(seed); pts = []
    for k in range(26):
        a = k * 2 * math.pi / 13; rr = (60 + r.uniform(-12, 12)) * s
        pts.append(f"{x + rr*1.4*math.cos(a):.0f},{y + rr*math.sin(a):.0f}")
    g = f'<polyline points="{" ".join(pts)}" fill="none" stroke="#c43d55" stroke-width="{6*s}" stroke-linejoin="round"/>'
    g += f'<path d="M{x-30*s},{y-110*s} l{20*s},{30*s} l{-15*s},{8*s} l{25*s},{35*s}" stroke="#c43d55" stroke-width="{6*s}" fill="none"/>'
    g += f'<path d="M{x+40*s},{y-100*s} l{15*s},{28*s} l{-14*s},{6*s} l{20*s},{30*s}" stroke="#c43d55" stroke-width="{6*s}" fill="none"/>'
    return g

def lightning(x, y, s=1.0):
    return f'<path d="M{x},{y} l{-40*s},{110*s} l{40*s},0 l{-30*s},{110*s} l{100*s},{-140*s} l{-45*s},0 l{30*s},{-80*s}z" fill="#e2b84f" stroke="#c43d55" stroke-width="{4*s}"/>'

def thorn_bush(x, y, s=1.0, seed=3):
    r = random.Random(seed); g = ""
    for _ in range(40):
        a = r.uniform(math.pi * 1.05, math.pi * 1.95); L_ = r.uniform(120, 330) * s
        x1, y1 = x + L_ * math.cos(a), y + L_ * math.sin(a)
        g += f'<path d="M{x},{y} Q{(x+x1)/2 + r.uniform(-60,60)},{(y+y1)/2} {x1:.0f},{y1:.0f}" stroke="#5a4a3a" stroke-width="{r.uniform(4,8)*s}" fill="none" stroke-linecap="round"/>'
        for k in range(3):
            t = r.uniform(0.3, 0.9); tx, ty = x + (x1 - x) * t, y + (y1 - y) * t
            g += f'<path d="M{tx},{ty} l{r.choice([-1,1])*16*s},{-12*s}" stroke="#5a4a3a" stroke-width="{3*s}"/>'
    for _ in range(18):
        a = r.uniform(math.pi * 1.1, math.pi * 1.9); d = r.uniform(80, 280) * s
        px, py = x + d * math.cos(a), y + d * math.sin(a)
        g += f'<ellipse cx="{px}" cy="{py}" rx="{22*s}" ry="{10*s}" fill="#7b8a55" stroke="{INK}" stroke-width="1" transform="rotate({r.uniform(-60,60)} {px} {py})"/>'
    return g

def book_stack(x, y, s=1.0):
    g = ""; cols = ["#3f6b4c", "#b4483f", "#6d86ab", "#8a6a55", "#e2b84f"]
    for k in range(5):
        w = (230 - k * 14) * s
        g += rect(x - w/2 + (k % 2) * 10, y - (k + 1) * 46*s, w, 42*s, cols[k], rx=4, sw=2)
        g += f'<line x1="{x - w/2 + 14 + (k%2)*10}" y1="{y-(k+1)*46*s+21*s}" x2="{x + w/2 - 14 + (k%2)*10}" y2="{y-(k+1)*46*s+21*s}" stroke="#e2b84f" stroke-width="2"/>'
    return g

def bookshelf(x, y, w=900, rows=4, seed=2):
    r = random.Random(seed); g = rect(x - w/2, y - rows * 230 - 40, w, rows * 230 + 40, WOOD, sw=3)
    cols = ["#3f6b4c", "#b4483f", "#6d86ab", "#8a6a55", "#556078", "#c9a26b"]
    for rw in range(rows):
        by = y - rw * 230 - 20
        g += rect(x - w/2 + 20, by - 200, w - 40, 200, "#5a4235", sw=1.5)
        bx = x - w/2 + 30
        while bx < x + w/2 - 70:
            bw = r.uniform(34, 60); bh = r.uniform(140, 190)
            g += rect(bx, by - bh, bw, bh, r.choice(cols), rx=3, sw=1.6)
            g += f'<line x1="{bx+5}" y1="{by-bh+25}" x2="{bx+bw-5}" y2="{by-bh+25}" stroke="#e2b84f" stroke-width="2"/>'
            bx += bw + 3
    return g

def open_book(x, y, s=1.0):
    return manual(x, y, s, icons=False) + "".join(
        f'<line x1="{x-125*s}" y1="{y-150*s+k*26*s}" x2="{x-25*s}" y2="{y-130*s+k*26*s}" stroke="#9a948a" stroke-width="{3*s}"/>'
        f'<line x1="{x+25*s}" y1="{y-130*s+k*26*s}" x2="{x+125*s}" y2="{y-150*s+k*26*s}" stroke="#9a948a" stroke-width="{3*s}"/>' for k in range(5))

def jug(x, y, s=1.0):
    g = f'<path d="M{x-50*s},{y} q{-30*s},{-90*s} {10*s},{-150*s} l{-10*s},{-40*s} l{70*s},0 l{-10*s},{40*s} q{40*s},{60*s} {10*s},{150*s}z" fill="#6d86ab" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<path d="M{x+30*s},{y-150*s} q{60*s},{-10*s} {80*s},{40*s}" stroke="{INK}" stroke-width="{6*s}" fill="none"/>'
    return g

def water_stream(x0, y0, x1, y1, w=26):
    return f'<path d="M{x0},{y0} Q{(x0+x1)/2+30},{y0} {x1},{y1}" stroke="#9fc6e6" stroke-width="{w}" fill="none" opacity="0.85" stroke-linecap="round"/>'

def prayer_mat(x, y, s=1.0, col="#3f6b4c"):
    g = poly([(x - 160*s, y), (x + 160*s, y), (x + 120*s, y - 330*s), (x - 120*s, y - 330*s)], col, sw=2.5)
    g += poly([(x - 120*s, y - 30*s), (x + 120*s, y - 30*s), (x + 92*s, y - 270*s), (x - 92*s, y - 270*s)], "none", stroke="#e2b84f", sw=4)
    g += f'<path d="M{x-60*s},{y-250*s} q{60*s},{-80*s} {120*s},0" stroke="#e2b84f" stroke-width="4" fill="none"/>'
    return g

def mihrab(x, y, s=1.0):
    g = f'<path d="M{x-200*s},{y} L{x-200*s},{y-520*s} Q{x-200*s},{y-760*s} {x},{y-820*s} Q{x+200*s},{y-760*s} {x+200*s},{y-520*s} L{x+200*s},{y}z" fill="#d8cdbf" stroke="{INK}" stroke-width="3"/>'
    g += f'<path d="M{x-140*s},{y} L{x-140*s},{y-480*s} Q{x-140*s},{y-660*s} {x},{y-710*s} Q{x+140*s},{y-660*s} {x+140*s},{y-480*s} L{x+140*s},{y}z" fill="#3f6b4c" stroke="{INK}" stroke-width="2.5"/>'
    return g

def warning(x, y, s=1.0):
    return (poly([(x, y - 90*s), (x + 100*s, y + 80*s), (x - 100*s, y + 80*s)], "#e2b84f", sw=4)
            + f'<rect x="{x-9*s}" y="{y-30*s}" width="{18*s}" height="{70*s}" rx="6" fill="{INK}"/><circle cx="{x}" cy="{y+60*s}" r="{10*s}" fill="{INK}"/>')

def green_dome(x, y, s=1.0):
    g = rect(x - 330*s, y - 300*s, 660*s, 300*s, WALL)
    g += rect(x - 110*s, y - 420*s, 220*s, 130*s, WALL2)
    g += f'<path d="M{x-120*s},{y-420*s} a{120*s},{150*s} 0 0 1 {240*s},0z" fill="#4f8a5c" stroke="{INK}" stroke-width="3"/>'
    g += f'<line x1="{x}" y1="{y-570*s}" x2="{x}" y2="{y-640*s}" stroke="{INK}" stroke-width="3"/><circle cx="{x}" cy="{y-650*s}" r="{10*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    for mx in (-420, 420):
        g += rect(x + mx*s - 32*s, y - 820*s, 64*s, 820*s, WALL2) + f'<path d="M{x+mx*s-36*s},{y-820*s} l{36*s},{-90*s} l{36*s},{90*s}z" fill="#dcd3c6" stroke="{INK}" stroke-width="2"/>'
        g += rect(x + mx*s - 46*s, y - 560*s, 92*s, 22*s, "#dcd3c6", sw=1.5)
    for k in range(-2, 3):
        g += f'<path d="M{x+k*120*s-35*s},{y} l0,{-130*s} a{35*s},{35*s} 0 0 1 {70*s},0 l0,{130*s}z" fill="#ffe3a1" stroke="{INK}" stroke-width="2"/>'
    return g

# ---------------- reel 0015 props (2026-11-20): shop vs prayer ----------------
def shelves(x, y, w=900, h=700, rows=3, seed=5):
    """shop shelves with jars, boxes and sacks (goods for sale)."""
    r = random.Random(seed); g = rect(x, y, w, h, "#b98d57")
    for k in range(rows):
        sy = y + (k + 1) * h / rows
        g += rect(x, sy - 16, w, 16, WOOD)
        cx = x + 20
        while cx < x + w - 70:
            kind = r.choice(["jar", "box", "sack"]); c = r.choice(["#d04a7a", "#e2b84f", "#6d86ab", "#4f7d5c", "#c98b4f"])
            if kind == "jar":
                g += rect(cx, sy - 16 - 110, 70, 110, c, rx=14) + rect(cx + 8, sy - 16 - 128, 54, 22, "#f4f1ea", rx=4)
                cx += 85
            elif kind == "box":
                bw = r.uniform(80, 120); bh = r.uniform(80, 150)
                g += rect(cx, sy - 16 - bh, bw, bh, c) + rect(cx + 10, sy - 16 - bh + 20, bw - 20, 24, "#f4f1ea", sw=1)
                cx += bw + 12
            else:
                g += f'<path d="M{cx},{sy-16} q-6,-90 20,-120 l50,0 q26,30 20,120z" fill="#d9c7a8" stroke="{INK}" stroke-width="2"/>'
                cx += 100
    return g

def counter(x, y, w=800, h=260, col=WOOD):
    """shop counter (front face + top), x,y = top-left of the top."""
    return rect(x - 20, y - 24, w + 40, 30, "#a07a5f") + rect(x, y, w, h, col) + rect(x + 30, y + 40, w - 60, h - 80, "#7a5a47", sw=1.5)

def azan_waves(x, y, n=4, s=1.0, col="#fff1c4"):
    """sound arcs spreading from a minaret top (the call to prayer)."""
    g = ""
    for k in range(1, n + 1):
        r = 70 * k * s
        g += f'<path d="M{x-r},{y-r*0.2} a{r},{r} 0 0 1 {2*r},0" fill="none" stroke="{col}" stroke-width="{12-k*2}" stroke-linecap="round" opacity="{0.95-k*0.15}"/>'
    return g

def shop_front(x, y, w=560, label="DO'KON", awning="#3f6b4c"):
    """shop front with striped awning, open door and goods outside."""
    h = 640
    g = rect(x, y - h, w, h, WALL)
    for k in range(int(w // 70) + 1):
        g += poly([(x + k * 70, y - h + 120), (x + k * 70 + 70, y - h + 120), (x + k * 70 + 80, y - h + 220), (x + k * 70 - 10, y - h + 220)],
                  awning if k % 2 == 0 else "#f4f1ea", sw=1.5)
    g += rect(x + 20, y - h + 20, w - 40, 90, "#3f6b4c", rx=8)
    g += f'<text x="{x+w/2}" y="{y-h+85}" font-family="Inter, sans-serif" font-weight="800" font-size="56" fill="#f6e7b8" text-anchor="middle">{label}</text>'
    g += rect(x + 40, y - 380, w - 80, 380, "#5e4a3f") + shelves(x + 50, y - 370, w - 100, 300, 2, seed=int(x) + 3)
    return g

def minaret_clock(x, y, s=1.0):
    """tall mosque with minaret + a clock on the wall (prayer time). returns (svg, clock center)."""
    g = dome(x, y, s)
    cx, cy, cr = x, y - 150 * s, 60 * s
    return g + clock_face(cx, cy, cr), (cx, cy, cr)

# ---------------- reel 0013 props (2026-11-20): "zero" start, no skip / no undo in life ----------------
def milestone(x, y, s=1.0, label="0"):
    """stone road milestone with a big number (journey start = 0)."""
    g = f'<path d="M{x-110*s},{y} L{x-110*s},{y-260*s} a{110*s},{110*s} 0 0 1 {220*s},0 L{x+110*s},{y}z" fill="#e9e2d6" stroke="{INK}" stroke-width="3"/>'
    g += rect(x - 130*s, y - 20*s, 260*s, 30*s, "#cfc5b8")
    g += f'<text x="{x}" y="{y-150*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{170*s}" fill="#3f6b4c" text-anchor="middle">{label}</text>'
    return g

def big_zero(x, y, r=260, col="#e2b84f"):
    """a huge golden '0' ring (the number zero)."""
    return (f'<circle cx="{x}" cy="{y}" r="{r*1.5}" fill="url(#glow)"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="{r*0.72}" ry="{r}" fill="none" stroke="{INK}" stroke-width="{r*0.36+6}"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="{r*0.72}" ry="{r}" fill="none" stroke="{col}" stroke-width="{r*0.36}"/>')

def trophy(x, y, s=1.0):
    """golden cup (yutuq = prize/win)."""
    g = rect(x - 120*s, y - 40*s, 240*s, 40*s, WOOD) + rect(x - 30*s, y - 160*s, 60*s, 120*s, "#d3a23f")
    g += f'<path d="M{x-170*s},{y-480*s} L{x+170*s},{y-480*s} Q{x+160*s},{y-180*s} {x},{y-160*s} Q{x-160*s},{y-180*s} {x-170*s},{y-480*s}z" fill="#e2b84f" stroke="{INK}" stroke-width="3"/>'
    for sd in (-1, 1):
        g += f'<path d="M{x+sd*165*s},{y-440*s} q{sd*110*s},{0} {sd*90*s},{110*s} q{-sd*20*s},{70*s} {-sd*110*s},{80*s}" fill="none" stroke="{INK}" stroke-width="{16*s}"/>'
        g += f'<path d="M{x+sd*165*s},{y-440*s} q{sd*110*s},{0} {sd*90*s},{110*s} q{-sd*20*s},{70*s} {-sd*110*s},{80*s}" fill="none" stroke="#e2b84f" stroke-width="{10*s}"/>'
    g += f'<path d="M{x-120*s},{y-430*s} q{40*s},{200*s} {60*s},{230*s}" stroke="#fff1c4" stroke-width="{14*s}" fill="none" opacity="0.7"/>'
    return g

def ui_button(x, y, label, s=1.0, col="#2e2a3a"):
    """video-player style button with a label (e.g. SKIP ⏭)."""
    w = (len(label) * 52 + 160) * s
    g = rect(x - w/2, y - 75*s, w, 150*s, col, rx=int(75*s), sw=4)
    g += f'<text x="{x-40*s}" y="{y+28*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{80*s}" fill="#f6f1e6" text-anchor="middle">{label}</text>'
    tx = x + w/2 - 90*s
    g += f'<path d="M{tx-30*s},{y-35*s} l{35*s},{35*s} l{-35*s},{35*s}z M{tx+5*s},{y-35*s} l{35*s},{35*s} l{-35*s},{35*s}z" fill="#f6f1e6"/>'
    return g

def keycap(x, y, label, w=260, s=1.0):
    g = rect(x - w/2*s, y - 110*s, w*s, 220*s, "#d9d4cc", rx=int(28*s), sw=4)
    g += rect(x - w/2*s + 22*s, y - 92*s, w*s - 44*s, 160*s, "#f4f1ea", rx=int(20*s), sw=2)
    g += f'<text x="{x}" y="{y+20*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{90*s}" fill="{INK}" text-anchor="middle">{label}</text>'
    return g

def undo_arrow(x, y, r=300, col="#6d86ab"):
    """big curved arrow turning back (undo)."""
    return (f'<path d="M{x+r},{y} A{r},{r} 0 1 0 {x},{y+r}" fill="none" stroke="{INK}" stroke-width="64" stroke-linecap="round"/>'
            f'<path d="M{x+r},{y} A{r},{r} 0 1 0 {x},{y+r}" fill="none" stroke="{col}" stroke-width="50" stroke-linecap="round"/>'
            + poly([(x - 80, y + r - 90), (x + 40, y + r), (x - 80, y + r + 90)], col, sw=4))

def fake_facade(x, y, s=1.0):
    """a grand house front that is only a painted board propped up by wooden sticks (soxta obro')."""
    w, h = 620*s, 720*s
    g = ""
    for k in (0.2, 0.8):  # props behind
        g += f'<path d="M{x-w/2+w*k},{y-h+80*s} L{x-w/2+w*k+220*s},{y}" stroke="{WOOD}" stroke-width="{18*s}"/>'
    g += rect(x - w/2, y - h, w, h, "#efe2c8", sw=3)
    g += poly([(x - w/2 - 30*s, y - h), (x + w/2 + 30*s, y - h), (x, y - h - 200*s)], "#c9a26b", sw=3)
    for cx in (x - w/2 + 60*s, x + w/2 - 100*s): g += rect(cx, y - h + 20*s, 40*s, h - 20*s, "#e6d3ad", sw=2)
    g += window(x - 220*s, y - h + 140*s, 110*s, 170*s) + window(x + 110*s, y - h + 140*s, 110*s, 170*s)
    g += door(x - 80*s, y - 340*s, 160*s, 340*s, WOOD)
    g += f'<path d="M{x+w/2},{y-h} l{30*s},{40*s} l{-30*s},{20*s}" fill="#f4f1ea" stroke="{INK}" stroke-width="2"/>'  # peeling corner
    return g

def debt_papers(x, y, s=1.0, label="QARZ"):
    """a tall stack of IOU papers with a red label."""
    g = ""
    for k in range(9):
        g += rect(x - 160*s + (k % 2) * 12*s, y - (k + 1) * 46*s, 320*s, 46*s, "#f6f1e6", sw=2)
    g += rect(x - 150*s, y - 520*s, 300*s, 100*s, "#b4483f", rx=10, sw=3)
    g += f'<text x="{x}" y="{y-445*s}" font-family="Inter, sans-serif" font-weight="800" font-size="{70*s}" fill="#f6f1e6" text-anchor="middle">{label}</text>'
    return g

def broken_jug(x, y, s=1.0):
    g = f'<path d="M{x-80*s},{y} q{-20*s},{-70*s} {20*s},{-110*s} l{30*s},{40*s} l{20*s},{-30*s} l{30*s},{100*s}z" fill="#6d86ab" stroke="{INK}" stroke-width="2.5"/>'
    g += poly([(x + 60*s, y), (x + 120*s, y - 40*s), (x + 170*s, y - 5*s)], "#6d86ab", sw=2.5)
    g += poly([(x - 170*s, y), (x - 130*s, y - 50*s), (x - 100*s, y - 10*s)], "#6d86ab", sw=2.5)
    g += f'<path d="M{x-200*s},{y+10*s} q{200*s},{40*s} {420*s},0" stroke="#9fc6e6" stroke-width="{14*s}" fill="none" opacity="0.8"/>'
    return g

def numbered_steps(x, y0, y1, n=6, wb=900, wt=360):
    """big perspective stairs with step numbers 1..n (life stages / bosqichlar)."""
    g = stairs(x, y0, x, y1, wb, wt, n, col="#efe8da")
    for i in range(n):
        k = ((i + 0.6) / n) ** 0.8
        yy = y0 + (y1 - y0) * k; ww = wb + (wt - wb) * k
        g += f'<text x="{x}" y="{yy+10}" font-family="Inter, sans-serif" font-weight="800" font-size="{40+ww*0.06:.0f}" fill="#3f6b4c" text-anchor="middle">{i+1}</text>'
    return g

# ---------------- reel 0009 props (2026-11-20): islom / iymon / ihson ----------------
def golden_dome_shrine(x, y, s=1.0):
    """octagonal shrine with a golden dome (old Quds), stone walls around."""
    g = rect(x - 520*s, y - 180*s, 1040*s, 180*s, "#d9cdb5", sw=2.5)
    for k in range(9): g += rect(x - 520*s + k * 120*s, y - 220*s, 60*s, 40*s, "#d9cdb5", sw=2)
    g += poly([(x - 260*s, y - 180*s), (x + 260*s, y - 180*s), (x + 260*s, y - 520*s), (x - 260*s, y - 520*s)], "#6d86ab", sw=3)
    for k in range(-2, 3): g += f'<path d="M{x+k*95*s-28*s},{y-260*s} l0,{-150*s} a{28*s},{28*s} 0 0 1 {56*s},0 l0,{150*s}z" fill="#ffe3a1" stroke="{INK}" stroke-width="2"/>'
    g += rect(x - 150*s, y - 600*s, 300*s, 80*s, "#e9e2d6", sw=2.5)
    g += f'<path d="M{x-170*s},{y-600*s} a{170*s},{190*s} 0 0 1 {340*s},0z" fill="#e2b84f" stroke="{INK}" stroke-width="3"/>'
    g += f'<line x1="{x}" y1="{y-790*s}" x2="{x}" y2="{y-860*s}" stroke="{INK}" stroke-width="3"/><circle cx="{x}" cy="{y-868*s}" r="{10*s}" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
    return g

def sea_city(y, s=1.0):
    """city on the sea shore: walls, domes, several minarets; sailing boats on the water."""
    g = f'<path d="M0,{y} L{SW},{y} L{SW},{y+500} L0,{y+500}z" fill="#9fb8c9" stroke="{INK}" stroke-width="2"/>'
    g += "".join(f'<path d="M{x},{y+yy} l120,0" stroke="#f4f1ea" stroke-width="5" opacity="0.7"/>' for x, yy in ((100, 120), (500, 200), (850, 90), (300, 320)))
    g += rect(0, y - 160*s, SW, 160*s, "#d9cdb5", sw=2.5)
    for k in range(12): g += rect(k * 110, y - 200*s, 55, 40*s, "#d9cdb5", sw=2)
    g += dome(700, y - 150*s, 1.0 * s) + dome(300, y - 150*s, 0.7 * s)
    for mx in (120, 1120):
        g += rect(mx - 30, y - 760*s, 60, 600*s, WALL2) + f'<path d="M{mx-34},{y-760*s} l34,-90 l34,90z" fill="#dcd3c6" stroke="{INK}" stroke-width="2"/>'
    return g

def boat(x, y, s=1.0):
    g = f'<path d="M{x-150*s},{y} L{x+150*s},{y} L{x+110*s},{y+60*s} L{x-110*s},{y+60*s}z" fill="{WOOD}" stroke="{INK}" stroke-width="2.5"/>'
    g += f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-260*s}" stroke="{INK}" stroke-width="4"/>'
    g += f'<path d="M{x+6*s},{y-250*s} Q{x+150*s},{y-140*s} {x+6*s},{y-20*s}z" fill="#f4f1ea" stroke="{INK}" stroke-width="2.5"/>'
    return g

def tent(x, y, s=1.0, col="#d9c7a8"):
    g = poly([(x - 300*s, y), (x + 300*s, y), (x, y - 360*s)], col, sw=3)
    g += poly([(x - 70*s, y), (x + 70*s, y), (x, y - 220*s)], "#5e4a3f", sw=2)
    g += f'<line x1="{x}" y1="{y-360*s}" x2="{x}" y2="{y-460*s}" stroke="{INK}" stroke-width="3"/><path d="M{x},{y-460*s} l90,25 l-90,25z" fill="#3f6b4c" stroke="{INK}" stroke-width="2"/>'
    return g

def broken_arrows(x, y, s=1.0):
    g = ""
    for k, (dx, a) in enumerate(((-200, -20), (-80, 15), (60, -8), (190, 25), (-140, 40))):
        x0, y0 = x + dx*s, y - k * 8*s
        g += f'<g transform="rotate({a} {x0} {y0})"><line x1="{x0-110*s}" y1="{y0}" x2="{x0-10*s}" y2="{y0}" stroke="{WOOD}" stroke-width="{10*s}"/>'
        g += f'<line x1="{x0+10*s}" y1="{y0+6*s}" x2="{x0+110*s}" y2="{y0+6*s}" stroke="{WOOD}" stroke-width="{10*s}"/>'
        g += f'<path d="M{x0+110*s},{y0-6*s} l{30*s},{12*s} l{-30*s},{12*s}z" fill="#8f8aa6" stroke="{INK}" stroke-width="1.5"/></g>'
    g += f'<path d="M{x-260*s},{y+40*s} q{80*s},{-160*s} {150*s},{-20*s}" stroke="{WOOD}" stroke-width="{12*s}" fill="none"/>'
    g += f'<path d="M{x-90*s},{y+40*s} q{60*s},{-120*s} {140*s},{-30*s}" stroke="{WOOD}" stroke-width="{12*s}" fill="none"/>'
    return g

def three_tiers(x, y, labels=("ISLOM", "IYMON", "IHSON"), lit=(), checks=(), s=1.0):
    """3 big stone tiers (pyramid steps) with labels; lit = indices glowing gold; checks = indices with a green tick."""
    g = ""
    for i, lab in enumerate(labels):
        w = (1000 - i * 260) * s; h = 230 * s; ty = y - (i + 1) * h
        col = "#f2d98a" if i in lit else ["#e9e2d6", "#e2dbd0", "#dcd3c6"][i]
        if i in lit: g += f'<circle cx="{x}" cy="{ty+h/2}" r="{w*0.55}" fill="url(#glow)"/>'
        g += rect(x - w/2, ty, w, h, col, sw=3)
        g += f'<text x="{x}" y="{ty+h*0.63}" font-family="Inter, sans-serif" font-weight="800" font-size="{min(84*s, w/7)}" fill="#3f6b4c" text-anchor="middle">{lab}</text>'
        if i in checks:
            cx = x + w/2 - 80*s; cy = ty + h/2
            g += f'<circle cx="{cx}" cy="{cy}" r="{50*s}" fill="#4f8a5c" stroke="{INK}" stroke-width="3"/><path d="M{cx-25*s},{cy} l{18*s},{20*s} l{32*s},{-38*s}" stroke="#f6f1e6" stroke-width="{10*s}" fill="none" stroke-linecap="round"/>'
    return g

def tier_top(x, y, i, s=1.0):
    """feet position (x, y) on top of tier i of three_tiers(x, y)."""
    return x, y - (i + 1) * 230 * s
