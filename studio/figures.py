"""More natural faceless figures: articulated limbs, hair, hands, clothing; poses driven by joint angles."""
import math
INK = "#3b3a48"; SKIN = "#d9a98a"; HAIR = "#2b2523"

def _pt(x, y, ang, L):  # angle in degrees, 0 = straight down
    a = math.radians(ang); return x + L * math.sin(a), y + L * math.cos(a)

def limb(x0, y0, x1, y1, w0, w1, fill, sw=2):
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    p = [(x0 + nx * w0, y0 + ny * w0), (x1 + nx * w1, y1 + ny * w1), (x1 - nx * w1, y1 - ny * w1), (x0 - nx * w0, y0 - ny * w0)]
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in p)
    g = f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{w0:.1f}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>'
    g += f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="{w1:.1f}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>'
    g += f'<polygon points="{pts}" fill="{fill}" stroke="none"/>'
    g += f'<line x1="{p[0][0]:.1f}" y1="{p[0][1]:.1f}" x2="{p[1][0]:.1f}" y2="{p[1][1]:.1f}" stroke="{INK}" stroke-width="{sw}"/>'
    g += f'<line x1="{p[3][0]:.1f}" y1="{p[3][1]:.1f}" x2="{p[2][0]:.1f}" y2="{p[2][1]:.1f}" stroke="{INK}" stroke-width="{sw}"/>'
    return g

def hand(x, y, ang, s, open_=False):
    g = f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{7*s:.1f}" ry="{10*s:.1f}" fill="{SKIN}" stroke="{INK}" stroke-width="1.6" transform="rotate({-ang:.1f} {x:.1f} {y:.1f})"/>'
    tx, ty = _pt(x, y, ang - 50, 9 * s)
    g += f'<ellipse cx="{tx:.1f}" cy="{ty:.1f}" rx="{3*s:.1f}" ry="{6*s:.1f}" fill="{SKIN}" stroke="{INK}" stroke-width="1.3" transform="rotate({-(ang-50):.1f} {tx:.1f} {ty:.1f})"/>'
    if open_:
        for k in (-12, 0, 12):
            fx, fy = _pt(x, y, ang + k, 13 * s)
            g += f'<ellipse cx="{fx:.1f}" cy="{fy:.1f}" rx="{2.6*s:.1f}" ry="{6*s:.1f}" fill="{SKIN}" stroke="{INK}" stroke-width="1.2" transform="rotate({-(ang+k):.1f} {fx:.1f} {fy:.1f})"/>'
    return g

def person(x, y, s=1.0, pose=None, view="side", facing=1, gender="m", coat="#556078", pants="#4d505c",
           dress="#3f6b4c", scarf="#e8e6e0", cap=True):
    """(x,y) feet on ground. pose: dict of joint angles (deg, 0=down): ls,le (left shoulder/elbow), rs,re, lh,lk, rh,rk, lean."""
    P = dict(ls=8, le=10, rs=-8, re=-4, lh=4, lk=0, rh=-4, rk=0, lean=0)
    if pose: P.update(pose)
    f = facing
    if view != "side":  # seen from behind/front: legs swing toward/away from camera, not sideways
        P["lh"], P["rh"] = P["lh"] * 0.15, P["rh"] * 0.15
        P["ls"], P["rs"] = (P["ls"] * 0.3, P["rs"] * 0.3) if abs(P["ls"]) < 60 else (P["ls"], P["rs"])
    thigh, shin, upper, fore = 62 * s, 60 * s, 48 * s, 44 * s
    hip_y = y - (thigh + shin) - 10 * s
    lean = P["lean"] * f
    hx, hy = x, hip_y
    sx, sy = _pt(hx, hy, 180 + lean, 98 * s)  # shoulders
    head_x, head_y = _pt(sx, sy, 180 + lean, 30 * s)
    g = f'<ellipse cx="{x}" cy="{y+2*s}" rx="{48*s}" ry="{8*s}" fill="#000" opacity="0.16"/>'

    def leg(ha, ka, col, far):
        hx0 = hx + ((-11 if far else 11) * s if view != "side" else 0)
        lift = (ka / 28.0) * 14 * s if view != "side" else 0
        kx, ky = _pt(hx0, hy - lift, ha * f, thigh)
        if view != "side": ka = 0
        ax, ay = _pt(kx, ky, (ha - abs(ka)) * f if ka else ha * f, shin)
        out = limb(hx0, hy - lift, kx, ky, 15 * s, 12 * s, col) + limb(kx, ky, ax, ay, 12 * s, 9 * s, col)
        out += f'<path d="M{ax-8*s*f:.1f},{ay-4*s:.1f} q{20*s*f:.1f},{-6*s:.1f} {30*s*f:.1f},{4*s:.1f} l0,{6*s:.1f} l{-34*s*f:.1f},0z" fill="#2e2a2a" stroke="{INK}" stroke-width="1.5"/>'
        return out

    def arm(sa, ea, col, open_=False, side=0):
        ox = side * 22 * s if view != "side" else 0
        ax0 = sx + ox
        ex, ey = _pt(ax0, sy + 6 * s, sa * f, upper)
        wx, wy = _pt(ex, ey, (sa + ea) * f, fore)
        return limb(ax0, sy + 6 * s, ex, ey, 11 * s, 9 * s, col) + limb(ex, ey, wx, wy, 9 * s, 7 * s, col) + hand(wx, wy, (sa + ea) * f, s, open_)

    far_leg, near_leg = ("lh", "lk"), ("rh", "rk")
    if gender == "m":
        g += leg(P["lh"], P["lk"], "#43464f", True)
        g += arm(P["ls"], P["le"], "#4a5469" if view == "side" else coat, P.get("open_hands", False), -1)
        g += leg(P["rh"], P["rk"], pants, False)
        # torso (coat with slight taper and hem)
        tw = 17 if view == "side" else 28
        tl, tr = _pt(sx, sy, 270, tw * s), _pt(sx, sy, 90, tw * s)
        bl, br = _pt(hx, hy + 14 * s, 270, (tw - 2) * s), _pt(hx, hy + 14 * s, 90, (tw - 2) * s)
        g += f'<path d="M{tl[0]:.1f},{tl[1]+8*s:.1f} Q{sx:.1f},{sy-6*s:.1f} {tr[0]:.1f},{tr[1]+8*s:.1f} L{br[0]:.1f},{br[1]:.1f} Q{hx:.1f},{hy+22*s:.1f} {bl[0]:.1f},{bl[1]:.1f}z" fill="{coat}" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
        g += f'<path d="M{sx:.1f},{sy+4*s:.1f} L{hx+2*s*f:.1f},{hy+14*s:.1f}" stroke="{INK}" stroke-width="1.2" opacity="0.5"/>'
        g += limb(sx, sy + 2 * s, head_x, head_y + 16 * s, 6 * s, 6 * s, SKIN, 1.2)  # neck
        g += f'<ellipse cx="{head_x:.1f}" cy="{head_y:.1f}" rx="{17*s:.1f}" ry="{21*s:.1f}" fill="{SKIN}" stroke="{INK}" stroke-width="2"/>'
        # hair: back of head + short sideburn, covers the face side for 'back' view
        if view == "back":
            g += f'<ellipse cx="{head_x:.1f}" cy="{head_y+1*s:.1f}" rx="{17*s:.1f}" ry="{20*s:.1f}" fill="{HAIR}" stroke="{INK}" stroke-width="2"/>'
        else:
            g += f'<path d="M{head_x-17*s*f:.1f},{head_y+6*s:.1f} A{17*s:.1f},{20*s:.1f} 0 0 {1 if f>0 else 0} {head_x+6*s*f:.1f},{head_y-20*s:.1f} Q{head_x-2*s*f:.1f},{head_y-4*s:.1f} {head_x-6*s*f:.1f},{head_y+12*s:.1f}z" fill="{HAIR}"/>'
            g += f'<ellipse cx="{head_x-3*s*f:.1f}" cy="{head_y+2*s:.1f}" rx="{3*s:.1f}" ry="{5*s:.1f}" fill="#c99478"/>'  # ear
        if cap:
            g += f'<path d="M{head_x-17*s:.1f},{head_y-8*s:.1f} Q{head_x:.1f},{head_y-30*s:.1f} {head_x+17*s:.1f},{head_y-8*s:.1f} Q{head_x:.1f},{head_y-12*s:.1f} {head_x-17*s:.1f},{head_y-8*s:.1f}z" fill="#f4f1ea" stroke="{INK}" stroke-width="1.8"/>'
        g += arm(P["rs"], P["re"], coat, P.get("open_hands", False), 1)
    else:
        g += leg(P["lh"], P["lk"], "#2e2a2a", True) + leg(P["rh"], P["rk"], "#2e2a2a", False)
        g += arm(P["ls"], P["le"], dress, P.get("open_hands", False), -1)
        bl, br = _pt(x, y - 8 * s, 270, 40 * s), _pt(x, y - 8 * s, 90, 40 * s)
        g += f'<path d="M{sx-24*s:.1f},{sy+10*s:.1f} Q{sx:.1f},{sy-4*s:.1f} {sx+24*s:.1f},{sy+10*s:.1f} L{br[0]:.1f},{br[1]:.1f} Q{x:.1f},{y:.1f} {bl[0]:.1f},{bl[1]:.1f}z" fill="{dress}" stroke="{INK}" stroke-width="2.2"/>'
        g += f'<path d="M{head_x-24*s:.1f},{head_y+4*s:.1f} Q{head_x-26*s:.1f},{head_y-30*s:.1f} {head_x:.1f},{head_y-28*s:.1f} Q{head_x+26*s:.1f},{head_y-30*s:.1f} {head_x+24*s:.1f},{head_y+4*s:.1f} Q{head_x+34*s:.1f},{sy+30*s:.1f} {head_x:.1f},{sy+40*s:.1f} Q{head_x-34*s:.1f},{sy+30*s:.1f} {head_x-24*s:.1f},{head_y+4*s:.1f}z" fill="{scarf}" stroke="{INK}" stroke-width="2"/>'
        if view != "back":
            g += f'<ellipse cx="{head_x+5*s*f:.1f}" cy="{head_y+4*s:.1f}" rx="{11*s:.1f}" ry="{14*s:.1f}" fill="{SKIN}" stroke="{INK}" stroke-width="1.4"/>'
        g += arm(P["rs"], P["re"], dress, P.get("open_hands", False), 1)
    return g

def walk_pose(ph):
    """natural walk cycle, ph in radians."""
    sw = math.sin(ph)
    return dict(lh=22 * sw, lk=max(0, 28 * math.sin(ph + 1.2)), rh=-22 * sw, rk=max(0, 28 * math.sin(ph + 1.2 + math.pi)),
                ls=-20 * sw, le=-12 - 8 * max(0, -sw), rs=20 * sw, re=-12 - 8 * max(0, sw), lean=4)

def idle_pose(ph):
    b = math.sin(ph)
    return dict(lh=3, rh=-3, ls=6 + 2 * b, le=8, rs=-6 - 2 * b, re=-6, lean=1 * b)

def dua_pose(ph):
    return dict(lh=3, rh=-3, ls=25 + 2 * math.sin(ph), le=125, rs=25 + 2 * math.sin(ph), re=125, open_hands=True)
