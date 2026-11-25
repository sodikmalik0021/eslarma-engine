"""Kit v3 (2026-11-22 evening): desert-road / caravan world — camel (walk phases), city gate, Kaaba, stone prison tower,
fruit tree, child figure, desert road on the shared world.py camera. Same palette/ink as kit2/kit25."""
import math, random
from scenes import INK, SW, SH, poly, rect, man, woman
from kit2 import tree

SAND, SAND2, SAND3 = "#e6d3b0", "#d9c29a", "#cdb48a"
STONE, STONE2 = "#d8cbb5", "#c4b49a"

def camel(x, y, s=1.0, walk=0.0, flip=False, blanket="#b4483f", load=True):
    """Side-view camel, (x,y)=feet centre, faces right (flip=True faces left). walk in [-1,1] swings legs."""
    c = "#c9a274"; c2 = "#b38c5f"; k = 2.0
    g = f'<ellipse cx="0" cy="0" rx="150" ry="16" fill="#000" opacity="0.13"/>'
    sw_ = walk * 22
    for lx, ph, col in ((-85, 1, c2), (65, -1, c2), (-60, -1, c), (90, 1, c)):  # legs: far pair darker
        d = sw_ * ph
        g += poly([(lx - 13, -175), (lx + 13, -175), (lx + 8 + d * 0.6, -95), (lx + 7 + d, -6), (lx - 7 + d, -6), (lx - 9 + d * 0.6, -95)], col, sw=k)
        g += f'<ellipse cx="{lx + d}" cy="-5" rx="17" ry="7" fill="{c2}" stroke="{INK}" stroke-width="{k}"/>'
    g += (f'<path d="M-130,-170 Q-150,-250 -70,-262 Q-30,-345 25,-262 Q70,-250 110,-215 L150,-215 Q150,-170 105,-160 '
          f'Q20,-140 -100,-150 Q-128,-152 -130,-170z" fill="{c}" stroke="{INK}" stroke-width="{k}"/>')
    g += f'<path d="M-138,-195 q-25,20 -18,60" fill="none" stroke="{INK}" stroke-width="3"/>'  # tail
    g += (f'<path d="M105,-215 Q150,-260 160,-330 Q165,-370 200,-372 L232,-362 Q246,-350 232,-338 L205,-332 Q190,-300 178,-250 '
          f'Q165,-195 140,-170z" fill="{c}" stroke="{INK}" stroke-width="{k}"/>')  # neck + head
    g += f'<circle cx="206" cy="-358" r="4" fill="{INK}"/><path d="M190,-372 l-6,-14 l12,6z" fill="{c2}" stroke="{INK}" stroke-width="1.5"/>'
    if blanket:
        g += f'<path d="M-62,-262 Q-30,-300 15,-262 L28,-200 Q-20,-188 -75,-200z" fill="{blanket}" stroke="{INK}" stroke-width="{k}"/>'
        for i in range(6):
            tx = -72 + i * 19
            g += f'<path d="M{tx},-200 l3,18" stroke="#e2b84f" stroke-width="4"/>'
        g += f'<path d="M-62,-245 Q-25,-270 18,-245" fill="none" stroke="#e2b84f" stroke-width="5"/>'
    if load:
        g += rect(-20, -318, 70, 52, "#a98a6a", sw=k, rx=8) + f'<path d="M-20,-300 h70" stroke="{INK}" stroke-width="2"/>'
    tr = f"translate({x},{y}) scale({-s if flip else s},{s})"
    return f'<g transform="{tr}">{g}</g>'

def camel_kneel(x, y, s=1.0, flip=False):
    c = "#c9a274"
    g = f'<ellipse cx="0" cy="0" rx="170" ry="16" fill="#000" opacity="0.13"/>'
    g += f'<path d="M-150,-10 Q-160,-110 -70,-125 Q-30,-200 25,-125 Q90,-120 120,-70 Q140,-10 100,-6z" fill="{c}" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M100,-60 Q150,-110 160,-180 Q165,-215 198,-216 L230,-206 Q244,-194 230,-182 L203,-178 Q188,-140 172,-80 L140,-20z" fill="{c}" stroke="{INK}" stroke-width="2"/>'
    g += f'<circle cx="204" cy="-202" r="4" fill="{INK}"/>'
    g += f'<path d="M-62,-125 Q-30,-162 15,-125 L28,-62 Q-20,-50 -75,-62z" fill="#b4483f" stroke="{INK}" stroke-width="2"/>'
    return f'<g transform="translate({x},{y}) scale({-s if flip else s},{s})">{g}</g>'

def rein(x0, y0, x1, y1, sag=40):
    return f'<path d="M{x0},{y0} Q{(x0+x1)/2},{max(y0,y1)+sag} {x1},{y1}" fill="none" stroke="#6b4a35" stroke-width="5"/>'

def city_gate(x, y, s=1.0, open_=0.0, glow=True):
    """Big arched city gate with crenellated towers; open_ 0..1 opens the two wooden leaves (light spills out)."""
    w, h = 520, 620
    g = ""
    for tx in (-w / 2 - 150, w / 2):  # towers
        g += rect(tx, -h - 140, 150, h + 140, STONE, sw=2.2)
        for i in range(4): g += rect(tx + 6 + i * 36, -h - 175, 28, 36, STONE, sw=1.8)
        g += rect(tx + 55, -h - 40, 40, 70, "#5b5470", sw=1.8, rx=18)
    g += rect(-w / 2, -h, w, h, STONE2, sw=2.2)
    for i in range(7): g += rect(-w / 2 + 6 + i * 73, -h - 34, 58, 34, STONE2, sw=1.8)
    for r_ in range(9):  # brick courses
        yy = -h + 60 + r_ * 62
        g += f'<path d="M{-w/2},{yy} h{w}" stroke="{INK}" stroke-opacity="0.18" stroke-width="2"/>'
    aw, ah = 300, 440
    arch = f'M{-aw/2},0 L{-aw/2},{-ah+aw/2} A{aw/2},{aw/2} 0 0 1 {aw/2},{-ah+aw/2} L{aw/2},0z'
    if glow and open_ > 0:
        g += f'<path d="{arch}" fill="#fff1c4"/><ellipse cx="0" cy="-200" rx="{220*open_+60}" ry="300" fill="url(#glow)"/>'
    else:
        g += f'<path d="{arch}" fill="#4d4560"/>'
    if open_ == 0:
        g += f'<path d="{arch}" fill="#8a6a55" stroke="{INK}" stroke-width="2.2"/>'
        for i in range(3): g += f'<path d="M{-aw/2},{-60-i*120} H{aw/2}" stroke="#4a3a30" stroke-width="6"/>'
    else:
        lw = aw / 2 * (1 - 0.8 * open_)
        for sgn in (-1, 1):
            x0 = sgn * aw / 2; x1 = sgn * (aw / 2 - lw)
            g += poly([(x0, 0), (x0, -ah + aw / 2 + 10), (x1, -ah + aw / 2 + 40), (x1, 0)], "#8a6a55", sw=2.2)
            for i in range(3): g += f'<path d="M{x0},{-60-i*120} L{x1},{-60-i*118}" stroke="#4a3a30" stroke-width="6"/>'
    if open_ == 0:
        g += f'<path d="M0,0 L0,{-ah}" stroke="{INK}" stroke-width="3"/><circle cx="-18" cy="-200" r="9" fill="#e2b84f" stroke="{INK}" stroke-width="2"/><circle cx="18" cy="-200" r="9" fill="#e2b84f" stroke="{INK}" stroke-width="2"/>'
        g += f'<path d="M-8,{-ah+6} L0,{-ah+6} L0,{-ah+30}" stroke="#fff1c4" stroke-width="5" opacity="0.8"/>'  # light in the crack
        g += f'<rect x="-3" y="{-ah+30}" width="6" height="{ah-40}" fill="#fff1c4" opacity="0.75"/>'
    g += f'<path d="M{-aw/2-18},0 L{-aw/2-18},{-ah+aw/2} A{aw/2+18},{aw/2+18} 0 0 1 {aw/2+18},{-ah+aw/2} L{aw/2+18},0" fill="none" stroke="{INK}" stroke-width="2.5"/>'
    for lx in (-aw / 2 - 60, aw / 2 + 60):  # lanterns
        g += f'<circle cx="{lx}" cy="{-ah+80}" r="70" fill="url(#glow)"/><rect x="{lx-14}" y="{-ah+60}" width="28" height="42" rx="6" fill="#ffd98a" stroke="{INK}" stroke-width="2"/>'
    return f'<g transform="translate({x},{y}) scale({s})">{g}</g>'

def kaaba(x, y, s=1.0):
    g = poly([(-120, 0), (120, 0), (150, -30), (150, -250), (-90, -250), (-120, -220)], "#2b2a33", sw=2.2)
    g += poly([(120, 0), (150, -30), (150, -250), (120, -220)], "#1f1e26", sw=2.2)
    g += poly([(-120, -220), (120, -220), (150, -250), (-90, -250)], "#3a3944", sw=2.2)
    g += poly([(-120, -175), (120, -175), (120, -150), (-120, -150)], "#d4a84a", sw=1.2)
    g += poly([(120, -175), (150, -205), (150, -180), (120, -150)], "#b88e3a", sw=1.2)
    g += rect(55, -125, 40, 95, "#d4a84a", sw=1.5, rx=3)
    return f'<g transform="translate({x},{y}) scale({s})">{g}</g>'

def tawaf_ring(cx, cy, rx, ry, n, seed=4, s=0.33):
    r = random.Random(seed); pts = []
    for ring in range(3):
        for i in range(n):
            a = 2 * math.pi * (i + r.random() * 0.6) / n
            pts.append((cy + math.sin(a) * (ry + ring * 55), cx + math.cos(a) * (rx + ring * 90)))
    g = ""
    for py, px in sorted(pts):
        sc = s * (0.85 + 0.3 * (py - cy + ry) / (2 * ry + 1))
        g += man(px, py, sc, back=True, cap=False, coat="#f3f0e8") if r.random() < 0.7 else woman(px, py, sc, dress="#f3f0e8", scarf="#ffffff")
    return g

def prison_tower(x, y, s=1.0, lit=True):
    g = poly([(-210, 0), (210, 0), (180, -820), (-180, -820)], STONE, sw=2.4)
    for i in range(14):
        yy = -50 - i * 56; off = 0 if i % 2 else 40
        g += f'<path d="M{-205+i*2},{yy} H{205-i*2}" stroke="{INK}" stroke-opacity="0.2" stroke-width="2"/>'
        for j in range(4): g += f'<path d="M{-150+off+j*90},{yy} v56" stroke="{INK}" stroke-opacity="0.15" stroke-width="2"/>'
    for i in range(5): g += rect(-185 + i * 78, -870, 60, 50, STONE, sw=2)
    g += f'<circle cx="0" cy="-560" r="190" fill="url(#glow)" opacity="{0.9 if lit else 0.2}"/>'
    g += rect(-60, -640, 120, 150, "#ffd98a" if lit else "#4d4560", sw=2.4, rx=50)
    for i in range(4): g += f'<path d="M{-36+i*24},-635 v140" stroke="{INK}" stroke-width="7"/>'
    g += f'<path d="M-60,-560 h120" stroke="{INK}" stroke-width="6"/>'
    g += f'<path d="M-80,0 L-80,-210 A80,80 0 0 1 80,-210 L80,0z" fill="#6b5545" stroke="{INK}" stroke-width="2.4"/>'
    for i in range(3): g += f'<path d="M-80,{-50-i*60} h160" stroke="#3d3030" stroke-width="7"/>'
    g += f'<circle cx="50" cy="-110" r="11" fill="#7a7480" stroke="{INK}" stroke-width="2"/>'
    return f'<g transform="translate({x},{y}) scale({s})">{g}</g>'

def prison_door_open(x, y, s=1.0):
    """Close-up: heavy door swung open, a beam of light falls out onto the floor; the cell stays (nobody steps out)."""
    g = f'<path d="M-170,0 L-170,-430 A170,170 0 0 1 170,-430 L170,0z" fill="#fff1c4" stroke="{INK}" stroke-width="3"/>'
    g += f'<ellipse cx="0" cy="-300" rx="260" ry="380" fill="url(#glow)"/>'
    g += poly([(-170, 0), (170, 0), (420, 260), (-420, 260)], "#fbe7b0", sw=0, op=0.55)
    g += rect(-120, -360, 240, 150, "#f3d993", sw=0, rx=60) + "".join(f'<path d="M{-80+i*40},-360 v150" stroke="#c9a868" stroke-width="10"/>' for i in range(5))
    g += poly([(170, 0), (170, -560), (330, -520), (330, 30)], "#6b5545", sw=3)  # open leaf
    for i in range(4): g += f'<path d="M170,{-80-i*130} L330,{-60-i*125}" stroke="#3d3030" stroke-width="9"/>'
    g += f'<circle cx="300" cy="-280" r="16" fill="#7a7480" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M300,-262 q-6,40 6,70 l14,0 m-14,-20 l12,0" fill="none" stroke="#e2b84f" stroke-width="7"/>'  # key on ring
    return f'<g transform="translate({x},{y}) scale({s})">{g}</g>'

def scroll(x, y, s=1.0, ribbon="#3f6b4c"):
    """Unrolled white scroll (verdict / clean name) with a gold seal."""
    g = rect(-230, -300, 460, 560, "#fbf6ea", sw=2.4, rx=10)
    g += rect(-260, -330, 520, 50, "#e8dcc2", sw=2.4, rx=25) + rect(-260, 230, 520, 50, "#e8dcc2", sw=2.4, rx=25)
    for i in range(7): g += f'<path d="M-170,{-220+i*55} h{340 - (90 if i==6 else (i*13)%60)}" stroke="#9b9388" stroke-width="7" stroke-linecap="round"/>'
    g += f'<path d="M110,140 l-30,110 l30,-25 l30,25z" fill="{ribbon}" stroke="{INK}" stroke-width="2"/>'
    g += f'<circle cx="110" cy="150" r="48" fill="#e2b84f" stroke="{INK}" stroke-width="2.4"/><circle cx="110" cy="150" r="30" fill="none" stroke="#b88e3a" stroke-width="4"/>'
    return f'<g transform="translate({x},{y}) scale({s})">{g}</g>'

def fruit_tree(x, y, s=1.0, seed=0, ripe=0.0, n=16):
    """kit2 tree + apricots; ripe 0 = small green, 1 = big orange."""
    r = random.Random(seed + 100); g = tree(x, y, s, seed=seed)
    col = ["#9fb36a", "#d6b04a", "#e9973f"][0 if ripe < 0.3 else (1 if ripe < 0.7 else 2)]
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0.2, 0.95)
        fx_ = x + math.cos(a) * 80 * s * d; fy = y - 195 * s + math.sin(a) * 60 * s * d
        rr = (6 + 6 * ripe) * s
        g += f'<circle cx="{fx_:.1f}" cy="{fy:.1f}" r="{rr:.1f}" fill="{col}" stroke="{INK}" stroke-width="1.2"/>'
        if ripe > 0.6: g += f'<circle cx="{fx_-rr*0.3:.1f}" cy="{fy-rr*0.3:.1f}" r="{rr*0.3:.1f}" fill="#f8d3a0"/>'
    return g

def child(x, y, s=1.0, reach=False, coat="#c46f55"):
    """Small faceless boy (no kufi), optionally both arms raised (reaching up). Simple shapes, no fingers."""
    g = man(x, y, s * 0.55, back=True, cap=False, coat=coat)
    if reach:
        h = 300 * s * 0.55
        for sgn in (-1, 1):
            g += poly([(x + sgn * 16 * s, y - h * 0.8), (x + sgn * 30 * s, y - h * 1.15), (x + sgn * 22 * s, y - h * 1.18), (x + sgn * 8 * s, y - h * 0.78)], coat, sw=1.6)
    return g

def desert_road(cam, road=2.6, z0=1.0, z1=500, bends=False):
    """Packed-sand road straight to the vanishing point (shared camera), with stones and wheel ruts."""
    from world import quad
    r = random.Random(7); g = ""
    g += quad(cam, [(-200, 0, z1), (200, 0, z1), (200, 0, z0), (-200, 0, z0)], SAND, sw=0)
    g += quad(cam, [(-road, 0, z1), (road, 0, z1), (road, 0, z0), (-road, 0, z0)], "#e9dcc0", sw=1.2)
    for X in (-0.9, 0.9):
        g += quad(cam, [(X - .12, 0.01, z1), (X + .12, 0.01, z1), (X + .12, 0.01, z0), (X - .12, 0.01, z0)], "#d8c7a5", sw=0)
    for _ in range(60):
        X = r.choice([-1, 1]) * r.uniform(road + 0.3, 14); Z = r.uniform(2, 90)
        x, y = cam.project(X, 0, Z); rr = cam.scale(Z) * r.uniform(0.12, 0.3)
        g += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rr:.1f}" ry="{rr*0.45:.1f}" fill="{r.choice([SAND3, "#bfa984", STONE2])}" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.5"/>'
    return g

def dunes(y, seed=3):
    return (f'<path d="M0,{y} q220,-120 470,-40 q260,80 470,-30 q170,-60 302,-10 L{SW},{y+700} L0,{y+700}z" fill="{SAND2}" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M0,{y+90} q300,-70 600,10 q330,80 642,-20 L{SW},{y+800} L0,{y+800}z" fill="{SAND}" stroke="{INK}" stroke-width="2"/>')

def palm(x, y, s=1.0, seed=0):
    r = random.Random(seed)
    g = f'<path d="M{x-10*s},{y} Q{x+20*s},{y-200*s} {x+5*s},{y-380*s} L{x+20*s},{y-380*s} Q{x+40*s},{y-200*s} {x+12*s},{y}z" fill="#8a6a55" stroke="{INK}" stroke-width="2"/>'
    for i in range(8):
        a = -math.pi / 2 + (i - 3.5) * 0.42 + r.uniform(-.08, .08); L = r.uniform(150, 190) * s
        ex, ey = x + 12 * s + math.cos(a) * L, y - 380 * s + math.sin(a) * L * 0.7 + 60 * s
        mx, my = x + 12 * s + math.cos(a) * L * 0.5, y - 380 * s + math.sin(a) * L * 0.5 - 20 * s
        g += f'<path d="M{x+12*s},{y-380*s} Q{mx},{my-30*s} {ex},{ey} Q{mx},{my+10*s} {x+12*s},{y-372*s}z" fill="{r.choice(["#7f9a5b","#6c8a4e","#93ad6a"])}" stroke="{INK}" stroke-width="1.4"/>'
    return g

def tents(x, y, n=4, s=1.0, seed=2):
    r = random.Random(seed); g = ""
    for i in range(n):
        tx = x + i * 170 * s + r.uniform(-20, 20) * s; ts = s * r.uniform(0.8, 1.1)
        g += poly([(tx - 80 * ts, y), (tx, y - 110 * ts), (tx + 80 * ts, y)], r.choice(["#f1ece0", "#e6dccb", "#d9c7a8"]), sw=1.8)
        g += poly([(tx - 18 * ts, y), (tx, y - 60 * ts), (tx + 18 * ts, y)], "#6b5545", sw=1.4)
    return g
