"""Art-directed scene library for the automatic pipeline (approved 2.5D watercolor storybook kit, simple faceless figures).

The planner AI only PICKS a scene name per phrase; composition, scale and framing are fixed here.
build(name, uid, seed, label) -> {"layers", "screen_particles", "move", "cam"?}. Feet stay above the subtitle band.
"""
from kit25 import *
from kit2 import tree, crowd, watercolor_post
from kit3 import child, fruit_tree, kaaba
from scenes import man, woman
from world import Cam, street3d, car_on_road

FEET = 1560
SCENES = {}


def scene(meaning, words=""):
    def deco(fn):
        SCENES[fn.__name__] = (fn, meaning, tuple(words.split()))
        return fn
    return deco


def esc(t): return str(t or "").replace("&", "va").replace("<", "").replace(">", "")


def txt(x, y, t, size=90, col="#2e2a3a"):
    return f'<text x="{x}" y="{y}" font-family="Inter, sans-serif" font-weight="800" font-size="{size}" fill="{col}" text-anchor="middle">{esc(t)}</text>'


def up(body, x, y, k):
    """scale a drawing around its anchor"""
    return f'<g transform="translate({x},{y}) scale({k}) translate({-x},{-y})">{body}</g>'


def W(name, body, bg=None):
    p = R(name, body, bg); watercolor_post(p); return p


def still(x, s=1.7, kind="man", y=FEET, back=False):
    return {"kind": kind, "x0": x, "y0": y, "x1": x, "y1": y, "s0": s, "s1": s, "dur": 1, "back": back}


def walk(x0, x1, s0=1.7, s1=None, y0=FEET, y1=FEET, dur=2.6, kind="man", back=True):
    return {"kind": kind, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "s0": s0, "s1": s1 or s0, "dur": dur, "back": back, "ease": False}


def outdoor(u, body="", actors=(), seed=1, sky="dawnsky", sun=(900, 560), far="mosque", grass=True, fg="vines", parts=None, move="push", gy=1300):
    night = sky == "nightsky"
    a = sky_layers(u + "s", sky, seed=seed, sun=None if night else sun, moon=(900, 420) if night else None, stars=night)
    f = hills(gy - 220) + village(gy - 70, seed, 0.9)
    if far == "mosque": f += dome(900, gy - 40, 0.7)
    for k, x in enumerate((90, 330, 560, 1150)): f += tree(x, gy + 10, 0.62 + 0.1 * (k % 2), seed=seed + k)
    b = W(u + "b", f)
    c = W(u + "c", (meadow(gy) if grass else ground(gy, "#d8cfc2")) + body)
    layers = [*sky_anim(a, 14), L(b, .45), L(c, 1.0, **({"actors": list(actors)} if actors else {}))]
    if fg == "vines": layers.append(L(W(u + "d", fg_vines("left" if seed % 2 else "right", seed=seed)), 1.9))
    elif fg == "bush": layers.append(L(W(u + "d", fg_bush(-60, 330, 1980, 2280, seed)), 1.9))
    if not parts:
        parts = [["stars", 40, [0, 0, 1080, 800]]] if night else [["birds", 3, [0, 120, 1080, 420]], ["leaves", 6, [0, 600, 1080, 1300]]]
    return {"layers": layers, "screen_particles": parts, "move": move}


def room(u, wall="", floor="", actors=(), night=False, lamp=(230, 470), move="push", win=True):
    a = W(u + "a", room_wall(col="#4a4560" if night else "#e9e2d6", floor=1420, sky="nightsky" if night else "dawnsky", win=win) + lantern(lamp[0], lamp[1], 1.4) + wall)
    c = W(u + "c", floor)
    return {"layers": [L(a, .6, flicker=[[lamp[0], lamp[1] + 60, 170]]), L(c, 1.0, **({"actors": list(actors)} if actors else {}))],
            "screen_particles": [["dust", 18, [100, 300, 1000, 1300]]], "move": move}


def insert(u, body, night=False, table="#b98d57", ty=1380, move="push", parts=None):
    """close detail: one big object with soft light"""
    a = W(u + "a", rect(0, 0, SW, SH, "#3d3a55" if night else "#e9e0cc", sw=0) + rays(621, 250, 11, 1700, 80, op=0.28))
    c = W(u + "c", (tabletop(ty, table) if table else "") + body)
    return {"layers": [L(a, .5), L(c, 1.0)], "screen_particles": parts or [["dust", 24, [100, 250, 1000, 1200]]], "move": move,
            "cam": {"zoom": [1.0, 1.1] if move == "push" else [1.1, 1.0], "focus": [0.5, 0.48]}}


def bub(x, y, inner, rx=190, ry=160): return bubble(x, y, rx, ry, (-1, 1)) + inner


def house(x, y, s=1.0):
    w, h = 620 * s, 400 * s
    g = rect(x - w / 2, y - h, w, h, WALL) + poly([(x - w / 2 - 50 * s, y - h), (x + w / 2 + 50 * s, y - h), (x, y - h - 250 * s)], "#b4614f")
    g += door(x - 65 * s, y - 250 * s, 130 * s, 250 * s, DOOR)
    for wx in (x - w / 2 + 70 * s, x + w / 2 - 190 * s): g += rect(wx, y - h + 90 * s, 120 * s, 120 * s, "#ffd98a")
    return g


def tabletop(y, col):
    """table with a plain runner cloth so the lower third is not empty"""
    g = rect(-40, y, SW + 80, 1000, col, sw=2.5) + rect(-40, y + 70, SW + 80, 10, INK, sw=0)
    g += poly([(230, y), (1012, y), (1130, SH + 40), (110, SH + 40)], "#3f6b4c") + poly([(262, y), (980, y), (1088, SH + 40), (152, SH + 40)], "#4f7d5c")
    for k in range(5):
        yy = y + 120 + k * 150; h = 34 + k * 3
        g += poly([(621, yy - h), (621 + h * 1.5, yy), (621, yy + h), (621 - h * 1.5, yy)], "#e2b84f")
    return g


def smartphone(x, y):
    """phone with a speaker on the screen; no hand (owner rule: no fingers)"""
    return (rect(x - 220, y - 420, 440, 860, "#2e2a3a", rx=56, sw=3) + rect(x - 190, y - 360, 380, 740, "#cfe0e6", rx=26, sw=2)
            + man(x, y + 250, 1.55, back=False) + rect(x - 150, y + 300, 300, 18, "#8e8e9e", rx=9, sw=0) + rect(x - 150, y + 300, 130, 18, "#b4483f", rx=9, sw=0))


def dumbbell(x, y, s=1.0):
    return (rect(x - 90 * s, y - 64 * s, 180 * s, 28 * s, "#8a8f99", rx=8) + rect(x - 130 * s, y - 100 * s, 50 * s, 100 * s, "#3b3a48", rx=10)
            + rect(x + 80 * s, y - 100 * s, 50 * s, 100 * s, "#3b3a48", rx=10))


def kid(x, y=FEET, s=1.75): return child(x, y, s)


def plant_young(x, y):
    g = f'<ellipse cx="{x}" cy="{y}" rx="80" ry="18" fill="#8a6a4f"/><path d="M{x},{y} q-8,-120 0,-220" stroke="#6b4a35" stroke-width="10" fill="none"/>'
    for k, (dx, dy, a) in enumerate(((-38, -200, -30), (36, -180, 30), (-32, -130, -40), (34, -110, 35), (0, -240, 0))):
        g += f'<ellipse cx="{x+dx}" cy="{y+dy}" rx="32" ry="15" fill="{("#7fa36a", "#5f8a55")[k % 2]}" stroke="{INK}" stroke-width="1.6" transform="rotate({a} {x+dx} {y+dy})"/>'
    return g


def can_tilt(x, y):
    g = rect(x - 90, y - 150, 180, 150, "#4f8a7a", rx=14, sw=2.5) + f'<path d="M{x+80},{y-40} L{x+190},{y-160}" stroke="#4f8a7a" stroke-width="20" stroke-linecap="round"/><path d="M{x-60},{y-150} q60,-100 120,0" stroke="{INK}" stroke-width="12" fill="none"/>'
    d = "".join(f'<path d="M{x+215+k*14},{y-60+k*k*7} q8,14 0,22 q-8,-8 0,-22z" fill="#9fc6e6" stroke="{INK}" stroke-width="1.2"/>' for k in range(6))
    return f'<g transform="rotate(28 {x} {y})">{g}</g>' + d


# ---------------- family & upbringing ----------------
@scene("father talks to / advises his small son (tarbiya, nasihat)", "tarbiya farzand bola o'g'il nasihat")
def father_son(u, seed, label):
    k = seed % 3
    if k == 1: return outdoor(u, tree(1030, 1480, 1.5, seed=seed) + kid(760) + bub(640, 860, heart(640, 930, 0.9)), [still(430)], seed)
    if k == 2: return outdoor(u, dirt_road(621, 1300, 760) + kid(770, FEET, 1.6), [walk(520, 540, 1.6, 1.25, FEET, 1480, 3.5)], seed, sky="daysky", fg="bush")
    return room(u, bookshelf(960, 1400, 420, 4, seed=seed), dastarxon(560, 1570, 900, 220, items=False) + teapot(560, 1540, 1.1) + kid(760, 1500, 1.8), [still(380, 1.7, y=1500)], win=False)

@scene("a parent repeats advice to a child once, twice: bubbles 1 and 2")
def advice_repeat(u, seed, label): return outdoor(u, kid(800) + bub(520, 830, txt(520, 900, "1", 190, "#3f6b4c"), 150, 130) + bub(830, 600, txt(830, 690, "2", 240, "#b4483f"), 190, 160), [still(400)], seed, fg="")

@scene("child does not listen, words do not get through", "kirmayapti quloq")
def not_listening(u, seed, label): return outdoor(u, kid(900) + ball(1060, FEET, 1.4) + bub(560, 830, cross(560, 830, 100), 170, 140), [still(360)], seed, fg="bush")

@scene("family at the dastarxon: food, rizq, guests, gratitude", "oila dasturxon dastarxon mehmon taom ovqat rizq shukr ne'mat")
def family_meal(u, seed, label): return room(u, "", man(330, 1450, 1.5, back=False) + woman(930, 1450, 1.5) + kid(630, 1400, 1.5) + dastarxon(621, 1530, 1000, 250) + teapot(621, 1480, 1.6))

@scene("family home: house with father, mother, child", "uy uyda uyga ota ona ota-ona xonadon")
def family_home(u, seed, label): return outdoor(u, house(621, 1380, 1.15) + tree(120, 1420, 1.2, seed=seed) + kid(621, FEET, 1.5), [still(420, 1.5), still(830, 1.5, "woman")], seed, far="")

@scene("wedding, marriage, bride and groom", "nikoh to'y uylan kelin kuyov turmush")
def wedding(u, seed, label): return outdoor(u, wedding_arch(621, 1500, 1.3), [still(520, 1.6), still(730, 1.6, "woman")], seed, far="", parts=[["petals", 26, [0, 200, 1080, 1300]]])

@scene("quarrel, anger between people", "urish janjal jahl g'azab asab")
def quarrel(u, seed, label): return room(u, "", man(360, FEET - 20, 1.7, back=False) + woman(890, FEET - 20, 1.7) + anger(621, 760, 1.6) + lightning(621, 900, 1.7))

@scene("kindness, gentleness, love between father and child", "muloyim yumshoq mehr muhabbat sevgi rahm")
def gentle_love(u, seed, label): return outdoor(u, kid(710, FEET, 1.9) + heart(640, 830, 2.1), [still(540, 1.9)], seed, sun=(620, 700), parts=[["petals", 20, [0, 200, 1080, 1300]]])

# ---------------- time, patience, growth ----------------
@scene("patience, slow steady effort: man waters a young sapling", "sabr shoshil asta davomli")
def water_sapling(u, seed, label): return outdoor(u, up(plant_young(850, FEET), 850, FEET, 1.7) + can_tilt(580, 1330), [still(400)], seed, move="right")

@scene("habits / character formed over years: deep roots", "yillar odat tabiat ildiz xarakter")
def deep_roots(u, seed, label):
    a = sky_layers(u + "s", "dawnsky", seed=seed, sun=(960, 480))
    g = rect(-20, 1010, SW + 40, 1300, "#8a6a4f", sw=0) + rect(-20, 990, SW + 40, 50, "#7c9a5e", sw=2)
    for dx, l in ((-430, 520), (-260, 640), (-90, 760), (90, 740), (270, 630), (430, 500)):
        g += f'<path d="M621,1010 C{621+dx*.3},{1010+l*.3} {621+dx*.8},{1010+l*.5} {621+dx},{1010+l}" stroke="#5e4333" stroke-width="{34-abs(dx)/22}" fill="none" stroke-linecap="round"/>'
    return {"layers": [*sky_anim(a, 10), L(W(u + "c", g + tree(621, 1010, 2.0, seed=seed)), 1.0)], "screen_particles": [["leaves", 8, [0, 300, 1080, 900]]], "move": "down"}

@scene("beautiful result, success, baraka, hope: tree in bloom", "chiroyli natija baraka umid go'zal")
def blossom(u, seed, label): return outdoor(u, blossom_tree(800, 1480, 1.25, seed=seed) + kid(1000), [still(400)], seed, parts=[["petals", 28, [0, 200, 1080, 1400]], ["birds", 3, [0, 120, 1080, 400]]])

@scene("time, life passing, waiting", "vaqt umr soat kut muddat")
def time_hourglass(u, seed, label): return insert(u, up(hourglass(621, 1390, 1.0), 621, 1390, 3.0))

@scene("a named weekday / month / age (needs label)", "dushanba seshanba chorshanba payshanba juma shanba yakshanba ramazon yosh")
def calendar_day(u, seed, label): return insert(u, up(calendar(400, 700, 1.0, label or "KUN", 3), 621, 900, 1.7))

@scene("tired, lazy, asleep or ill in bed", "charcha uyqu uxla dangasa kasal bemor")
def tired_bed(u, seed, label): return room(u, "", up(bed(640, 1530, 1.2, person=True), 640, 1530, 1.35), night=True)

@scene("gives up, drops everything and leaves", "tashla to'xta voz")
def give_up(u, seed, label): return room(u, door(930, 960, 240, 460, DOOR), f'<g transform="rotate(-18 330 1540)">{up(book_stack(330, 1540, 1.0), 330, 1540, 1.3)}</g>' + dumbbell(640, 1560, 1.4), [walk(820, 1040, 1.6, 1.4, FEET - 40, 1440)], win=False, move="pull")

# ---------------- worship ----------------
@scene("man prays before the mihrab: namoz, sajda, worship", "namoz sajda ibodat tahajjud bomdod peshin xufton")
def prayer(u, seed, label): return room(u, mihrab(621, 1420, 1.5), prayer_mat(621, 1600, 1.6), [still(621, 1.75, "man_dua", back=True)], night=True, win=False, lamp=(190, 470))

@scene("man walks to the mosque", "masjid jamoat azon")
def to_mosque(u, seed, label): return outdoor(u, dirt_road(700, 1300, 900) + dome(640, 1310, 1.25), [walk(560, 660, 1.7, 0.95, FEET, 1400, 3.2)], seed, far="", grass=False, fg="bush")

@scene("hands raised in dua, repentance", "duo tavba istig'for allohim so'ra")
def dua(u, seed, label): return outdoor(u, rays(621, 120, 11, 1500, 80, op=0.35), [still(621, 2.1, "man_dua", back=True)], seed, sky="nightsky", grass=False)

@scene("the Qur'an on a rehal", "qur'on oyat sura tilovat")
def quran(u, seed, label): return insert(u, up(quran_rehal(621, 1390, 1.0), 621, 1390, 2.9), night=True, table="#6b4a35")

@scene("the Prophet's words, hadith, sunnat: green dome (never drawn as a person)", "payg'ambar rasululloh hadis sunnat madina sollallohu")
def green_dome_night(u, seed, label): return outdoor(u, green_dome(621, 1440, 1.75), [], seed, sky="nightsky", far="", grass=False, fg="")

@scene("Makka, Ka'ba, haj, umra", "ka'ba makka haj umra tavof")
def kaaba_scene(u, seed, label): return outdoor(u, kaaba(621, 1400, 1.9) + crowd(60, 1440, 1180, 1560, 16, 0.45, 0.6, seed=seed, mix=0.3), [], seed, far="", grass=False, fg="")

@scene("Allah's mercy, guidance, paradise, light", "alloh rabb jannat rahmat hidoyat nur iymon")
def mercy_light(u, seed, label): return outdoor(u, rays(621, 200, 11, 1500, 90, op=0.4) + fruit_tree(930, 1500, 1.2, seed=seed, ripe=1.0), [still(430, 1.7, back=True)], seed, sun=(621, 420), far="", parts=[["petals", 16, [0, 200, 1080, 1300]], ["birds", 4, [0, 120, 1080, 420]]])

@scene("sin, haram, shaytan, danger: thorny dark road", "gunoh harom shayton xato do'zax yomon")
def sin_thorns(u, seed, label): return outdoor(u, dirt_road(700, 1300, 800) + up(thorn_bush(260, 1520, 1.0, seed=seed), 260, 1520, 1.6) + up(thorn_bush(1030, 1500, 1.0, seed=seed + 2), 1030, 1500, 1.4) + up(warning(860, 1080, 1.0), 860, 1080, 2.2), [still(600, 1.6, back=True)], seed, sky="nightsky", far="", grass=False, fg="")

@scene("death, grave, the hereafter", "o'lim qabr oxirat vafot o'ldi")
def grave(u, seed, label):
    g = "".join(f'<path d="M{x-70*s},{y} l0,{-150*s} a{70*s},{70*s} 0 0 1 {140*s},0 l0,{150*s}z" fill="#cfc6b8" stroke="{INK}" stroke-width="3"/><ellipse cx="{x}" cy="{y+14*s}" rx="{130*s}" ry="{26*s}" fill="#8a7a62" stroke="{INK}" stroke-width="2"/>' for x, y, s in ((260, 1380, .9), (950, 1370, .9), (400, 1500, 1.25), (900, 1520, 1.25)))
    return outdoor(u, tree(1120, 1380, 1.3, seed=seed) + g, [still(640, 1.5, back=True)], seed, sky="nightsky", far="", fg="")

# ---------------- knowledge, work, self ----------------
@scene("reading, books, knowledge, study", "kitob ilm o'qiy dars talaba ustoz maktab")
def reading(u, seed, label): return room(u, bookshelf(300, 1400, 480, 4, seed=seed), up(open_book(900, 1540, 1.0), 900, 1540, 1.1) + up(book_stack(330, 1560, 1.0), 330, 1560, 1.2), [still(640, 1.75)], win=False, lamp=(980, 470))

@scene("father or teacher teaches a child from a book", "o'rgat ta'lim")
def teach_child(u, seed, label): return room(u, "", dastarxon(621, 1560, 1000, 240, items=False) + up(open_book(600, 1570, 1.0), 600, 1570, 0.7) + kid(860, 1500, 1.9), [still(380, 1.7, y=1500)])

@scene("lecture or video on a phone, internet", "telefon internet ma'ruza video instagram")
def phone_lecture(u, seed, label): return insert(u, smartphone(621, 900) + sparkle(250, 620, 1.6) + sparkle(990, 560, 1.4), table=None)

@scene("sport, running, exercise", "sport yugur mashq")
def sport(u, seed, label): return outdoor(u, dumbbell(1000, FEET + 20, 0.9), [walk(80, 720, 1.75, dur=1.6, back="side")], seed, sky="daysky", far="", move="right")

@scene("healthy food, diet, water", "parhez dieta suv ichimlik")
def diet(u, seed, label): return insert(u, up(bowl(470, 1400, 1.0, food="#7fa36a"), 470, 1400, 3.2) + up(cup_water(880, 1400, 1.0), 880, 1400, 3.4))

@scene("looking at oneself, self-discipline, nafs: mirror", "o'zimiz o'zini nafs o'zing")
def mirror_self(u, seed, label):
    m = rect(600, 640, 480, 860, "#b98d57", rx=240, sw=3) + rect(640, 680, 400, 790, "#cfe0e6", rx=200, sw=2.5) + f'<g opacity="0.6">{man(840, 1430, 1.75, back=False)}</g>'
    return room(u, "", m, [still(380, 1.8, back=True)], win=False)

@scene("a question: what, why, how", "nima nega qanday qachon kim")
def question(u, seed, label): return outdoor(u, bub(760, 800, txt(760, 900, "?", 290, "#3f6b4c"), 220, 190), [still(520, 1.9)], seed, fg="bush")

@scene("money, wealth, worldly life, debt", "pul boylik dunyo savdo biznes qarz")
def money(u, seed, label): return insert(u, up(coins(380, 1390, 1.0), 380, 1390, 2.1) + up(coins(760, 1390, 1.0), 760, 1390, 2.1))

@scene("shop, work, trade", "do'kon ish kasb tijorat")
def shop(u, seed, label): return outdoor(u, up(shop_front(341, 1390, 560, esc(label)[:10] or "DO'KON"), 621, 1390, 1.3), [still(1060, 1.5)], seed, far="", grass=False)

@scene("car on a street, travel", "mashina safar avtomobil")
def car_street(u, seed, label):
    cam = Cam(f=1250, h=1.7, vx=SW * 0.55, vy=1000)
    body = street3d(cam, seed=3) + car_on_road(cam, -1.4, 7.5, body="#f1efe8", flowers=False, ribbon=False, uid=u)
    return {"layers": [*sky_anim(sky_layers(u + "s", "dawnsky", seed=seed, sun=(850, 700)), 14), L(W(u + "c", body), 1.0)], "screen_particles": [["birds", 3, [0, 120, 1080, 400]]], "move": "push"}

@scene("choice, decision, road of life: fork in the road", "tanla yo'l hayot qaror")
def two_paths(u, seed, label): return outdoor(u, fork_road(1300) + up(signpost(760, 1400, 1.0), 760, 1400, 1.8), [still(560, 1.4, back=True)], seed, far="", fg="bush")

@scene("balance, justice, weighing deeds", "tarozi amal savob adolat mas'uliyat")
def scale_deeds(u, seed, label): return insert(u, up(scale(621, 1390, 1.0, tilt=1), 621, 1390, 1.55))

@scene("gift, charity, help", "hadya sovg'a sadaqa yordam ehson")
def gift(u, seed, label): return outdoor(u, up(gift_box(640, FEET, 1.0), 640, FEET, 2.0), [still(340), still(930, 1.7, "woman")], seed)

@scene("many people, society", "odamlar xalq yigitlar insonlar jamiyat")
def people(u, seed, label): return outdoor(u, crowd(80, 1400, 1160, 1570, 13, 0.95, 1.25, seed=seed, mix=0.0, coat="#556078"), [], seed, grass=False)

@scene("heart, intention, feelings", "qalb yurak niyat ta'sir")
def heart_scene(u, seed, label): return insert(u, up(heart(621, 1050, 1.0), 621, 1050, 4.2) + sparkle(270, 720, 1.6) + sparkle(980, 660, 1.4), table=None, parts=[["petals", 20, [0, 200, 1080, 1300]]])


def die(x, y, s, pips):
    g = rect(x - 90 * s, y - 180 * s, 180 * s, 180 * s, "#f6f1e6", rx=26 * s, sw=3)
    P = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}[pips]
    return g + "".join(f'<circle cx="{x+a*48*s}" cy="{y-90*s+b*48*s}" r="{17*s}" fill="#b4483f"/>' for a, b in P)


@scene("gambling, betting, qimor, stavka: dice and coins crossed out", "qimor stavka bukmeker garov tik")
def gambling(u, seed, label): return insert(u, die(430, 1390, 1.7, 5) + die(800, 1390, 1.7, 3) + coins(930, 1395, 1.0) + cross(621, 830, 170, 34))

@scene("football, match, club, sport betting on football", "futbol klub o'yin gol")
def football(u, seed, label):
    net = rect(330, 900, 580, 400, "none", sw=9) + "".join(f'<path d="M{330+k*58},900 L{330+k*58},1300 M330,{900+k*40} L910,{900+k*40}" stroke="#f6f1e6" stroke-width="2.5" opacity="0.8"/>' for k in range(11))
    b = f'<circle cx="800" cy="1500" r="62" fill="#f6f1e6" stroke="{INK}" stroke-width="3"/>' + poly([(800, 1474), (825, 1492), (815, 1522), (785, 1522), (775, 1492)], "#2e2a3a")
    return outdoor(u, net + b, [still(480, 1.6, back=True)], seed, sky="daysky", far="", fg="bush")

@scene("trap, bait, addiction, being hooked by the first easy win (ilashdi, birinchi yutuq)", "ilash tuzoq aldan yutuq yutib yutsang")
def hook_trap(u, seed, label):
    h = f'<path d="M700,-20 L700,760 q0,230 -150,230 q-140,0 -140,-150 l0,-40" stroke="#5a5f6b" stroke-width="30" fill="none" stroke-linecap="round"/>' + poly([(410, 760), (350, 850), (470, 850)], "#5a5f6b")
    c = f'<circle cx="560" cy="890" r="135" fill="#e2b84f" stroke="{INK}" stroke-width="5"/><circle cx="560" cy="890" r="102" fill="none" stroke="#b98d2f" stroke-width="8"/>' + txt(560, 930, "PUL", 88, "#8a6420")
    return insert(u, h + c, table=None)

@scene("honest work, effort, labour in the field (mehnat)", "mehnat halol dehqon")
def honest_work(u, seed, label): return outdoor(u, wheat(60, 1180, 1280, 1480, seed) + up(hoe(760, FEET, 1.0), 760, FEET, 1.6), [still(560, 1.75)], seed, far="", fg="")

@scene("an enemy, danger for a young man (dushman)", "dushman xavf")
def enemy(u, seed, label): return outdoor(u, up(warning(850, 1060, 1.0), 850, 1060, 2.6) + lightning(300, 700, 2.0), [still(540, 1.8)], seed, sky="nightsky", far="", grass=False, fg="")

@scene("leaving with money, taking the win (pulni olib ketish)", "pulni")
def take_money(u, seed, label): return outdoor(u, dirt_road(760, 1300, 800) + coins(900, 1500, 1.5), [walk(420, 690, 1.7, 1.0, FEET, 1390, 3.4)], seed, far="", grass=False, fg="bush")


def build(name, uid, seed=1, label=""):
    return SCENES[name][0](uid, seed, str(label or "").upper()[:12])


def catalog():
    return "\n".join(f"- {k}: {v[1]}" for k, v in SCENES.items())


def by_words(text):
    """scenes whose keyword starts a word of the phrase, in spoken order (literal-meaning guard)"""
    hits = []
    for w in str(text).lower().replace("’", "'").split():
        w = w.strip(".,?!:;«»\"()-")
        for k, (_, _, keys) in SCENES.items():
            if k not in hits and any(w == x or (len(x) >= 4 and w.startswith(x)) for x in keys):
                hits.append(k)
    return hits
