"""SVG illustration kit in the reference style: cream houses, stairs, blue doors, lanterns, flowers, faceless figures."""
import random, subprocess

SW, SH = 1242, 2208  # 1.15x of 1080x1920, room for camera moves
INK = "#3b3a48"
WALL, WALL2, WALL3 = "#ece6dc", "#d9d1c8", "#c7bfbf"
DOOR = "#6d86ab"; WOOD = "#8a6a55"

def defs():
    return f'''<defs>
<linearGradient id="nightsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f3156"/><stop offset="0.6" stop-color="#5b5880"/><stop offset="1" stop-color="#8d86a3"/></linearGradient>
<linearGradient id="dawnsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7d7896"/><stop offset="0.5" stop-color="#c9b9b0"/><stop offset="1" stop-color="#ead8bf"/></linearGradient>
<linearGradient id="daysky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fb3c6"/><stop offset="1" stop-color="#e3e3dc"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#ffd98a" stop-opacity="0.85"/><stop offset="0.35" stop-color="#ffc96b" stop-opacity="0.35"/><stop offset="1" stop-color="#ffc96b" stop-opacity="0"/></radialGradient>
<radialGradient id="dusk" cx="0.5" cy="0.3" r="0.8"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="1" stop-color="#3c3a5c" stop-opacity="0.35"/></radialGradient>
<filter id="soft"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="wc" x="0" y="0" width="1" height="1"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="4"/><feColorMatrix values="0 0 0 0 0.25  0 0 0 0 0.24  0 0 0 0 0.32  0 0 0 0.10 0"/><feComposite in2="SourceGraphic" operator="in"/><feBlend in="SourceGraphic" mode="multiply"/></filter>
</defs>'''

def svg(body, sky="nightsky", night=True):
    over = '<rect width="100%" height="100%" fill="url(#dusk)"/>' if night else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}" height="{SH}" viewBox="0 0 {SW} {SH}">{defs()}'
            f'<g filter="url(#wc)"><rect width="100%" height="100%" fill="url(#{sky})"/>{body}{over}</g></svg>')

def render(svg_text, png):
    open(png[:-4] + ".svg", "w").write(svg_text)
    subprocess.run(["rsvg-convert", "-w", str(SW), "-h", str(SH), png[:-4] + ".svg", "-o", png], check=True)

def poly(pts, fill, stroke=INK, sw=2.2, op=1):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" opacity="{op}"/>'

def rect(x, y, w, h, fill, stroke=INK, sw=2.2, rx=0):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def clouds(y, n=4, col="#d9d6e6", op=0.55, seed=1):
    r = random.Random(seed); out = ""
    for _ in range(n):
        x = r.uniform(-100, SW); w = r.uniform(250, 520); h = r.uniform(28, 55); yy = y + r.uniform(-60, 60)
        out += f'<path d="M{x},{yy} q{w*0.2},{-h} {w*0.45},{-h*0.4} q{w*0.2},{-h*0.9} {w*0.4},{-h*0.1} q{w*0.15},{h*0.2} {w*0.15},{h*0.5} z" fill="{col}" opacity="{op}" stroke="{INK}" stroke-width="1.5"/>'
    return out

def window(x, y, w, h, shut=True):
    s = rect(x, y, w, h, "#4d5770" if not shut else DOOR)
    if shut:
        s += f'<line x1="{x+w/2}" y1="{y}" x2="{x+w/2}" y2="{y+h}" stroke="{INK}" stroke-width="2"/>'
        for k in range(1, 6):
            s += f'<line x1="{x+4}" y1="{y+h*k/6}" x2="{x+w-4}" y2="{y+h*k/6}" stroke="#56698a" stroke-width="1.5"/>'
    return s

def door(x, y, w, h, col=DOOR):
    s = rect(x, y, w, h, col, rx=3)
    s += rect(x + w*0.14, y + h*0.08, w*0.72, h*0.36, "none", sw=1.6)
    s += rect(x + w*0.14, y + h*0.52, w*0.72, h*0.38, "none", sw=1.6)
    s += f'<circle cx="{x+w*0.82}" cy="{y+h*0.5}" r="4" fill="{INK}"/>'
    return s

def lantern(x, y, s=1.0, lit=True):
    g = f'<circle cx="{x}" cy="{y+30*s}" r="{140*s}" fill="url(#glow)"/>' if lit else ""
    g += f'<path d="M{x-45*s},{y-40*s} q{-10*s},{-35*s} {30*s},{-40*s} l{15*s},0 l0,{40*s}" fill="none" stroke="{INK}" stroke-width="{3*s}"/>'
    g += poly([(x-18*s, y), (x+18*s, y), (x+14*s, y+60*s), (x-14*s, y+60*s)], "#ffe3a1" if lit else "#7a7f93", sw=2.5*s)
    g += poly([(x-24*s, y), (x, y-16*s), (x+24*s, y)], "#3f3f4f", sw=2*s)
    g += f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+60*s}" stroke="{INK}" stroke-width="{1.5*s}"/>'
    return g

def pot(x, y, s=1.0, seed=0, flowers=True):
    r = random.Random(seed)
    g = poly([(x-22*s, y-34*s), (x+22*s, y-34*s), (x+16*s, y), (x-16*s, y)], "#b9785a", sw=1.8*s)
    if flowers:
        for _ in range(7):
            lx, ly = x + r.uniform(-30, 30)*s, y - 34*s - r.uniform(5, 45)*s
            g += f'<ellipse cx="{lx}" cy="{ly}" rx="{9*s}" ry="{5*s}" fill="#5f8a55" stroke="{INK}" stroke-width="1" transform="rotate({r.uniform(-50,50)} {lx} {ly})"/>'
        for _ in range(4):
            fx, fy = x + r.uniform(-24, 24)*s, y - 34*s - r.uniform(15, 50)*s
            g += f'<circle cx="{fx}" cy="{fy}" r="{7*s}" fill="{r.choice(["#d04a7a","#e06b8f","#c43d55","#f2a1b8"])}" stroke="{INK}" stroke-width="1"/>'
    return g

def man(x, y, s=1.0, back=True, walk=0.0, cap=True, coat="#556078"):
    """Faceless man in kufi; (x,y) = feet center."""
    h = 300 * s
    g = f'<ellipse cx="{x}" cy="{y}" rx="{55*s}" ry="{10*s}" fill="#000" opacity="0.15"/>'
    lx = walk * 22 * s
    g += poly([(x-22*s, y-h*0.47), (x-2*s, y-h*0.47), (x-6*s+lx, y-4*s), (x-24*s+lx, y-4*s)], "#6b6f78")
    g += poly([(x+2*s, y-h*0.47), (x+22*s, y-h*0.47), (x+24*s-lx, y-4*s), (x+6*s-lx, y-4*s)], "#6b6f78")
    g += poly([(x-36*s, y-h*0.82), (x+36*s, y-h*0.82), (x+32*s, y-h*0.45), (x-32*s, y-h*0.45)], coat)
    g += poly([(x-36*s, y-h*0.80), (x-46*s, y-h*0.55), (x-38*s, y-h*0.5), (x-30*s, y-h*0.72)], coat)
    g += poly([(x+36*s, y-h*0.80), (x+46*s, y-h*0.55), (x+38*s, y-h*0.5), (x+30*s, y-h*0.72)], coat)
    g += f'<ellipse cx="{x}" cy="{y-h*0.9}" rx="{19*s}" ry="{23*s}" fill="#d9a98a" stroke="{INK}" stroke-width="2"/>'
    if back: g += f'<path d="M{x-19*s},{y-h*0.9} a{19*s},{23*s} 0 0 1 {38*s},0 l0,{10*s} q{-19*s},{10*s} {-38*s},0z" fill="#2e2a2a"/>'
    if cap: g += f'<path d="M{x-19*s},{y-h*0.92} a{19*s},{16*s} 0 0 1 {38*s},0 z" fill="#f4f1ea" stroke="{INK}" stroke-width="2"/>'
    return g

def woman(x, y, s=1.0, dress="#3f6b4c", scarf="#e8e6e0"):
    h = 310 * s
    g = f'<ellipse cx="{x}" cy="{y}" rx="{55*s}" ry="{10*s}" fill="#000" opacity="0.15"/>'
    g += poly([(x-26*s, y-h*0.72), (x+26*s, y-h*0.72), (x+34*s, y-2*s), (x-34*s, y-2*s)], dress)
    g += f'<path d="M{x-28*s},{y-h*0.66} q{0},{-h*0.32} {28*s},{-h*0.32} q{28*s},0 {28*s},{h*0.32} q{-28*s},{h*0.08} {-56*s},0z" fill="{scarf}" stroke="{INK}" stroke-width="2"/>'
    return g

def stairs(x0, y0, x1, y1, wb, wt, n=22, col="#e6e0d6"):
    """Stairs from bottom (x0,y0,width wb) to top (x1,y1,width wt) in perspective."""
    g = ""
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        k0, k1 = t0 ** 0.8, t1 ** 0.8
        ya, yb = y0 + (y1 - y0) * k0, y0 + (y1 - y0) * k1
        xa, xb = x0 + (x1 - x0) * k0, x0 + (x1 - x0) * k1
        wa, wbb = wb + (wt - wb) * k0, wb + (wt - wb) * k1
        mid = ya + (yb - ya) * 0.45
        g += poly([(xa - wa/2, ya), (xa + wa/2, ya), (xa + wa/2, mid), (xa - wa/2, mid)], "#d4cdc3", sw=1.4)
        g += poly([(xa - wa/2, mid), (xa + wa/2, mid), (xb + wbb/2, yb), (xb - wbb/2, yb)], col, sw=1.4)
    return g

def car(x, y, s=1.0, col="#355078", tilt=0):
    g = f'<g transform="rotate({tilt} {x} {y})">'
    g += f'<ellipse cx="{x}" cy="{y+6*s}" rx="{170*s}" ry="{16*s}" fill="#000" opacity="0.18"/>'
    g += f'<path d="M{x-165*s},{y-20*s} l0,{-45*s} q{10*s},{-25*s} {60*s},{-28*s} l{30*s},{-45*s} q{75*s},{-14*s} {150*s},0 l{40*s},{45*s} q{50*s},{5*s} {50*s},{30*s} l0,{43*s} z" fill="{col}" stroke="{INK}" stroke-width="3"/>'
    g += f'<path d="M{x-62*s},{y-96*s} l{22*s},{-32*s} q{55*s},{-10*s} {110*s},0 l{28*s},{32*s}z" fill="#c9d6e3" stroke="{INK}" stroke-width="2"/>'
    for wx in (-100, 100):
        g += f'<circle cx="{x+wx*s}" cy="{y-18*s}" r="{30*s}" fill="#2b2b33" stroke="{INK}" stroke-width="2"/><circle cx="{x+wx*s}" cy="{y-18*s}" r="{13*s}" fill="#9aa0ad"/>'
    return g + "</g>"
