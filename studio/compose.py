"""Scene composer for the automatic pipeline.

A shot is described in small JSON (written by the planner AI) and turned into the layered shot dict that
animate.py renders, using the approved 2.5D storybook kit (kit25 / kit2 / world / car3d).

shot = {"start": 3.84, "setting": "outdoor_day", "camera": "push",
        "props": [{"name": "wedding_arch", "slot": "center", "depth": "mid", "label": ""}],
        "actors": [{"kind": "man", "action": "walk_in", "slot": "left"}],
        "text": "", "particles": "petals", "car": false}
"""
from kit25 import *
from kit2 import crowd, watercolor_post
from world import Cam, street3d, car_on_road

SAND = "#d8cfc2"
SLOT_X = {"left": 300, "center": 621, "right": 940, "left2": 180, "right2": 1060}
DEPTH = {"far": (1430, 0.6), "mid": (1650, 0.85), "near": (1900, 1.1)}
SETTINGS = ["outdoor_day", "outdoor_sunset", "outdoor_night", "room_day", "room_night", "street", "card", "village", "meadow", "mosque_night"]
CAMERAS = ["push", "pull", "left", "right"]
PARTICLES = ["", "birds", "petals", "dust", "stars", "leaves", "rain"]


def txt(x, y, t, size=90, col="#2e2a3a"):
    t = (t or "").replace("&", "va").replace("<", "").replace(">", "")
    return f'<text x="{x}" y="{y}" font-family="Inter, sans-serif" font-weight="800" font-size="{size}" fill="{col}" text-anchor="middle">{t}</text>'


def label_plate(x, y, t, s=1.0):
    if not t:
        return ""
    w = max(220, 34 * len(t)) * s
    return rect(x - w / 2, y - 70 * s, w, 90 * s, "#3f6b4c", rx=14) + txt(x, y - 8 * s, t, 50 * s, "#f6e7b8")


def lights(x0, x1, y, sag=60, n=14):
    g = f'<path d="M{x0},{y} Q{(x0+x1)/2},{y+sag*2} {x1},{y}" fill="none" stroke="{INK}" stroke-width="2"/>'
    for k in range(1, n):
        t = k / n; x = x0 + (x1 - x0) * t; yy = y + 4 * sag * t * (1 - t)
        g += f'<circle cx="{x}" cy="{yy+10}" r="11" fill="{("#ffd98a", "#f2a1b8", "#bfe3c0")[k % 3]}" stroke="{INK}" stroke-width="1.5"/>'
    return g


def house(x, y, s=1.0, label=""):
    w, h = 620 * s, 420 * s
    g = rect(x - w / 2, y - h, w, h, WALL)
    g += poly([(x - w / 2 - 60 * s, y - h), (x + w / 2 + 60 * s, y - h), (x, y - h - 300 * s)], "#b4483f")
    g += door(x - 70 * s, y - 280 * s, 140 * s, 280 * s, DOOR)
    for wx in (x - w / 2 + 70 * s, x + w / 2 - 190 * s):
        g += rect(wx, y - h + 90 * s, 120 * s, 120 * s, "#ffd98a")
    if label:
        parts = [p.strip() for p in label.split(",") if p.strip()][:3]
        if len(parts) > 1:  # foundation stones
            sw = (w + 40 * s) / len(parts)
            for i, lab in enumerate(parts):
                bx = x - w / 2 - 20 * s + i * sw
                g += rect(bx, y, sw - 8, 130 * s, "#cfc6b8", rx=8) + txt(bx + sw / 2 - 4, y + 90 * s, lab, 56 * s)
        else:
            g += label_plate(x, y - h - 330 * s, label, s)
    return g


def wedding_house(x, y, s=1.0, label=""):
    w = 620 * s
    return house(x, y, s, label) + lights(x - w / 2 - 40 * s, x + w / 2 + 40 * s, y - 430 * s, 50 * s)


def badge(x, y, s=1.0, label="1"):
    r = 240 * s
    return f'<circle cx="{x}" cy="{y - r}" r="{r}" fill="#3f6b4c" stroke="{INK}" stroke-width="4"/>' + txt(x, y - r + r * 0.4, label or "1", r * 1.1, "#f6e7b8")


def crossed_badge(x, y, s=1.0, label="1"):
    r = 240 * s
    return badge(x, y, s, label) + cross(x, y - r, r * 0.85, 24 * s)


def weight_scale(x, y, s=1.0, label=""):
    g = scale(x, y, 1.6 * s, tilt=1 if label else 0)
    if label:
        g += label_plate(x + 300 * s, y - 380 * s, label, s * 0.9)
    return g


def question(x, y, s=1.0, label="?"):
    return txt(x, y - 40 * s, label or "?", 420 * s, "#3f6b4c")


def thought(x, y, s=1.0, label=""):
    g = bubble(x, y - 700 * s, 300 * s, 240 * s, (-1, 1))
    return g + txt(x, y - 680 * s, label or "...", 70 * s)


def big_calendar(x, y, s=1.0, label=""):
    return calendar(x - 330 * s, y - 900 * s, 1.7 * s, label or "KUN", 6)


def lamp(x, y, s=1.0, label=""):
    return lantern(x, y - 1000 * s, 3.5 * s) + (txt(x, y, label, 100 * s) if label else "")


def books(x, y, s=1.0, label=""):
    return book_stack(x, y, 2.2 * s) + (label_plate(x, y + 120 * s, label, s) if label else "")


def shop(x, y, s=1.0, label=""):
    return shop_front(x, y, 640 * s, label or "DO'KON")


def work(x, y, s=1.0, label=""):
    return workshop(x, y, 640 * s, label or "USTAXONA", s=s)


def school(x, y, s=1.0, label=""):
    return institute(x, y, s, label or "INSTITUT")


def plant(x, y, s=1.0, label=""):
    return f'<g transform="translate({x},{y}) scale({1.8*s})"><path d="M0,0 C-10,-120 10,-200 0,-300" stroke="#4e7d4f" stroke-width="10" fill="none"/>' \
           f'<ellipse cx="-50" cy="-200" rx="60" ry="26" fill="#7fb07a" stroke="{INK}" stroke-width="2" transform="rotate(-25 -50 -200)"/>' \
           f'<ellipse cx="50" cy="-250" rx="60" ry="26" fill="#7fb07a" stroke="{INK}" stroke-width="2" transform="rotate(25 50 -250)"/>' \
           f'<rect x="-70" y="-10" width="140" height="80" rx="10" fill="#b98d57" stroke="{INK}" stroke-width="2"/></g>'


def money(x, y, s=1.0, label=""):
    return coins(x - 160 * s, y, 2.4 * s) + coins(x + 170 * s, y, 2.0 * s) + (label_plate(x, y - 260 * s, label, s) if label else "")


def text_card(x, y, s=1.0, label=""):
    return txt(x, y - 300, label, 220 * s)


# name -> (draw(x, ground_y, s, label), base scale, description for the planner)
PROPS = {
    "house": (house, 0.9, "family home; label 'A,B,C' puts up to 3 foundation stones under it"),
    "wedding_house": (wedding_house, 0.9, "home with festive string lights = marriage/family"),
    "wedding_arch": (lambda x, y, s, l: wedding_arch(x, y, 1.1 * s), 1.0, "wedding arch with flowers"),
    "mosque": (lambda x, y, s, l: dome(x, y, 1.0 * s), 1.0, "mosque with dome and minaret"),
    "green_dome": (lambda x, y, s, l: green_dome(x, y, 1.0 * s), 1.0, "green dome of Madina (prophet is NEVER drawn)"),
    "kaaba_shrine": (lambda x, y, s, l: golden_dome_shrine(x, y, s), 1.0, "golden-dome shrine"),
    "mihrab": (lambda x, y, s, l: mihrab(x, y, 1.2 * s), 1.0, "mihrab niche indoors"),
    "prayer_mat": (lambda x, y, s, l: prayer_mat(x, y - 80, 2.0 * s), 1.0, "prayer mat"),
    "quran": (lambda x, y, s, l: quran_rehal(x, y, 2.2 * s), 1.0, "open Quran/book on a stand (hadith, revelation)"),
    "book_open": (lambda x, y, s, l: open_book(x, y, 2.4 * s), 1.0, "open book"),
    "books": (books, 1.0, "stack of books; label optional (ILM, AQL)"),
    "bookshelf": (lambda x, y, s, l: bookshelf(x, y, 900 * s, 4), 1.0, "bookshelf (knowledge)"),
    "school": (school, 1.0, "institute/university building; label = name"),
    "grad_cap": (lambda x, y, s, l: grad_cap(x, y - 500 * s, 6 * s), 1.0, "graduation cap"),
    "exam": (lambda x, y, s, l: exam_sheet(x, y - 200 * s, 1.3 * s), 1.0, "exam sheet"),
    "shop": (shop, 1.0, "shop front; label = sign text (BIZNES, DO'KON)"),
    "workshop": (work, 1.0, "workshop/craft; label = sign"),
    "factory": (lambda x, y, s, l: factory(x, y, s, l or "ZAVOD"), 1.0, "factory/work"),
    "money": (money, 1.0, "gold coins = money/wealth; label optional"),
    "debt": (lambda x, y, s, l: debt_papers(x, y, 1.3 * s, l or "QARZ"), 1.0, "debt papers"),
    "gift": (lambda x, y, s, l: gift_box(x, y, 2.6 * s), 1.0, "gift box (hadya)"),
    "heart": (lambda x, y, s, l: heart(x, y - 350 * s, 3.5 * s), 1.0, "heart (love, iymon, qalb)"),
    "scale": (weight_scale, 1.0, "balance scale; label = heavy weight name (MAS'ULIYAT, AMAL)"),
    "question": (question, 1.0, "big question mark"),
    "thought": (thought, 1.0, "thought bubble with short text label"),
    "calendar": (big_calendar, 1.0, "wall calendar with crossed days; label = title (30 YOSH, RAMAZON)"),
    "hourglass": (lambda x, y, s, l: hourglass(x, y, 1.5 * s), 1.0, "hourglass = time passing"),
    "clock": (lambda x, y, s, l: clock_face(x, y - 300 * s, 230 * s), 1.0, "clock face = time"),
    "lamp": (lamp, 1.0, "hanging lamp = light/mind; label optional (AQL)"),
    "dastarxon": (lambda x, y, s, l: dastarxon(x, y + 40, 760 * s, 240 * s) + teapot(x, y + 10, 1.1 * s), 1.0, "low table with tea, bread = family meal, guests"),
    "teapot": (lambda x, y, s, l: teapot(x, y, 3.0 * s), 1.0, "teapot"),
    "bread": (lambda x, y, s, l: bread(x, y, 3.0 * s), 1.0, "bread (rizq)"),
    "water": (lambda x, y, s, l: cup_water(x, y, 3.2 * s), 1.0, "cup of water"),
    "jug": (lambda x, y, s, l: jug(x, y, 2.6 * s), 1.0, "clay jug"),
    "broken_jug": (lambda x, y, s, l: broken_jug(x, y, 2.6 * s), 1.0, "broken jug (loss, mistake)"),
    "phone": (lambda x, y, s, l: phone(x, y - 300 * s, 1.8 * s), 1.0, "smartphone (social media, distraction)"),
    "bed": (lambda x, y, s, l: bed(x, y, 1.2 * s, person=True), 1.0, "bed with sleeping person (sleep, illness)"),
    "chair": (lambda x, y, s, l: chair(x, y, 2.2 * s), 1.0, "chair"),
    "shelves": (lambda x, y, s, l: shelves(x - 300 * s, y - 800 * s, 600 * s, 700 * s, 3), 1.0, "shelves with jars (home, goods)"),
    "tree": (lambda x, y, s, l: blossom_tree(x, y, 1.1 * s), 1.0, "blossoming tree (growth, hope)"),
    "plant": (plant, 1.0, "small sprout in a pot (small daily deeds, beginning)"),
    "wheat": (lambda x, y, s, l: wheat(x - 300 * s, x + 300 * s, y - 250 * s, y), 1.0, "wheat field patch (harvest, rizq)"),
    "thorns": (lambda x, y, s, l: thorn_bush(x, y, 1.2 * s), 1.0, "thorn bush (sin, hardship)"),
    "logs": (lambda x, y, s, l: logs(x, y, 2.2 * s), 1.0, "logs (hard work, strength)"),
    "tent": (lambda x, y, s, l: tent(x, y, 1.8 * s), 1.0, "tent (journey, travel, hijra)"),
    "boat": (lambda x, y, s, l: boat(x, y, 2.2 * s), 1.0, "boat"),
    "sheep": (lambda x, y, s, l: sheep(x, y, 2.6 * s), 1.0, "sheep (qurbon, shepherd)"),
    "cow": (lambda x, y, s, l: cow(x, y, 2.2 * s), 1.0, "cow"),
    "cart": (lambda x, y, s, l: cart(x, y, 2.0 * s), 1.0, "hand cart (burden, trade)"),
    "signpost": (lambda x, y, s, l: signpost(x, y, 2.4 * s), 1.0, "signpost (choice, direction)"),
    "milestone": (lambda x, y, s, l: milestone(x, y, 2.2 * s, l or "0"), 1.0, "milestone stone; label = number"),
    "trophy": (lambda x, y, s, l: trophy(x, y, 1.3 * s), 1.0, "trophy (success)"),
    "warning": (lambda x, y, s, l: warning(x, y - 300 * s, 3.0 * s), 1.0, "warning sign (danger, haram)"),
    "lightning": (lambda x, y, s, l: lightning(x, y - 700 * s, 3.5 * s), 1.0, "lightning (anger, sudden)"),
    "anger": (lambda x, y, s, l: anger(x, y - 450 * s, 3.5 * s), 1.0, "anger steam symbol"),
    "badge": (badge, 1.0, "numbered circle; label = number (1, 2, 3)"),
    "crossed_badge": (crossed_badge, 1.0, "numbered circle crossed out (a mistake)"),
    "text": (text_card, 1.0, "big short word/phrase on screen (max 3 words, Uzbek)"),
    "crowd": (lambda x, y, s, l: crowd(x - 480, y - 150, x + 480, y + 250, 14, 0.6 * s, 0.9 * s, seed=5, mix=0.5), 1.0, "crowd of people (men and women)"),
    "men_group": (lambda x, y, s, l: crowd(x - 480, y - 150, x + 480, y + 250, 12, 0.7 * s, 1.0 * s, seed=8, mix=0.0, coat="#556078"), 1.0, "group of men (yigitlar, jamoat)"),
    "rays": (lambda x, y, s, l: rays(x, y - 900, 9, 1400, 50, op=0.25), 1.0, "divine light rays from above (rahmat, hidoyat)"),
    "sparkle": (lambda x, y, s, l: sparkle(x, y - 400 * s, 3.5 * s), 1.0, "sparkle (new, shining)"),
}


def _sky(name, kind, sun=None, moon=None, stars=False):
    return sky_anim(sky_layers(name, kind, seed=abs(hash(name)) % 50, sun=sun, moon=moon, stars=stars), 10)


def _bg(name, setting):
    """return (list of background layers, ground y, base svg prefix for the main layer)"""
    if setting in ("outdoor_day", "outdoor_sunset"):
        return _sky(name + "s", "dawnsky", sun=(860, 800)) + [L(W(name + "h", hills(1180)), .45)], ground(1350, SAND)
    if setting in ("outdoor_night", "mosque_night"):
        return _sky(name + "s", "nightsky", moon=(860, 380), stars=True), ground(1450, "#5d5a6e")
    if setting == "village":
        return _sky(name + "s", "dawnsky", sun=(300, 760)) + [L(W(name + "h", hills(1100) + village(1300, seed=4)), .45)], ground(1450, SAND)
    if setting == "meadow":
        return _sky(name + "s", "dawnsky", sun=(860, 760)) + [L(W(name + "h", hills(1150)), .45)], meadow(1350)
    if setting == "room_day":
        return [], room_wall(col="#e9e2d6", floor=1600, sky="dawnsky")
    if setting == "room_night":
        return [], room_wall(col="#3e3a4c", floor=1650, sky="nightsky")
    if setting == "card":
        return [], rect(0, 0, SW, SH, "#efe6d4", sw=0)
    return [], ""


def W(name, body):
    p = R(name, body)
    watercolor_post(p)
    return p


def build_shot(sh, name):
    setting = sh.get("setting") if sh.get("setting") in SETTINGS else "outdoor_day"
    if sh.get("car"):
        setting = "street"
    layers, base = _bg(name, setting)
    body, flick, actors = base, [], []
    if setting == "street":
        layers = _sky(name + "s", "dawnsky", sun=(850, 760))
        cam = Cam(f=1250, h=1.7, vx=SW * 0.55, vy=1080)
        body = street3d(cam, seed=3) + (car_on_road(cam, -1.9, 9.0, body="#f1efe8", flowers=False, ribbon=False, uid=name) if sh.get("car") else "")
    props = sorted(sh.get("props", [])[:4], key=lambda p: DEPTH.get(p.get("depth"), DEPTH["mid"])[0])
    for p in props:
        if p.get("name") not in PROPS:
            continue
        fn, base_s, _ = PROPS[p["name"]]
        y, ds = DEPTH.get(p.get("depth"), DEPTH["mid"])
        if setting.startswith("room"):
            y = max(y, 1650)
        x = SLOT_X.get(p.get("slot"), 621)
        try:
            body += fn(x, y, base_s * ds * float(p.get("size", 1.0)), str(p.get("label", ""))[:24])
        except Exception as e:  # never crash the pipeline on one prop
            print("prop failed", p, e)
        if p["name"] in ("lamp", "house", "wedding_house", "mosque", "green_dome"):
            flick.append([x, int(y - 300 * ds), 140])
    if setting == "mosque_night" and not props:
        body += green_dome(621, 1500, 1.1) + lantern(200, 1250, 1.0) + lantern(1040, 1250, 1.0)
    if sh.get("text"):
        body += txt(621, 520, sh["text"][:28], 96)
    for a in sh.get("actors", [])[:2]:
        kind = a.get("kind") if a.get("kind") in ("man", "woman") else "man"
        x = SLOT_X.get(a.get("slot"), 621)
        y0 = 1880 if not setting.startswith("room") else 1880
        act = a.get("action", "stand")
        if act == "walk_in":
            actors.append({"kind": kind, "x0": x - 250, "y0": 2150, "x1": x, "y1": 1700, "s0": 1.5, "s1": 1.05, "dur": 2.0, "back": True, "ease": False})
        elif act == "walk_away":
            actors.append({"kind": kind, "x0": x, "y0": 2050, "x1": x, "y1": 1550, "s0": 1.4, "s1": 0.9, "dur": 3.0, "back": True, "ease": False})
        else:
            actors.append({"kind": kind, "x0": x, "y0": y0, "x1": x, "y1": y0, "s0": 1.25, "s1": 1.25, "dur": 1, "back": bool(a.get("back"))})
    main = L(W(name + "c", body), 1.0, **({"flicker": flick} if flick else {}), **({"actors": actors} if actors else {}))
    layers = layers + [main]
    part = sh.get("particles") if sh.get("particles") in PARTICLES else ""
    sp = []
    if part == "birds": sp = [["birds", 3, [0, 120, 1080, 420]]]
    elif part == "stars": sp = [["stars", 30, [0, 0, 1080, 900]]]
    elif part: sp = [[part, 25, [0, 200, 1080, 1700]]]
    move = sh.get("camera") if sh.get("camera") in CAMERAS else "push"
    d = {"start": float(sh["start"]), "move": move, "layers": layers, "screen_particles": sp}
    if move in ("push", "pull") and setting in ("card", "room_day", "room_night"):
        d["cam"] = {"zoom": [1.0, 1.1] if move == "push" else [1.1, 1.0], "focus": [0.5, 0.5]}
    return d


def catalog_text():
    lines = ["SETTINGS: " + ", ".join(SETTINGS), "CAMERAS: " + ", ".join(CAMERAS), "PARTICLES: " + ", ".join(p for p in PARTICLES if p),
             "SLOTS: left2, left, center, right, right2; DEPTH: far, mid, near", "PROPS (name — meaning):"]
    lines += [f"- {k} — {v[2]}" for k, v in PROPS.items()]
    return "\n".join(lines)
