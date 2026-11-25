"""Sedan built as a simple 3D model and projected with real perspective, so front, side, hood and roof always meet
correctly (no 'broken' car). Draws front + one side like a car seen from the roadside.
car3d(x, y, s, yaw, side) -> SVG. (x,y) = ground point under the car centre; s = scale (1.0 ~ 600 px long)."""
import math
INK = "#3b3a48"

def _proj(p, yaw, pitch, dist, f):
    x, y, z = p
    c, s_ = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s_ * z, -s_ * x + c * z           # yaw around vertical axis
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = cp * y - sp * z, sp * y + cp * z           # pitch (camera slightly above)
    z = dist - z                                      # camera looks along -z toward the car
    return f * x / z, -f * y / z, z

def _poly(pts, fill, sw=2.0, op=1.0, stroke=INK):
    d = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" opacity="{op}"/>'

def _lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def _bil(q, u, v):  # point on a 3D quad q=[p00,p10,p11,p01] at (u,v)
    return _lerp(_lerp(q[0], q[1], u), _lerp(q[3], q[2], u), v)

def car3d(x, y, s=1.0, yaw_deg=32, side=1, body="#f1efe8", shade="#d6d3ca", flowers=True, ribbon=True, uid="k", world=None):
    yaw = math.radians(yaw_deg) * side; pitch = math.radians(12); dist = 8.0; f = 1150 * s
    vis = -side
    if world: vis = 1 if world[1] < 0 else -1
    W, Lh = 0.86, 2.25                      # half width, half length (metres)
    yb, yw, yh, yr = 0.22, 0.62, 0.80, 1.36  # bottom, belt, hood top, roof
    zf, zh, zw, zr0, zr1, zt, zb = 2.25, 2.12, 0.95, 0.35, -0.85, -1.35, -2.25
    sx = W * vis  # visible side x (faces the camera)
    P = lambda p: _proj(p, yaw, pitch, dist, f)
    def S(p):
        a, b, _ = P(p); return (x + a, y + b - P((0, 0, 0))[1] * 0)
    g0 = P((0, 0, 0)); oy = y - g0[1]; ox = x - g0[0]
    def T(p):
        if world:  # world = (cam, X, Z, heading_deg): project in the shared street camera
            cam, WX, WZ, hd = world
            c_, s_ = math.cos(math.radians(hd)), math.sin(math.radians(hd))
            lx, ly, lz = p
            wx, wz = WX + c_ * lx + s_ * lz, WZ - (-s_ * lx + c_ * lz)
            return cam.project(wx, ly, wz)
        a, b, _ = P(p); return (ox + a, oy + b)
    def poly3(pts3, fill, **kw): return _poly([T(p) for p in pts3], fill, **kw)
    g = ""
    # shadow
    sh = [T((-W - .1, 0, zf + .2)), T((W + .1, 0, zf + .2)), T((W + .1, 0, zb - .1)), T((-W - .1, 0, zb - .1))]
    g += _poly(sh, "#000", sw=0, op=0.16, stroke="none")
    # far-side wheels peek (drawn first)
    # side body (lower), from front to back on the visible side
    side_lower = [(sx, yb, zf - .05), (sx, yb, zb + .05), (sx, yh - .02, zb), (sx, yh, zf - .1)]
    g += poly3(side_lower, shade)
    # wheel arches + wheels on the visible side
    for wz in (1.45, -1.45):
        pts = []
        for k in range(18):
            a = 2 * math.pi * k / 18
            pts.append(T((sx + 0.02 * vis, 0.34 + 0.33 * math.cos(a), wz + 0.33 * math.sin(a))))
        g += _poly(pts, "#2b2b31", sw=1.8)
        rim = [T((sx + 0.04 * vis, 0.34 + 0.17 * math.cos(2 * math.pi * k / 14), wz + 0.17 * math.sin(2 * math.pi * k / 14))) for k in range(14)]
        g += _poly(rim, "#b7bac1", sw=1.2)
    # door lines + handles on the side
    for dz in (0.95, -0.25):
        g += f'<line x1="{T((sx, yb+.05, dz))[0]:.1f}" y1="{T((sx, yb+.05, dz))[1]:.1f}" x2="{T((sx, yh-.02, dz))[0]:.1f}" y2="{T((sx, yh-.02, dz))[1]:.1f}" stroke="#a8a59c" stroke-width="1.6"/>'
    for hz in (0.65, -0.55):
        g += poly3([(sx, .62, hz), (sx, .62, hz - .18), (sx, .66, hz - .18), (sx, .66, hz)], "#9b9890", sw=0.8)
    g += f'<line x1="{T((sx,.45,zf-.1))[0]:.1f}" y1="{T((sx,.45,zf-.1))[1]:.1f}" x2="{T((sx,.45,zb+.1))[0]:.1f}" y2="{T((sx,.45,zb+.1))[1]:.1f}" stroke="#bdbab1" stroke-width="1.5"/>'
    # trunk top, hood top
    g += poly3([(-W, yh - .02, zt), (W, yh - .02, zt), (W, yh - .02, zb), (-W, yh - .02, zb)], "#e7e5de")
    hood = [(-W, yh, zw), (W, yh, zw), (W, yh - .06, zf - .08), (-W, yh - .06, zf - .08)]
    g += poly3(hood, body)
    # front face
    front = [(-W, yb, zf), (W, yb, zf), (W, yh - .06, zf - .08), (-W, yh - .06, zf - .08)]
    g += poly3(front, "#e9e7e0")
    # cabin: side window band, windshield, roof
    rW = W - 0.08
    g += poly3([(sx, yh, zw), (sx, yh, zt), (rW * vis, yr, zr1), (rW * vis, yr, zr0)], "#e9e7e0")       # c-pillar/side frame
    g += poly3([(sx * 0.99, yh + .05, zw - .12), (sx * 0.99, yh + .05, zt + .12), (rW * vis * 0.99, yr - .05, zr1 + .08), (rW * vis * 0.99, yr - .05, zr0 - .06)], "#6f8496", sw=1.6)
    g += f'<line x1="{T((sx, yh+.05, -0.25))[0]:.1f}" y1="{T((sx, yh+.05, -0.25))[1]:.1f}" x2="{T((rW*side, yr-.05, -0.3))[0]:.1f}" y2="{T((rW*side, yr-.05, -0.3))[1]:.1f}" stroke="#e9e7e0" stroke-width="{5*s:.1f}"/>'
    ws = [(-W, yh, zw), (W, yh, zw), (rW, yr, zr0), (-rW, yr, zr0)]
    g += poly3(ws, "#e9e7e0")
    wsg = [_bil(ws, .06, .06), _bil(ws, .94, .06), _bil(ws, .94, .92), _bil(ws, .06, .92)]
    g += poly3(wsg, "#5d7385", sw=1.6)
    g += poly3([_bil(ws, .22, .1), _bil(ws, .36, .1), _bil(ws, .2, .85), _bil(ws, .1, .85)], "#ffffff", sw=0, op=0.25, stroke="none")
    g += poly3([(-rW, yr, zr0), (rW, yr, zr0), (rW, yr, zr1), (-rW, yr, zr1)], body)
    # front details via the front quad
    fq = front
    def fpoly(uv, fill, sw=1.4, op=1): return poly3([_bil(fq, u, v) for u, v in uv], fill, sw=sw, op=op)
    g += fpoly([(.05, .55), (.30, .55), (.30, .82), (.05, .78)], "#f4edc9")              # headlights
    g += fpoly([(.70, .55), (.95, .55), (.95, .78), (.70, .82)], "#f4edc9")
    g += fpoly([(.33, .58), (.67, .58), (.67, .80), (.33, .80)], "#3b3d45")               # grille
    for k in range(1, 4):
        v = .58 + k * .055; g += fpoly([(.34, v), (.66, v), (.66, v + .006), (.34, v + .006)], "#6d7079", sw=0)
    g += fpoly([(.02, .18), (.98, .18), (.98, .42), (.02, .42)], "#dcd9d1", sw=1.2)        # bumper
    g += fpoly([(.40, .22), (.60, .22), (.60, .36), (.40, .36)], "#f7f7f2", sw=1.0)        # plate
    g += fpoly([(.405, .24), (.43, .24), (.43, .34), (.405, .34)], "#3f6fb0", sw=0)
    # wedding decoration on the hood
    if ribbon:
        a, b, c = T(_bil(hood, .1, 0)), T(_bil(hood, .5, .9)), T(_bil(hood, .9, 0))
        g += f'<path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} L{c[0]:.1f},{c[1]:.1f}" stroke="#cf4558" stroke-width="{5*s:.1f}" fill="none" stroke-linejoin="round"/>'
    if flowers:
        import random
        r = random.Random(5)
        for k in range(16):
            px, py = T(_bil(hood, .5 + r.uniform(-.17, .17), .45 + r.uniform(-.17, .17)))
            rr = r.uniform(6, 9) * s
            g += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{rr:.1f}" fill="#c63b4d" stroke="#7d1f2c" stroke-width="0.8"/>'
        for k in range(8):
            px, py = T(_bil(hood, .5 + r.uniform(-.2, .2), .45 + r.uniform(-.2, .2)))
            g += f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="{8*s:.1f}" ry="{3.5*s:.1f}" fill="#5f8a55" transform="rotate({r.uniform(-40,40):.0f} {px:.1f} {py:.1f})"/>'
    # mirror on the visible side
    g += poly3([(sx, yh + .08, zw - .05), (sx + .18 * vis, yh + .1, zw - .02), (sx + .18 * vis, yh + .2, zw - .02), (sx, yh + .18, zw - .05)], "#e4e2db", sw=1.2)
    return g
