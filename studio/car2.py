"""Detailed front-3/4-facing sedan (like the white wedding cars in bashar.uz reels). Drawn in a 600x420 box, scaled by s.
(x, y) = ground point under the car's centre."""
INK = "#3b3a48"

def car_defs(uid="c"):
    return f'''
<linearGradient id="{uid}body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbfaf6"/><stop offset="0.55" stop-color="#ecebe5"/><stop offset="1" stop-color="#cfcdc5"/></linearGradient>
<linearGradient id="{uid}side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#d9d7cf"/><stop offset="1" stop-color="#f1f0ea"/></linearGradient>
<linearGradient id="{uid}glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5f7486"/><stop offset="0.6" stop-color="#8fa4b4"/><stop offset="1" stop-color="#b9c8d2"/></linearGradient>
<linearGradient id="{uid}refl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>
<radialGradient id="{uid}lamp"><stop offset="0" stop-color="#fffbe8"/><stop offset="0.6" stop-color="#f3ecd0"/><stop offset="1" stop-color="#c9c2a6"/></radialGradient>
<radialGradient id="{uid}rim"><stop offset="0" stop-color="#e9ebee"/><stop offset="0.7" stop-color="#a9adb5"/><stop offset="1" stop-color="#6d7078"/></radialGradient>'''

def rose(x, y, r):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#c63b4d" stroke="#7d1f2c" stroke-width="0.8"/>'
            f'<path d="M{x-r*0.5:.1f},{y:.1f} q{r*0.5:.1f},{-r*0.7:.1f} {r:.1f},0" stroke="#e3707f" stroke-width="{r*0.25:.1f}" fill="none"/>'
            f'<ellipse cx="{x+r*0.9:.1f}" cy="{y+r*0.6:.1f}" rx="{r*0.6:.1f}" ry="{r*0.3:.1f}" fill="#5f8a55"/>')

def sedan34(x, y, s=1.0, uid="c", flowers=True, ribbon=True, plate=True):
    """Car facing the viewer, slightly turned (front + left side visible)."""
    T = f'translate({x - 300*s:.1f},{y - 400*s:.1f}) scale({s:.4f})'
    g = f'<g transform="{T}">'
    g += '<ellipse cx="300" cy="400" rx="300" ry="26" fill="#000" opacity="0.18"/>'
    # left side panel (visible side, receding)
    g += f'<path d="M40,334 L42,258 Q50,220 96,212 L190,196 L150,200 L150,356 L62,356 Q40,354 40,334z" fill="url(#{uid}side)" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
    g += f'<path d="M190,196 L235,118 L150,132 Q112,140 92,170 L70,210z" fill="#f1f0ea" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>'
    g += f'<path d="M186,192 L226,126 L156,138 Q122,146 104,172 L86,204z" fill="url(#{uid}glass)" stroke="{INK}" stroke-width="1.8"/>'
    g += f'<line x1="140" y1="136" x2="128" y2="200" stroke="{INK}" stroke-width="3"/>'
    g += f'<line x1="44" y1="282" x2="150" y2="278" stroke="#b9b7af" stroke-width="2"/>'
    # rear wheel (side)
    g += f'<ellipse cx="88" cy="352" rx="30" ry="40" fill="#2c2c33" stroke="{INK}" stroke-width="2"/><ellipse cx="90" cy="352" rx="15" ry="22" fill="url(#{uid}rim)"/>'
    # front body block
    g += f'<path d="M150,196 Q300,180 540,196 Q575,202 580,240 L585,330 Q585,360 560,364 L170,364 Q150,362 150,340z" fill="url(#{uid}body)" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round"/>'
    # roof + windshield
    g += f'<path d="M190,196 L235,118 Q330,104 445,118 L505,196 Q350,184 190,196z" fill="#f4f3ee" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
    g += f'<path d="M205,192 L246,126 Q330,114 438,126 L488,192 Q350,180 205,192z" fill="url(#{uid}glass)" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M232,186 L262,132 L300,128 L262,186z" fill="url(#{uid}refl)"/>'
    g += f'<path d="M350,124 L322,186 L340,186 L366,124z" fill="#ffffff" opacity="0.25"/>'
    # mirrors
    g += f'<path d="M160,196 l-22,-10 l-6,20 l24,6z" fill="#e9e8e2" stroke="{INK}" stroke-width="1.6"/><path d="M530,196 l24,-8 l6,20 l-26,6z" fill="#e9e8e2" stroke="{INK}" stroke-width="1.6"/>'
    # hood crease lines
    g += f'<path d="M210,206 Q300,236 345,300" stroke="#c9c7bf" stroke-width="2" fill="none"/><path d="M480,206 Q420,236 395,300" stroke="#c9c7bf" stroke-width="2" fill="none"/>'
    # headlights
    g += f'<path d="M168,262 L248,272 L246,300 L172,294 Q162,280 168,262z" fill="url(#{uid}lamp)" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M570,262 L492,272 L494,300 L566,294 Q576,280 570,262z" fill="url(#{uid}lamp)" stroke="{INK}" stroke-width="2"/>'
    g += f'<circle cx="208" cy="283" r="9" fill="#fffdf0" stroke="#bdb59a" stroke-width="1"/><circle cx="532" cy="283" r="9" fill="#fffdf0" stroke="#bdb59a" stroke-width="1"/>'
    # grille + emblem
    g += f'<path d="M262,276 L478,276 L470,312 L270,312z" fill="#3a3c44" stroke="{INK}" stroke-width="2"/>'
    for k in range(1, 5):
        yy = 276 + k * 7.2
        g += f'<line x1="{264+k*1.5}" y1="{yy:.1f}" x2="{476-k*1.5}" y2="{yy:.1f}" stroke="#6b6e78" stroke-width="1.4"/>'
    g += f'<ellipse cx="370" cy="294" rx="13" ry="9" fill="#cfd3d8" stroke="{INK}" stroke-width="1.2"/>'
    # bumper, fog lights, plate
    g += f'<path d="M160,318 L580,318 L582,346 Q580,362 560,362 L178,362 Q160,360 158,344z" fill="#e4e2db" stroke="{INK}" stroke-width="2"/>'
    g += f'<ellipse cx="200" cy="338" rx="12" ry="7" fill="#f4eecf" stroke="{INK}" stroke-width="1.2"/><ellipse cx="540" cy="338" rx="12" ry="7" fill="#f4eecf" stroke="{INK}" stroke-width="1.2"/>'
    if plate:
        g += f'<rect x="322" y="326" width="96" height="24" rx="3" fill="#f7f7f2" stroke="{INK}" stroke-width="1.5"/><rect x="326" y="330" width="14" height="16" fill="#3f6fb0"/>'
        for k in range(6): g += f'<rect x="{346+k*11}" y="333" width="7" height="10" fill="#3b3a48" opacity="0.75"/>'
    # front wheels (perspective)
    g += f'<path d="M170,364 l0,30 q0,10 12,10 l34,0 q10,0 10,-10 l0,-30z" fill="#2c2c33" stroke="{INK}" stroke-width="2"/>'
    g += f'<path d="M514,364 l0,30 q0,10 12,10 l34,0 q10,0 10,-10 l0,-30z" fill="#2c2c33" stroke="{INK}" stroke-width="2"/>'
    if ribbon:
        g += f'<path d="M232,198 Q330,250 372,318" stroke="#d1475a" stroke-width="7" fill="none" stroke-linecap="round"/>'
        g += f'<path d="M478,198 Q410,250 372,318" stroke="#d1475a" stroke-width="7" fill="none" stroke-linecap="round"/>'
        g += f'<path d="M372,318 l-18,26 l12,-2 l6,12 l6,-12 l12,2z" fill="#d1475a" stroke="#8c2433" stroke-width="1"/>'
    if flowers:
        import random
        r = random.Random(3)
        for k in range(18):
            fx = 330 + r.uniform(-55, 55); fy = 236 + r.uniform(-14, 18)
            g += rose(fx, fy, r.uniform(6.5, 9))
        for k in range(8):
            fx = 300 + r.uniform(-80, 80); fy = 232 + r.uniform(-20, 24)
            g += f'<ellipse cx="{fx:.1f}" cy="{fy:.1f}" rx="9" ry="4" fill="#5f8a55" transform="rotate({r.uniform(-40,40):.0f} {fx:.1f} {fy:.1f})"/>'
    return g + '</g>'
