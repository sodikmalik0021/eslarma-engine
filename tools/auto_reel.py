"""Fully automatic reel maker for eslarma.uz (runs on GitHub Actions, no Claude needed).

  python3 tools/auto_reel.py plan   <src_name>   -> data/plans/<id>.json   (Gemini: shots, subtitles, caption)
  python3 tools/auto_reel.py render <src_name>   -> out/eslarma_<id>.mp4   (studio/compose.py + animate.py)
  python3 tools/auto_reel.py check  <src_name>   -> exit 1 if the video fails automatic checks

Env: GEMINI_API_KEY (free key from aistudio.google.com), optional GEMINI_MODEL.
"""
import re
import json, os, subprocess, sys, time, urllib.error, urllib.request, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studio"))
MODELS = [m for m in [os.environ.get("GEMINI_MODEL"), "gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"] if m]

RULES = """You are the director of the Instagram account eslarma.uz: short Uzbek Islamic reels made from the audio of a
speaker (Abdulloh domla). The original audio is kept; you design the ANIMATION that plays over it, plus subtitles and caption.

ABSOLUTE RULES
1. THE PICTURE MUST MATCH THE SPEAKER'S WORDS AT EVERY MOMENT. Each shot shows literally what is being said right then,
   recognizable at a glance (he says "mashina" -> a car; "do'kon/biznes" -> shop; "Payg'ambarimiz" -> green_dome; hadith -> quran).
2. One central metaphor for the whole reel (e.g. a house = marriage; a path = life), returning in the first and last shots.
3. Cut on key words: a new shot starts at the timestamp of the key word (use the word timestamps given). Shots 1.2–5 s long.
   Typically 12–25 shots per minute. First shot starts at 0.0.
4. Never draw the Prophet, companions or any face; people are small simple figures (actors: man / woman only).
5. Use ONLY the settings, props, slots, depths, cameras and particles from the CATALOG. Max 4 props and 2 actors per shot.
   Don't stack two props in the same slot+depth. Labels are short UPPERCASE Uzbek words (max 12 chars) or empty.
6. "text" (on-screen words) only for numbers or a key word, max 3 words. Usually empty.
7. Subtitles: rewrite every transcript segment into correct Uzbek LATIN (o', g', sh, ch, ng; Arabic phrases transliterated
   in Latin), same meaning and word order as spoken, no additions. Keep segment indexes.
8. hook: max 7 words, a question or surprising claim that makes people stay (Uzbek). cta: "Obuna bo'ling — har kuni eslatma".
9. caption: hook line + 2 short summary lines + a question to the audience + "\\n\\n🎙 @abdulloh.domla\\n\\n📌 Buni ... do'stingizga yuboring."
   (concrete person to send it to) + 5–8 hashtags incl #islom #eslatma #abdullohdomla #eslarma. comment: warm Uzbek dua/question, <=200 chars.

Return ONLY JSON:
{"hook": str, "cta": str, "caption": str, "comment": str, "metaphor": str,
 "subtitles": {"<segment index>": "corrected Uzbek Latin text", ...},
 "shots": [{"start": float, "says": "words spoken in this shot", "setting": str, "camera": str,
            "props": [{"name": str, "slot": str, "depth": str, "label": str, "size": float}],
            "actors": [{"kind": "man|woman", "action": "stand|walk_in|walk_away", "slot": str, "back": bool}],
            "text": str, "particles": str, "car": bool}]}"""


def local_llm(prompt, num_predict=2500, temperature=0.3):
    """Open model running on the GitHub runner itself (ollama). Free, no limits, no external queue.
    Small calls only: a 4B model on CPU truncates/loops on one huge JSON (run 45244437110 died at char 16931)."""
    model = os.environ.get("LOCAL_MODEL", "gemma3:12b")
    body = json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False,
                       "options": {"temperature": temperature, "num_ctx": 8192, "num_predict": num_predict,
                                   "repeat_penalty": 1.15}}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read())
    return json.loads(d["response"]), "local:" + model


def remote_llm(prompt, num_predict=2500):
    """the owner's strong free model (key lives in Supabase); None when it is not connected"""
    try:
        c = json.load(open(os.path.join(ROOT, "data/llm.json"), encoding="utf-8"))
    except Exception:
        return None, None
    for k in range(3):
        try:
            r = urllib.request.Request(c["url"], data=json.dumps({"prompt": prompt, "max": num_predict}).encode(),
                                       headers={"Content-Type": "application/json", "x-token": c["token"]})
            with urllib.request.urlopen(r, timeout=150) as x:
                d = json.load(x)
            t = d["text"]
            return json.loads(t[t.index("{"):t.rindex("}") + 1]), "cloud:" + d.get("model", "?")
        except urllib.error.HTTPError as e:
            if e.code in (401, 404, 503):  # not connected
                return None, None
        except Exception as e:
            print("cloud model:", str(e)[:120])
        time.sleep(25 * (k + 1))
    return None, None


def ask(prompt, check, num_predict=2500):
    r, m = remote_llm(prompt, num_predict)
    try:
        if r and check(r):
            return r, m
    except Exception:
        pass
    return ask_free(prompt, check, num_predict)


def ask_free(prompt, check, num_predict=2500):
    """Gemini first if it answers (much stronger), else the local model twice. Returns (result, model) or (None, None)."""
    if os.environ.get("GEMINI_API_KEY"):
        try:  # free tier is overloaded in bursts (run 45250587695: 503 in plan, answered 20 min later in QA) -> 2 rounds
            res, m = gemini(prompt, tries=2)
            if check(res):
                return res, m
            print("gemini: bad shape", str(res)[:200])
        except BaseException as e:  # gemini() raises SystemExit
            print("gemini failed:", str(e)[:200])
    if os.environ.get("USE_LOCAL_LLM", "1") == "1":
        for temp in (0.3, 0.15):
            try:
                res, m = local_llm(prompt, num_predict, temp)
                if check(res):
                    return res, m
                print("local model: bad shape", str(res)[:200])
            except Exception as e:
                print("local model failed:", str(e)[:200])
    return None, None


def gemini(prompt, tries=3):
    key = os.environ["GEMINI_API_KEY"]
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}}).encode()
    last = None
    import time
    for attempt in range(tries):  # free tier is often busy (503) -> retry with backoff
        for m in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
                with urllib.request.urlopen(req, timeout=180) as r:
                    d = json.loads(r.read())
                return json.loads(d["candidates"][0]["content"]["parts"][0]["text"]), m
            except Exception as e:
                last = e
                print("model failed", m, str(getattr(e, "code", "")), str(e)[:200])
        if attempt + 1 < tries:
            time.sleep(60 * (attempt + 1))
    raise SystemExit(f"Gemini failed: {last}")


# ---- free fallback planner (used when Gemini is overloaded): Uzbek keyword -> scene ----
KEYMAP = [
    (("nikoh", "uylan", "to'y", "kelin", "kuyov", "oila", "xotin", "er-xotin", "turmush"), {"setting": "outdoor_day", "props": [{"name": "wedding_house", "slot": "center", "depth": "mid"}], "particles": "petals"}),
    (("payg'ambar", "rasululloh", "sallallohu", "madina", "nabiy"), {"setting": "mosque_night", "props": [{"name": "green_dome", "slot": "center", "depth": "mid"}], "particles": "stars"}),
    (("qur'on", "oyat", "hadis", "kitob", "aytadilar", "rivoyat"), {"setting": "room_night", "props": [{"name": "quran", "slot": "center", "depth": "mid"}, {"name": "rays", "slot": "center", "depth": "mid"}]}),
    (("namoz", "masjid", "sajda", "jamoat", "azon"), {"setting": "outdoor_day", "props": [{"name": "mosque", "slot": "center", "depth": "mid"}], "actors": [{"kind": "man", "action": "walk_in", "slot": "center"}]}),
    (("alloh", "rabb", "duo", "rahmat", "jannat"), {"setting": "outdoor_sunset", "props": [{"name": "rays", "slot": "center", "depth": "mid"}], "particles": "birds"}),
    (("pul", "boylik", "boy", "mol", "dunyo", "savdo", "biznes", "tijorat"), {"setting": "outdoor_day", "props": [{"name": "shop", "slot": "center", "depth": "mid", "label": "BIZNES"}, {"name": "money", "slot": "left", "depth": "near"}]}),
    (("qarz",), {"setting": "room_day", "props": [{"name": "debt", "slot": "center", "depth": "mid"}]}),
    (("mashina", "avtomobil"), {"setting": "street", "car": True}),
    (("o'qi", "ilm", "talaba", "institut", "maktab", "domla", "ustoz"), {"setting": "outdoor_day", "props": [{"name": "school", "slot": "center", "depth": "mid"}], "actors": [{"kind": "man", "action": "walk_in", "slot": "center"}]}),
    (("vaqt", "soat", "umr", "yosh", "yil", "kech"), {"setting": "room_day", "props": [{"name": "calendar", "slot": "left", "depth": "mid"}, {"name": "hourglass", "slot": "right", "depth": "mid"}]}),
    (("sabr", "kut", "bardosh"), {"setting": "outdoor_day", "props": [{"name": "plant", "slot": "center", "depth": "mid"}, {"name": "hourglass", "slot": "right", "depth": "mid"}]}),
    (("shukr", "ne'mat", "non", "rizq", "dasturxon"), {"setting": "room_day", "props": [{"name": "dastarxon", "slot": "center", "depth": "near"}], "actors": [{"kind": "man", "action": "stand", "slot": "left"}, {"kind": "woman", "action": "stand", "slot": "right"}]}),
    (("ota", "ona", "farzand", "bola", "uy"), {"setting": "outdoor_day", "props": [{"name": "house", "slot": "center", "depth": "mid"}], "actors": [{"kind": "man", "action": "stand", "slot": "left"}, {"kind": "woman", "action": "stand", "slot": "right"}]}),
    (("g'azab", "jahl", "asab", "urish"), {"setting": "room_day", "props": [{"name": "anger", "slot": "center", "depth": "mid"}, {"name": "lightning", "slot": "right", "depth": "far"}]}),
    (("gunoh", "harom", "shayton", "xato"), {"setting": "outdoor_day", "props": [{"name": "thorns", "slot": "center", "depth": "mid"}, {"name": "warning", "slot": "right", "depth": "far"}]}),
    (("telefon", "internet", "instagram"), {"setting": "room_day", "props": [{"name": "phone", "slot": "center", "depth": "mid"}]}),
    (("yo'l", "safar", "hayot", "qadam"), {"setting": "meadow", "props": [{"name": "signpost", "slot": "right", "depth": "mid"}], "actors": [{"kind": "man", "action": "walk_away", "slot": "center"}]}),
    (("qalb", "yurak", "muhabbat", "sevgi", "iymon"), {"setting": "outdoor_sunset", "props": [{"name": "heart", "slot": "center", "depth": "mid"}], "particles": "petals"}),
    (("ish", "mehnat", "kasb"), {"setting": "outdoor_day", "props": [{"name": "workshop", "slot": "center", "depth": "mid"}], "actors": [{"kind": "man", "action": "stand", "slot": "left"}]}),
    (("hadya", "sovg'a"), {"setting": "room_day", "props": [{"name": "gift", "slot": "center", "depth": "mid"}]}),
]
DEFAULTS = [{"setting": "outdoor_day", "props": [{"name": "tree", "slot": "right", "depth": "mid"}], "actors": [{"kind": "man", "action": "walk_away", "slot": "center"}], "particles": "birds"},
            {"setting": "village", "props": [], "actors": [{"kind": "man", "action": "stand", "slot": "center"}]},
            {"setting": "meadow", "props": [{"name": "plant", "slot": "center", "depth": "mid"}], "particles": "leaves"}]


def fallback_plan(t):
    words = [w for s in t["segments"] for w in s.get("words", [])]
    shots, last, d = [], -9.0, 0
    for w in words:
        lw = w["w"].lower().strip(" ,.?!«»\"")
        for keys, scene in KEYMAP:
            if any(lw.startswith(k) for k in keys):
                if w["s"] - last >= 2.2 and (not shots or shots[-1].get("_k") != keys[0]):
                    shots.append(dict(scene, start=round(w["s"], 2), _k=keys[0], camera=("push", "right", "left", "pull")[len(shots) % 4]))
                    last = w["s"]
                break
    dur = t.get("duration") or t["segments"][-1]["end"]
    full, cur = [], 0.0  # fill gaps > 6 s with neutral scenes
    for sh in sorted(shots, key=lambda x: x["start"]) + [{"start": dur}]:
        while sh["start"] - cur > 6:
            cur += 3.5
            full.append(dict(DEFAULTS[d % 3], start=round(cur, 2), camera="push")); d += 1
        if sh["start"] < dur:
            full.append(sh); cur = sh["start"]
    if not full or full[0]["start"] > 0:
        full.insert(0, dict(full[0] if full else DEFAULTS[0], start=0.0))
    first = t["segments"][0]["text"].strip()
    hook = " ".join(first.split()[:6]).rstrip(",.") + "?"
    cap = (f"{hook}\n\n{first}\n\nSiz bu haqda nima deysiz? 👇\n\n🎙 @abdulloh.domla\n\n"
           "📌 Buni yaqin do'stingizga yuboring.\n\n#islom #eslatma #abdullohdomla #eslarma #nasihat #iymon")
    return {"hook": hook, "cta": "Obuna bo'ling — har kuni eslatma", "caption": cap,
            "comment": "Alloh barchamizga amal qilishni nasib etsin. Omin deb qoldiring 🤲", "subtitles": {}, "shots": full, "fallback": True}


def paths(src):
    rid = src.split("_")[-1].split(".")[0]
    best = os.path.join(ROOT, "data/transcripts", src + ".best.json")  # tools/stt.py (Uzbek models); planner, render and QA share it
    return rid, best if os.path.exists(best) else os.path.join(ROOT, "data/transcripts", src + ".json"), os.path.join(ROOT, "data/plans", rid + ".json")


UZ_FIX = str.maketrans({"ş": "sh", "Ş": "Sh", "ç": "ch", "Ç": "Ch", "ə": "a", "Ə": "A", "ı": "i", "İ": "I", "ü": "u", "Ü": "U",
                        "ö": "o", "Ö": "O", "ğ": "g'", "Ğ": "G'", "ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'"})
UZ_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '\",.?!-—:;()«»…")


def uz_latin(t):
    """Force subtitles into the Uzbek Latin alphabet (whisper mixes in Turkish/Azeri letters: ş, ç, ə, ı)."""
    t = str(t).translate(UZ_FIX)
    return " ".join(t.split())


def uz_clean(t):
    return bool(t) and all(c in UZ_OK for c in t)


META_RULES = """You are the director of the Instagram account eslarma.uz: short Uzbek Islamic reels made from the audio of
Abdulloh domla. Read the speech (whisper transcript, may contain errors and dialect spelling) and return ONLY JSON:
{"topic": one lowercase word (e.g. tarbiya, shukr, baraka, nikoh, sabr, rizq, namoz),
 "metaphor": ONE simple visual world that carries the whole reel (e.g. "a garden where a small sapling grows" = patience),
 "hook": max 6 words, Uzbek Latin, a question or surprising claim from the strongest idea,
 "cta": "Obuna bo'ling — har kuni eslatma",
 "caption": hook line + 2 short summary lines + a question to the audience + "\\n\\n🎙 @abdulloh.domla\\n\\n📌 Buni ... do'stingizga yuboring." (a concrete person) + 5-8 hashtags incl #islom #eslatma #abdullohdomla #eslarma,
 "comment": a warm Uzbek dua or question, max 200 chars}
All text in correct Uzbek LATIN (o', g', sh, ch). Never invent facts the speaker did not say."""

CHUNK_RULES = """You are the director of eslarma.uz reels (2.5D watercolor storybook animation over the speaker's original audio).
Plan the shots for ONE PART of the speech and correct its subtitles. Return ONLY JSON:
{"subtitles": {"<segment index>": "corrected text", ...},
 "shots": [{"start": float, "says": "words spoken in this shot", "setting": str, "camera": str,
            "props": [{"name": str, "slot": str, "depth": str, "label": str}],
            "actors": [{"kind": "man|woman", "action": "stand|walk_in|walk_away", "slot": str, "back": bool}],
            "text": str, "particles": str, "car": bool}]}
RULES
1. The picture must match the words at that exact second: a new shot starts at the timestamp of the key word.
   Concrete words get the literal object (bola -> child/family, namoz -> prayer_mat/mosque, Qur'on -> quran, Payg'ambar -> green_dome).
2. Stay inside the reel's ONE metaphor world; vary camera (push, pull, left, right); never the same camera twice in a row.
3. Shots 1.5-4 s long; first shot of this part starts exactly at PART START. Max 3 props and 2 actors per shot; no faces ever.
4. Use ONLY names from the CATALOG. Labels: short UPPERCASE Uzbek (max 12 chars) or "". "text" usually "".
5. Subtitles: rewrite EVERY listed segment into correct Uzbek LATIN (o', g', sh, ch, ng; only a-z letters and '),
   same meaning and word order as spoken, no additions; Arabic phrases transliterated in Latin."""


SUB_RULES = """Rewrite ONE sentence of an Uzbek Islamic talk (whisper transcript of a dialect speaker, with Turkish/Kazakh-looking
spelling) into correct standard Uzbek LATIN. Keep the same meaning and word order, add nothing. Use only Latin letters,
o' g' sh ch ng and the apostrophe. Arabic phrases: transliterate in Latin. Return ONLY JSON {"text": "..."}.
Example: "Balamgi bir mətda aytdim" -> {"text": "Bolamga bir marta aytdim"}"""


def _seg_lines(t, idx):
    out = []
    for i in idx:
        s = t["segments"][i]
        ws = " ".join(f"{w['w'].strip()}@{w['s']:.2f}" for w in s.get("words", []))
        out.append(f"[{i}] {s['start']:.2f}-{s['end']:.2f}: {s['text'].strip()}\n    words: {ws}")
    return "\n".join(out)


def _growth_notes():
    """What the analytics loop learned (growth/learned.json, written by tools/competitors.py) -> prompt lines."""
    try:
        g = json.load(open(os.path.join(ROOT, "growth/learned.json"), encoding="utf-8"))
        return "\nWHAT WORKS ON THIS ACCOUNT (use it):\n" + "\n".join("- " + x for x in g.get("prompt_notes", [])[:8])
    except Exception:
        return ""


TEXT_RULES = """You are a native Uzbek editor. Below is a talk by Abdulloh domla as heard by an Uzbek speech recogniser (mostly right).
Where a second recogniser heard it differently, its version is shown after "||": choose the one that makes sense in context.
Make MINIMAL corrections: spelling, capitals, punctuation, obviously misheard words, dialect -> correct standard Uzbek Latin
(o', g', sh, ch; straight apostrophe). Keep every meaning and the word order, add nothing, never paraphrase.
Arabic quotes: correct Latin transliteration. Return ONLY JSON {"subtitles": {"0": "...", "1": "...", ...}} with every index."""

PICK_RULES = """You are the art director of eslarma.uz reels. For every phrase choose the ONE scene whose picture shows what the speaker
MEANS at that moment, in the context of the whole speech (not just a similar word). A concrete thing that is named gets its literal scene.
Religious meanings: "dunyo" (as opposed to oxirat, qalb, ibodat) = worldly wealth -> money; "bu dunyoda" = in this life -> calendar_day or two_paths; never a globe.
"yo'l" = way of life; "nur" = guidance; "qalb / dil" = inner heart; "ne'mat" = blessing; "balo" = trial or misfortune; "nafs" = desires; "rizq" = provision.
If no scene fits, use "none". Neighbouring phrases of the same idea may share a scene, but do not use one scene more than 3 times.
Scenes with a child or family only when the speech is about children or family. "label": "".
Return ONLY JSON {"scenes": [{"i": 0, "scene": "name", "label": ""}, ...]} for ALL phrases."""
PIC_RULES = """You are the art director of eslarma.uz reels (Uzbek Islamic talks). For EVERY phrase write the ONE picture that shows
exactly what the speaker says in that phrase, in the context of the whole speech. The viewer must see the spoken words.
- Concrete things named in the phrase are painted literally (pul -> gold coins, daraxt -> tree, uy -> house, yomg'ir -> rain, masjid -> mosque).
- Abstract ideas become ONE clear symbolic object or place that means the same (sabr -> small sapling in dry soil, umr -> hourglass, gunoh -> dark thorns).
- NO PEOPLE AT ALL: no man, woman, child, hands, figures, silhouettes or crowds. Show objects, nature, houses, streets, mosques, food, animals instead.
- Uzbek setting: clay houses, courtyards with grape vines, blue-tiled domes, bazaars, teapots and piyola, plov, ikat fabric, Rishtan pottery.
- No text, letters, books with pages, screens, crosses or churches. 8-25 English words per picture, one subject, simple.
Return ONLY JSON {"pics": [{"i": 0, "pic": "..."}, ...] for ALL phrases, "cover": "one picture for the whole speech"}."""
PEOPLE = re.compile(r"\b(man|men|woman|women|person|people|boy|girl|child|children|kid|father|mother|son|daughter|family|crowd|figure|silhouette|hand|hands|worshipper|pilgrims?|farmer|imam|he|she)\b", re.I)


def pic_ok(v):
    v = " ".join(str(v or "").split())
    return 4 <= len(v.split()) <= 40 and not PEOPLE.search(v) and not any(b in v.lower() + " " for b in BANNED)


BANNED = ("paper", "banknote", "screen", "sign ", "calendar", "letter", "number", "text", "open book", "open quran", "page", "prophet", "angel",
          "face", "smil", "eyes", "portrait", "newspaper", "document", "ticket")


def recent_art(rid, n=3):
    """palettes and pictures of the last n planned reels, so a new reel never looks like them"""
    import glob
    ps = [p for p in sorted(glob.glob(os.path.join(ROOT, "data/plans/*.json")), key=lambda p: json.load(open(p, encoding="utf-8")).get("planned_at", ""))
          if not p.endswith(f"{rid}.json")][-n:]
    pl = [json.load(open(p, encoding="utf-8")) for p in ps]
    return [p.get("palette") for p in pl], [s.get("visual") for p in pl for s in p.get("shots", []) if s.get("visual") and not s.get("continues")]


def safe_visual(v):
    v = " ".join(str(v or "").split())
    import re  # one recognisable Uzbek look instead of the model's European default
    for who, look in ((r"\b(young |old |elderly |lone )?man\b", "man in white skullcap and dark blue chapan coat"), (r"\b(young |old |elderly )?woman\b", "woman in long hijab"),
                      (r"\bmen\b", "men in white skullcaps and dark coats"), (r"\b(boy|child)\b", "small boy in a white skullcap")):
        if "skullcap" not in v and "hijab" not in v:
            v = re.sub(who, look, v, count=1)
    return v if 5 <= len(v.split()) <= 45 and not any(b in v.lower() + " " for b in BANNED) else ""


def lessons():
    try:
        return "\n" + open(os.path.join(ROOT, "growth/lessons.md"), encoding="utf-8").read()[:2000]
    except Exception:
        return ""


def house_rules():
    try:
        return "\n\nHOUSE RULES:\n" + open(os.path.join(ROOT, "growth/knowledge.md"), encoding="utf-8").read().split("# How the program works")[0][:2500] + lessons()
    except Exception:
        return ""


def owner_wishes():
    try:
        n = json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("wishes") or []
        return "\nThe owner's wishes about the pictures: " + " | ".join(str(x)[:200] for x in n[-6:]) if n else ""
    except Exception:
        return ""


def phrases_of(tpath, subs):
    """split the corrected text at commas / every ~6 words; times come from the whisper word map"""
    from plan_util import build_words2
    out = []
    for i in sorted(int(k) for k in subs):
        seg, cur = [], []
        for w in build_words2(tpath, {i: subs[str(i)]}):
            cur.append(w)
            d = cur[-1]["e"] - cur[0]["s"]
            if (w["w"][-1] in ",.?!:;" and d >= 0.85) or (len(cur) >= 6 and d >= 2.2) or d >= 4.0:
                seg.append(cur); cur = []
        if cur:
            if seg and cur[-1]["e"] - cur[0]["s"] < 1.0:
                seg[-1] += cur
            else:
                seg.append(cur)
        out += seg
    return [{"start": round(p[0]["s"], 2), "text": " ".join(w["w"] for w in p)} for p in out]


def hook_lines(subs):
    """short complete sentences of the speech itself: the only titles a small model may choose"""
    out = []
    for i in sorted(subs, key=int):
        for x in re.split(r"(?<=[.?!])\s+", subs[i].strip()):
            x = x.strip(" ;")
            if x[-1:] in ".?!" and 3 <= len(x.split()) <= 8 and len(x) <= 60 and x not in out:
                out.append(x[:1].upper() + x[1:])
    return out


ASK_LINES = ["Siz bu haqda nima deysiz? 👇", "Sizga qaysi gap ta'sir qildi? 👇", "Fikringizni izohda yozing 👇"]
SEND_LINES = ["📌 Buni yaqiningizga yuboring.", "📌 Buni do'stingizga yuboring.", "📌 Buni oilangizga yuboring."]
NOTE_LINES = ["Eng ko'p ta'sir qilgan gapni izohda yozing 👇", "Davomini xohlaysizmi? Izohda yozing 👇", "Yaqinlaringizga ham yuboring 🤍"]


def safe_texts(hook, rid):
    """caption and comment from fixed, correct Uzbek phrases around a title that the speaker said himself"""
    k = int(hashlib.md5(rid.encode()).hexdigest(), 16) % 3
    cap = f"{hook}\n\n{ASK_LINES[k]}\n\n🎙 @abdulloh.domla\n\n{SEND_LINES[k]}\n\n{settings().get('hashtags') or '#islom #eslatma #abdullohdomla #eslarma #nasihat #iymon'}"
    return {"hook": hook, "caption": cap, "comment": NOTE_LINES[k]}


def cmd_plan(src):
    import scenelib
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import qa, stt
    if os.environ.get("NO_STT") != "1":
        stt.build(src, os.path.join("/tmp", src))
    rid, tpath, ppath = paths(src)
    t = json.load(open(tpath, encoding="utf-8"))
    segs = t["segments"]
    dur = t.get("duration") or segs[-1]["end"]
    flags, models = [], set()
    raw = "\n".join(f"{i}: {s['text'].strip()}" + (f"    || second recogniser: {s['alt']}" if s.get("alt") and s.get("agree", 1) < 0.97 else "")
                    for i, s in enumerate(segs))
    if t.get("agreement") is not None and t["agreement"] < 0.75:
        flags.append(f"fallback-like: speech unclear, two recognisers agree only {t['agreement']:.0%}")

    # 1. correct the whole text at once (context helps), then let a strong editor check it
    def ok_text(r):
        s = r.get("subtitles") if isinstance(r, dict) else None
        return isinstance(s, dict) and all(uz_clean(uz_latin(s.get(str(i), ""))) for i in range(len(segs)))
    note, subs = "", None
    for rnd in range(2):
        r, m = ask(f"{TEXT_RULES}{note}\n\nWHISPER SEGMENTS:\n{raw}", ok_text, 2500)
        if not r:
            break
        models.add(m)
        subs = {str(i): uz_latin(r["subtitles"][str(i)]) for i in range(len(segs))}
        rev = qa.sub_review(subs)
        if not rev or not rev.get("bad"):
            break
        note = f"\nYour previous version was rejected in lines {rev['bad']}: {rev.get('note', '')}. Previous: {json.dumps(subs, ensure_ascii=False)}"
    if not subs:  # the Uzbek recogniser's own text is good enough to continue; QA still judges it
        subs = {str(i): uz_latin(s["text"]) for i, s in enumerate(segs)}
        flags.append("subtitles taken from the recogniser without an editor")
        if t.get("model") != "kotib+rubai" or not all(uz_clean(v) for v in subs.values()):
            raise SystemExit("planner: no model could correct the text")
    speech = " ".join(subs[str(i)] for i in range(len(segs)))

    def ok_meta(m):
        return isinstance(m, dict) and all(str(m.get(k) or "").strip() for k in ("hook", "caption", "comment")) \
            and "#eslarma" in m["caption"] and len(m["hook"].split()) <= 8
    meta, mm = ask(f"{META_RULES}{_growth_notes()}\n\nSPEECH ({dur:.1f} s):\n{speech}", ok_meta, 900)
    if not meta:
        raise SystemExit("planner: no valid hook/caption from any model")
    models.add(mm)
    plan = {k: meta.get(k) for k in ("topic", "metaphor", "hook", "caption", "comment")}
    if not str(mm).startswith("gemini-"):  # a small model must not write Uzbek or Arabic of its own: only the speaker's words + fixed phrases
        lines = hook_lines(subs)
        hk = None
        if lines:
            hk, _ = ask("From this speech choose the line that works best as the title of a short video: clear without context, intriguing, "
                        'on the main topic. Return ONLY JSON {"i": line number}.\n\n' + "\n".join(f"{i}: {x}" for i, x in enumerate(lines)),
                        lambda r: isinstance(r, dict) and str(r.get("i", "")).isdigit() and int(r["i"]) < len(lines), 60)
        if not hk:
            raise SystemExit("planner: no line of the speech fits as a title")
        plan.update(safe_texts(lines[int(hk["i"])], rid))
    plan["hook"], plan["cta"], plan["subtitles"] = uz_latin(plan["hook"]), "Obuna bo'ling — har kuni eslatma", subs

    # 2. one library scene per phrase
    ph = phrases_of(tpath, subs)

    def ok_pick(r):
        s = r.get("scenes") if isinstance(r, dict) else None
        try:
            return {int(x["i"]) for x in s} >= set(range(len(ph))) and all(x.get("scene") in scenelib.SCENES or x.get("scene") == "none" for x in s)
        except Exception:
            return False
    listing = "\n".join(f"{i}: {p['text']}   (word hints: {', '.join(scenelib.by_words(p['text'])[:3]) or '-'})" for i, p in enumerate(ph))
    import datetime, open_art, art_prompts
    used_pal, used_vis = recent_art(rid)
    free = [p for p in open_art.PALETTES if p not in used_pal]
    plan["palette"] = free[int(hashlib.md5(rid.encode()).hexdigest(), 16) % len(free)]
    if settings().get("palette") in open_art.PALETTES:
        plan["palette"] = settings()["palette"]
    plan["planned_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    wish = owner_wishes() + house_rules()
    r, m = ask(f"{PICK_RULES}{wish}\n\nSCENES\n{scenelib.catalog()}\n\nWHOLE SPEECH: {speech}\n\nPHRASES:\n{listing}", ok_pick, 4000)
    if not r:
        raise SystemExit("planner: no model could pick scenes")  # never guess pictures
    models.add(m)

    def ok_theme(x):
        return isinstance(x, dict) and len([s for s in x.get("theme") or [] if s in scenelib.SCENES]) >= 4
    th, _ = ask("Choose the 6 scenes that best illustrate the MAIN TOPIC of the whole speech below (not single words).\n"
                f'Return ONLY JSON {{"theme": ["scene", ...]}}.\n\nSCENES\n{scenelib.catalog()}\n\nWHOLE SPEECH: {speech}', ok_theme, 200)
    theme = [s for s in (th or {}).get("theme", []) if s in scenelib.SCENES]
    print("theme:", theme)
    pics, cover_pic = {}, None
    pr, _ = ask(f"{PIC_RULES}{owner_wishes()}\n\nWHOLE SPEECH: {speech}\n\nPHRASES:\n" + "\n".join(f"{i}: {p['text']}" for i, p in enumerate(ph)),
                lambda x: isinstance(x, dict) and isinstance(x.get("pics"), list) and sum(pic_ok(y.get("pic")) for y in x["pics"] if isinstance(y, dict)) >= 0.8 * len(ph), 4000)
    if pr:
        pics = {int(y["i"]): " ".join(y["pic"].split()) for y in pr["pics"] if isinstance(y, dict) and str(y.get("i", "")).isdigit() and pic_ok(y.get("pic"))}
        cover_pic = pr.get("cover") if pic_ok(pr.get("cover")) else None
    print(f"own pictures: {len(pics)} of {len(ph)}")

    def fresh():  # topic scenes that still have an unseen painting
        return [s for s in theme if any(v not in shown for v in art_prompts.ART.get(s, []))]
    pick = {int(x["i"]): x for x in r["scenes"]}
    shots, none = [], []
    shown = list(used_vis)  # paintings of the last reels and of this one
    for i, p in enumerate(ph):
        sc, label = pick[i]["scene"], str(pick[i].get("label") or "")
        if i in pics:  # the picture of exactly these words
            if shots and p["start"] - shots[-1]["start"] < 1.4:
                shots[-1]["says"] += " " + p["text"]
                continue
            shown.append(pics[i])
            shots.append({"start": 0.0 if not shots else p["start"], "says": p["text"], "scene": sc if sc in scenelib.SCENES else "question", "label": "", "visual": pics[i]})
            continue
        hits = scenelib.by_words(p["text"])
        if hits and (sc == "none" or (m.startswith("local") and sc not in hits)):
            sc = hits[0]
        if sc == "none":
            if len(p["text"].split()) > 4 and not p["text"].strip().endswith("?"):  # short fillers may keep the previous picture
                none.append(p["text"])
            if fresh() and (not shots or p["start"] - shots[-1]["start"] >= 2.4):  # no picture of its own: show the topic of the speech
                sc = fresh()[len(shots) % len(fresh())]
            elif shots:  # keep the previous picture rather than show something unrelated
                shots[-1]["says"] += " " + p["text"]
                continue
            else:
                sc = "question"
        if sc == "calendar_day" and not label:
            label = p["text"].split()[0].strip(",.")
        start = 0.0 if not shots else p["start"]
        if shots and shots[-1]["scene"] == sc and shots[-1]["label"] == label and start - shots[-1]["start"] < 4.0:
            shots[-1]["says"] += " " + p["text"]
            continue
        vis = art_prompts.choose(sc, shown)
        if vis in shown:  # every variant was already seen: another picture of the topic, else keep the previous one
            if fresh():
                sc = fresh()[0]; vis = art_prompts.choose(sc, shown)
            elif shots:
                shots[-1]["says"] += " " + p["text"]
                continue
        shown.append(vis)
        shots.append({"start": start, "says": p["text"], "scene": sc, "label": label, "visual": vis})
    if len(none) > (0.45 if theme else 0.2) * len(ph):
        flags.append(f"fallback-like: no matching scene for {len(none)} of {len(ph)} phrases: {none[:4]}")
    full = []  # long shots continue with another camera framing
    for k, s in enumerate(shots):
        end = shots[k + 1]["start"] if k + 1 < len(shots) else dur
        n = int((end - s["start"]) // 5.0)
        full.append(s)
        for j in range(1, n + 1):
            c = dict(s, start=round(s["start"] + j * (end - s["start"]) / (n + 1), 2), continues=True)
            alt = art_prompts.choose(s["scene"], shown)
            if alt in shown:
                alt = next((v for x in theme for v in art_prompts.ART.get(x, []) if v not in shown), alt)
            if not pics and alt and alt not in shown and len(set(shown) - set(used_vis)) < 20:  # a new painting, not the same frame again
                shown.append(alt); c["visual"] = alt; c["fresh"] = True
            full.append(c)
    weak = [s["says"] for s in shots if not s["visual"]]
    if len(weak) > 0.15 * len(shots):
        flags.append(f"fallback-like: {len(weak)} shots have no usable painting description")
    plan["shots"] = full
    cv, _ = ask("One painting will be the COVER of this reel. Choose the ONE scene that shows the meaning of the whole speech together with its title at first glance.\n"
                f'Return ONLY JSON {{"cover": "scene"}}.{house_rules()}\n\nSCENES\n{scenelib.catalog()}\n\nTITLE: {plan["hook"]}\nWHOLE SPEECH: {speech}',
                lambda x: isinstance(x, dict) and x.get("cover") in scenelib.SCENES, 60)
    cs = (cv or {}).get("cover") or (theme[0] if theme else None)
    opts = art_prompts.ART.get(cs) or []
    plan["cover_visual"] = cover_pic or next((v for v in opts if v not in used_vis), opts[0] if opts else None)
    uses = {}  # the same scene again = another variant/seed and another framing, never the identical frame
    for s in full:
        k = uses[s["scene"]] = uses.get(s["scene"], 0) + (0 if s.get("continues") else 1)
        s["seed"] = k
    if full and not pics and max(uses.values()) > max(3, 0.3 * len(full)):  # own pictures differ even within one scene
        flags.append(f"repetitive: one scene used {max(uses.values())} times in {len(full)} shots")
    for s in full:
        s["palette"] = plan["palette"]
    plan.update(model=", ".join(sorted(x for x in models if x)), duration=dur, quality_flags=flags)
    os.makedirs(os.path.dirname(ppath), exist_ok=True)
    json.dump(plan, open(ppath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("plan ok", len(full), "shots via", plan["model"], "flags:", flags or "none")
    for s in full:
        print(f"  {s['start']:6.2f} {s['scene']:18} {s['label']:10} | {s['says']}" + (f"\n         -> {s['visual']}" if s.get("visual") and not s.get("continues") else ""))


CAMS_NEXT = {"push": "left", "left": "pull", "pull": "right", "right": "push"}


def paint(plan, shots, rid):
    """paint every distinct visual with the open model (own process, so its memory is freed); {visual: jpg path}"""
    if os.environ.get("OPEN_ART", "1") != "1":
        return {}
    vis = list(dict.fromkeys([s["visual"] for s in shots if s.get("visual")] + ([plan["cover_visual"]] if plan.get("cover_visual") else [])))
    if not vis:
        return {}
    import art_prompts
    out, pj = f"/tmp/art_{rid}", f"/tmp/art_{rid}.json"
    seed = int(hashlib.md5((rid + str(plan.get("planned_at"))).encode()).hexdigest()[:6], 16)
    json.dump([{"name": f"p{k:02d}", "prompt": v, "motion": motion_of(v) if settings().get("video_on") != "0" else "", "palette": plan.get("palette"), "style": art_style(), "seed": seed + k, "alts": [a for a in art_prompts.objects(art_prompts.scene_of(v), vis) if a not in vis]} for k, v in enumerate(vis)], open(pj, "w"))
    try:  # free the local planner model's memory first
        urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(
            {"model": os.environ.get("LOCAL_MODEL", "gemma3:4b"), "keep_alive": 0}).encode(), headers={"Content-Type": "application/json"}), timeout=30).read()
    except Exception:
        pass
    gpu = False
    if os.path.exists(os.path.expanduser("~/.kaggle/kaggle.json")):  # free Kaggle GPU: full SDXL, 30 steps; the CPU path stays as the fallback
        try:
            subprocess.run(["bash", "kaggle/run.sh", "art_gpu.py", pj, "tools/open_art.py", "tools/art_prompts.py"], cwd=ROOT, timeout=165 * 60)
            src = "/tmp/kout/out" if os.path.isdir("/tmp/kout/out") else "/tmp/kout"
            os.makedirs(out, exist_ok=True)
            for f in os.listdir(src):
                if f.endswith((".jpg", ".json", ".mp4")):  # .mp4 = the moving clips made on the GPU
                    import shutil
                    shutil.copy(os.path.join(src, f), os.path.join(out, f))
            got = sum(os.path.exists(f"{out}/p{k:02d}.jpg") for k in range(len(vis)))
            gpu = got >= 0.85 * len(vis)
            print(f"gpu paintings: {got} of {len(vis)}", flush=True)
        except Exception as e:
            print("gpu painting failed:", str(e)[:200])
    if not gpu:
        try:
            subprocess.run([sys.executable, os.path.join(ROOT, "tools/open_art.py"), pj, out], check=True, timeout=120 * 60)
        except Exception as e:
            print("painting failed:", str(e)[:200])
    art = {v: f"{out}/p{k:02d}.jpg" for k, v in enumerate(vis) if os.path.exists(f"{out}/p{k:02d}.jpg")}
    if len(art) < 0.85 * len(vis):  # mixed styles look broken: say so, QA will stop the reel
        plan.setdefault("quality_flags", []).append(f"fallback-like: only {len(art)} of {len(vis)} pictures painted")
        json.dump(plan, open(paths(f"src_{rid}.mp4")[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:
        sc = json.load(open(f"{out}/_clip.json"))
        plan["clip"] = {"min": min(sc.values()), "mean": round(sum(sc.values()) / len(sc), 3), "n": len(sc)}
        json.dump(plan, open(paths(f"src_{rid}.mp4")[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print("no clip scores:", e)
    print("painted", len(art), "of", len(vis), plan.get("clip"))
    return art


ART_MOVES = [("push", (1.02, 1.16), (.5, .5)), ("left", (1.12, 1.14), (.5, .48)), ("pull", (1.18, 1.03), (.5, .5)), ("up", (1.1, 1.16), (.5, .5)),
             ("right", (1.12, 1.14), (.5, .48)), ("push", (1.06, 1.22), (.5, .42))]
ART_AIR = {"night": ["dust", 26], "rain": ["rain", 45], "winter": ["snow", 45], "spring": ["petals", 18], "rose": ["leaves", 8], "golden": ["dust", 26], "mint": ["leaves", 8], "desert": ["dust", 34]}


def art_shot(jpg, name, i, s):
    """one painting as a full-frame 2.5D shot: camera move + drifting air particles"""
    import cv2
    import numpy as np
    from scenes import SW, SH
    im = cv2.imread(jpg)
    k = max(SW / im.shape[1], SH / im.shape[0])
    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_LANCZOS4)
    y, x = (im.shape[0] - SH) // 2, (im.shape[1] - SW) // 2
    im = im[y:y + SH, x:x + SW]
    im = np.clip(cv2.addWeighted(im, 1.35, cv2.GaussianBlur(im, (0, 0), 2.2), -0.35, 0), 0, 255).astype(np.uint8)
    os.makedirs("l25", exist_ok=True)
    png = f"l25/{name}_art.png"
    cv2.imwrite(png, im)
    mv, zoom, focus = ART_MOVES[(i + (3 if s.get("continues") else 0)) % len(ART_MOVES)]
    if s.get("continues") and not s.get("fresh"):  # second half of a long phrase: a closer view of the same painting
        zoom, focus = (1.38, 1.5), (.5, .45)
    kind, n = ART_AIR.get(s.get("palette"), ["dust", 24])
    return {"start": float(s["start"]), "move": mv, "layers": [{"png": png, "depth": 1.0}], "screen_particles": [[kind, n, [0, 100, 1080, 1500]]],
            "cam": {"zoom": list(zoom), "focus": list(focus)}}


def settings():
    try:
        return json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("settings") or {}
    except Exception:
        return {}


def art_style():
    try:
        return json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("art_style") or "uzbek"
    except Exception:
        return "uzbek"


def make_cover(plan, jpg, rid):
    """1080x1920 cover: the first painting, darkened, with the title inside the 3:4 part that the profile grid shows"""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont
    im = Image.open(jpg).convert("RGB")
    k = max(1080 / im.width, 1920 / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - 1080) // 2, (im.height - 1920) // 2
    im = ImageEnhance.Color(im.crop((x, y, x + 1080, y + 1920))).enhance(1.1)
    sh = Image.new("L", (1, 1920))
    for j in range(1920):
        sh.putpixel((0, j), int(60 + 165 * max(0, min(1, (j - 760) / 620)) - 120 * max(0, (j - 1560) / 360)))
    im = Image.composite(Image.new("RGB", im.size, (10, 26, 20)), im, sh.resize(im.size))
    d = ImageDraw.Draw(im)
    words, size = plan["hook"].split(), 124
    while True:
        f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", size)
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if not cur or f.getlength(t) <= 900:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if (len(lines) <= 4 and max(f.getlength(l) for l in lines) <= 920) or size <= 60:
            break
        size -= 6
    lh = int(size * 1.16)
    y0 = 1500 - lh * len(lines)
    d.rounded_rectangle([80, y0 - 56, 220, y0 - 44], radius=6, fill=(226, 184, 79))
    for j, l in enumerate(lines):
        d.text((80, y0 + j * lh), l, font=f, fill=(255, 250, 238))
    d.text((80, 1530), "@eslarma.uz", font=ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 44), fill=(246, 228, 180))
    im.save(os.path.join(ROOT, "out", f"cover_{rid}.jpg"), quality=92)


LIVE = (("stream", "water flows and sparkles"), ("water", "water moves and glitters"), ("tree", "leaves sway in the wind"), ("orchard", "branches sway, petals fall"),
        ("lantern", "the flame flickers"), ("lamp", "the flame flickers"), ("bird", "birds move and flap"), ("field", "grass waves in the wind"),
        ("walking", "the man walks forward step by step"), ("rain", "rain falls"), ("snow", "snow falls"), ("car", "the car drives forward"),
        ("sheep", "the sheep graze and move"), ("horse", "the horse moves its head and tail"), ("sand", "sand runs down"), ("crowd", "people walk"),
        ("street", "people walk"), ("raised arms", "the man slowly raises his arms"), ("sky", "clouds drift"), ("teapot", "steam rises from the tea"),
        ("plov", "steam rises from the food"), ("candle", "the flame flickers"), ("sea", "waves roll"), ("coins", "coins glitter"), ("rose", "petals tremble"))


def motion_of(v):
    """what moves in the painting: the GPU makes a real clip from this"""
    acts = [a for k, a in LIVE if k in v][:3] or ["light changes gently, dust floats in the air"]
    return f"{art_style()} animation, {v}, {', '.join(acts)}, clouds drift slowly, no people, smooth slow camera push in"


def add_video(built, shots, art, rid):
    """every painting becomes a moving clip; what is not animated keeps the still painting with a moving camera"""
    items, where = [], []
    for i, (b, s) in enumerate(zip(built, shots)):
        jpg = art.get(s.get("visual"))
        if not jpg:
            continue
        acts = [a for k, a in LIVE if k in s["visual"]][:3] or ["light changes gently, dust floats in the air"]
        items.append({"jpg": jpg, "mp4": f"/tmp/art_{rid}/v{i:02d}.mp4", "seconds": float(b["end"]) - float(b["start"]) + 0.6,
                      "prompt": f"{art_style()} animation, {s['visual']}, {', '.join(acts)}, clouds drift slowly, no people, smooth slow camera push in"})
        where.append(i)
    if not items or os.environ.get("OPEN_VIDEO", "1") != "1" or settings().get("video_on") == "0":
        return
    for it in items:  # clips already made on the Kaggle GPU next to the painting: fit them to the phrase length
        clip = os.path.join(os.path.dirname(it["jpg"]), "v_" + os.path.basename(it["jpg"])[:-4] + ".mp4")
        if os.path.exists(clip) and os.path.getsize(clip) > 5000:
            sl = max(1.0, min(1.6, it["seconds"] / 4.0))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", f"setpts={sl:.3f}*PTS,tpad=stop_mode=clone:stop_duration=6,fps=24",
                            "-t", f"{it['seconds']:.2f}", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", it["mp4"]])
    rest = [it for it in items if not (os.path.exists(it["mp4"]) and os.path.getsize(it["mp4"]) > 5000)]
    print(f"gpu clips: {len(items) - len(rest)} of {len(items)}", flush=True)
    pj = f"/tmp/art_{rid}_v.json"
    json.dump(rest, open(pj, "w"))
    try:
        if rest:
            subprocess.run([sys.executable, os.path.join(ROOT, "tools/open_video.py"), pj, str(55 * 60)], timeout=80 * 60, check=True)
    except Exception as e:
        print("animation failed:", str(e)[:200])
    for it, i in zip(items, where):
        if os.path.exists(it["mp4"]) and os.path.getsize(it["mp4"]) > 5000:
            built[i]["video"] = it["mp4"]


def cmd_render(src, video):
    os.chdir(os.path.join(ROOT, "studio"))  # layer PNGs are written relative to studio/
    import compose
    from plan_util import build_words2
    rid, tpath, ppath = paths(src)
    plan = json.load(open(ppath))
    dur = float(plan["duration"])
    shots = sorted([s for s in plan["shots"] if 0 <= float(s.get("start", 0)) < dur - 0.6], key=lambda s: float(s["start"]))
    if not shots or float(shots[0]["start"]) > 0.05:
        shots.insert(0, dict(shots[0] if shots else {"setting": "outdoor_day"}, start=0.0))
    clean = []
    for s in shots:  # drop shots shorter than 0.8 s
        if clean and float(s["start"]) - float(clean[-1]["start"]) < 0.8:
            continue
        clean.append(s)
    import scenelib
    art = paint(plan, clean, rid)
    built = []
    for i, s in enumerate(clean):
        if art.get(s.get("visual")):
            d = art_shot(art[s["visual"]], f"a{rid}_{i}", i, s)
        elif s.get("scene") in scenelib.SCENES:
            d = scenelib.build(s["scene"], f"a{rid}_{i}", int(s.get("seed", 1 + i % 5)), s.get("label", ""))
            d["start"] = float(s["start"])
            if s.get("continues"):
                d["move"] = CAMS_NEXT.get(d["move"], "pull"); d["cam"] = {"zoom": [1.22, 1.32], "focus": [0.5, 0.5]}
            elif int(s.get("seed", 1)) % 2 == 0 and "cam" not in d:
                d["cam"] = {"zoom": [1.18, 1.3], "focus": [0.5, 0.52]}  # second use of a scene = medium shot
        else:
            d = compose.build_shot(s, f"a{rid}_{i}")
        built.append(d)
    for i, b in enumerate(built):
        b["end"] = built[i + 1]["start"] if i + 1 < len(built) else dur
    add_video(built, clean, art, rid)
    first = art.get(plan.get("cover_visual")) or next((art[s["visual"]] for s in clean if art.get(s.get("visual"))), None)
    if first:
        try:
            make_cover(plan, first, rid)
        except Exception as e:
            print("cover failed:", str(e)[:200])
    fixed = {int(k): v for k, v in plan.get("subtitles", {}).items() if str(v).strip()}
    for i, seg in enumerate(json.load(open(tpath))["segments"]):
        fixed.setdefault(i, seg["text"].strip())  # fall back to raw whisper text
    out = os.path.join(ROOT, "out", f"eslarma_{rid}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    st = settings()
    rplan = {"settings": st, "duration": dur, "scenes": built, "words": build_words2(tpath, fixed), "keywords": [],
             "hook": "" if st.get("title_on") == "0" else plan.get("hook", ""), "cta": st.get("cta") or plan.get("cta", "Obuna bo'ling — har kuni eslatma"), "handle": "eslarma.uz",
             "source": video, "video_only": f"/tmp/v_only{rid}.mp4", "output": out}
    rp = os.path.join(ROOT, "studio", f"plan_auto_{rid}.json")
    json.dump(rplan, open(rp, "w"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, "animate.py", rp], cwd=os.path.join(ROOT, "studio"), check=True)
    print("render ok", out)


def _md5_audio(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:a", "-c", "copy", "-f", "data", "-"], capture_output=True)
    return hashlib.md5(r.stdout).hexdigest()


def cmd_check(src, video):
    rid, _, ppath = paths(src)
    out = os.path.join(ROOT, "out", f"eslarma_{rid}.mp4")
    probs = []
    if _md5_audio(out) != _md5_audio(video):
        probs.append("audio differs from original")
    plan = json.load(open(ppath))
    if len(plan.get("shots", [])) < 6:
        probs.append("too few shots")
    if not plan.get("caption") or "#eslarma" not in plan["caption"]:
        probs.append("caption missing hashtags")
    if len(plan.get("comment", "")) > 290:
        plan["comment"] = plan["comment"][:280]
        json.dump(plan, open(ppath, "w"), ensure_ascii=False, indent=1)
    # blank-frame check: sample frames, fail if any is nearly uniform
    import numpy as np
    for t in (1.0, float(plan["duration"]) / 2, float(plan["duration"]) - 1.5):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", "-vf", "scale=108:192",
                            "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
        a = np.frombuffer(r.stdout, dtype=np.uint8)
        if a.size and a.std() < 6:
            probs.append(f"blank frame at {t:.1f}s")
    if not probs and os.environ.get("QA_SEPARATE") != "1":
        # the 9-point checklist gate also runs here, so even the old workflow never publishes an unchecked reel
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import qa
        qa.main(src, video)
        rep = json.load(open(os.path.join(ROOT, "data/qa", f"{rid}.json"), encoding="utf-8"))
        if not rep.get("pass"):
            probs.append("9-point QA failed: " + ", ".join(v["name"] for v in rep["items"].values() if not v["ok"]))
        mode = json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("mode", "auto")
        if mode == "approve" and not probs:
            probs.append("approve mode: needs the new auto.yml to send the reel to the owner")
        if probs and os.environ.get("GITHUB_EVENT_NAME") == "schedule":
            import tg
            sheet = os.path.join(ROOT, "out", f"qa_{rid}.jpg")
            if os.path.exists(sheet):
                tg.photo(sheet, f"Ролик {rid} не прошёл проверку — НЕ опубликован.")
            tg.text(f"⚠️ Ролик {rid} «{plan.get('hook', '')}» не опубликован, вернул в очередь.\nПричина: {'; '.join(probs)[:800]}")
    print("CHECK", "OK" if not probs else probs)
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    c, src = sys.argv[1], sys.argv[2]
    video = sys.argv[3] if len(sys.argv) > 3 else os.path.join("/tmp", src)
    {"plan": lambda: cmd_plan(src), "render": lambda: cmd_render(src, video), "check": lambda: cmd_check(src, video)}[c]()
