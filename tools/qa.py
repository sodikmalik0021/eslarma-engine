"""Quality gate for an auto reel: the owner's 9-point checklist (studio/README.md), automated.

  python3 tools/qa.py <src_name> <source_video>   -> data/qa/<id>.json, out/qa_<id>.jpg; prints PASS/FAIL
Exit code is always 0; read "pass" from the json. A reel is published automatically ONLY when every point is ok.
Vision review: Gemini (GEMINI_API_KEY) first, local ollama gemma3 (multimodal) as backup. If no reviewer answers,
point 1/2/4/5 stay unverified -> FAIL (never publish an unchecked reel).
"""
import base64, json, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def frame(video, t, w=270, h=480):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", video, "-frames:v", "1",
                        "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    return a.reshape(h, w, 3) if a.size == w * h * 3 else None


def font(size):
    for p in ("/usr/share/fonts/truetype/inter/Inter-Regular.ttf", "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(video, shots, path):
    cols = 6
    rows = (len(shots) + cols - 1) // cols
    W, H, T = 270, 480, 70
    im = Image.new("RGB", (cols * W, rows * (H + T)), "white")
    d, f = ImageDraw.Draw(im), font(15)
    for k, (s, e, says) in enumerate(shots):
        fr = frame(video, (s + e) / 2)
        x, y = (k % cols) * W, (k // cols) * (H + T)
        if fr is not None:
            im.paste(Image.fromarray(fr), (x, y))
        txt = f"#{k + 1} {s:.1f}s: {says}"[:110]
        for j in range(3):
            d.text((x + 4, y + H + 3 + j * 21), txt[j * 37:(j + 1) * 37], fill="black", font=f)
    im.save(path, quality=82)
    return path


REVIEW = """You are the strict quality reviewer of eslarma.uz reels (Uzbek Islamic reminders, 2.5D watercolor storybook
animation over a speaker's voice). The image is a contact sheet: one frame per shot; under each frame: shot number, time
and the words spoken in that shot. Judge ONLY what you see. Return ONLY JSON:
{"words_match": {"ok": bool, "bad_shots": [int], "note": str},      # each picture clearly shows what the words say
 "recognizable": {"ok": bool, "bad_shots": [int], "note": str},     # every object instantly recognizable at phone size
 "people": {"ok": bool, "bad_shots": [int], "note": str},           # faceless simple figures, not cut by frame, not under text
 "style": {"ok": bool, "bad_shots": [int], "note": str},            # consistent watercolor storybook look, no empty/unfinished areas
 "perspective": {"ok": bool, "bad_shots": [int], "note": str},   # sizes plausible, nothing cut off or floating
 "score": int}                                                       # 1-10 overall; 7+ = good enough to publish
Be strict: a frame that is mostly empty background, a random object unrelated to the words, or a broken/overlapping
drawing is NOT ok. Publishing a bad reel hurts the account more than skipping a day."""


def review(img_path):
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        from auto_reel import MODELS
        body = json.dumps({"contents": [{"parts": [{"text": REVIEW}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
                           "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}).encode()
        import time
        strong = [x for x in MODELS if "lite" not in x]
        # free Gemini often answers 503 for a while: keep trying the strong models (~35 min) before using a lite one
        for attempt in range(3):
            for m in (strong if attempt < 2 else MODELS):
                try:
                    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                                 data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
                    with urllib.request.urlopen(req, timeout=60) as r:
                        d = json.loads(r.read())
                    return json.loads(d["candidates"][0]["content"]["parts"][0]["text"]), m
                except Exception as e:
                    print("reviewer failed", m, str(e)[:150])
            if attempt < 2:
                time.sleep(75)
    try:
        model = os.environ.get("LOCAL_MODEL", "gemma3:4b")
        body = json.dumps({"model": model, "prompt": REVIEW, "images": [b64], "format": "json", "stream": False,
                           "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": 900}}).encode()
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(json.loads(r.read())["response"]), "local:" + model
    except Exception as e:
        print("local reviewer failed", str(e)[:150])
    return None, None


SUBS = """You are a native Uzbek editor. Below are the on-screen subtitles of a short Islamic reel, one per line as
"<index>: text". Each line must be correct, natural STANDARD Uzbek in Latin script (o', g', sh, ch), with no dialect or
Turkish/Kazakh spelling, no broken or invented words; Arabic quotes must be a correct Latin transliteration.
Return ONLY JSON {"bad": [indexes of lines that are not correct standard Uzbek], "note": "short reason"}. Be strict."""


def sub_review(subs):
    """Strong model only (Gemini non-lite). None = nobody answered -> point 7 fails."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    from auto_reel import MODELS
    text = "\n".join(f"{k}: {v}" for k, v in sorted(subs.items(), key=lambda x: int(x[0])))
    body = json.dumps({"contents": [{"parts": [{"text": SUBS + "\n\n" + text}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}).encode()
    import time
    for attempt in range(2):
        for m in [x for x in MODELS if "lite" not in x]:
            try:
                req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                             data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"])
                if isinstance(d.get("bad"), list):
                    return d
            except Exception as e:
                print("subtitle reviewer failed", m, str(e)[:120])
        time.sleep(75)
    return None


def md5_audio(p):
    import hashlib
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:a", "-c", "copy", "-f", "data", "-"], capture_output=True)
    return hashlib.md5(r.stdout).hexdigest(), len(r.stdout)


def text_evidence(t, subs):
    """the subtitles are what is really said: two independent Uzbek recognisers agree and the editor changed little"""
    import difflib
    from stt import norm
    segs = t["segments"]
    if t.get("model") != "kotib+rubai" or not segs:
        return False, "no two-model transcript"
    low = [i for i, s in enumerate(segs) if s.get("agree", 0) < 0.6]
    far = [i for i, s in enumerate(segs) if difflib.SequenceMatcher(None, " ".join(map(norm, s["text"].split())),
                                                                    " ".join(map(norm, subs.get(str(i), "").split()))).ratio() < 0.72]
    ok = t.get("agreement", 0) >= 0.88 and len(low) <= 0.1 * len(segs) and len(far) <= 0.15 * len(segs)
    return ok, f"recognisers agree {t.get('agreement', 0):.0%}, unclear lines {low or '-'}, rewritten lines {far or '-'}"


def main(src, source):
    from auto_reel import paths, uz_clean
    rid, tpath, ppath = paths(src)
    out = os.path.join(ROOT, "out", f"eslarma_{rid}.mp4")
    plan = json.load(open(ppath, encoding="utf-8"))
    rp = json.load(open(os.path.join(ROOT, "studio", f"plan_auto_{rid}.json"), encoding="utf-8"))
    dur = float(plan["duration"])
    scenes = rp["scenes"]
    says = {round(float(s["start"]), 2): s.get("says", "") for s in plan["shots"]}
    shots = [(float(s["start"]), float(s["end"]), says.get(round(float(s["start"]), 2), "")) for s in scenes]
    res = {}

    def put(n, name, ok, note=""):
        res[str(n)] = {"name": name, "ok": bool(ok), "note": note}

    os.makedirs(os.path.join(ROOT, "data/qa"), exist_ok=True)
    img = sheet(out, shots, os.path.join(ROOT, "out", f"qa_{rid}.jpg"))
    rv, rmodel = review(img)
    flags = plan.get("quality_flags", [])
    if rv:
        g = lambda k: rv.get(k) if isinstance(rv.get(k), dict) else {"ok": False, "note": "no answer"}
        score = int(rv.get("score") or 0)
        # a weak judge (lite / local) is trusted only together with the objective CLIP check of every painting
        strong = rmodel and not rmodel.startswith("local:") and "lite" not in rmodel
        c = plan.get("clip") or {}
        clip_ok = c.get("min", 0) >= 0.22 and c.get("mean", 0) >= 0.26
        bad1 = g("words_match").get("bad_shots") or []
        put(1, "words = picture", g("words_match").get("ok") and score >= 8 and len(bad1) <= 1 and (strong or clip_ok)
            and not any("fallback" in f or "repetitive" in f for f in flags),
            f"{g('words_match').get('note', '')} score {score}/10 ({rmodel}); bad shots {bad1}; clip {c}; flags {flags}")
        put(3, "perspective", g("perspective").get("ok"), f"{g('perspective').get('note', '')} bad {g('perspective').get('bad_shots')}")
        put(2, "recognizable", g("recognizable").get("ok"), f"{g('recognizable').get('note', '')} bad {g('recognizable').get('bad_shots')}")
        put(4, "people", g("people").get("ok"), f"{g('people').get('note', '')} bad {g('people').get('bad_shots')}")
        put(5, "style", g("style").get("ok"), f"{g('style').get('note', '')} bad {g('style').get('bad_shots')}")
    else:
        for n, name in ((1, "words = picture"), (3, "perspective"), (2, "recognizable"), (4, "people"), (5, "style")):
            put(n, name, False, "no vision reviewer answered - unverified")
    # 6 motion: each shot must change between its start and end; no blank frames
    still, blank = [], []
    for k, (s, e, _) in enumerate(shots):
        f0, f1 = frame(out, s + 0.25, 108, 192), frame(out, max(s + 0.3, e - 0.25), 108, 192)
        if f0 is None or f1 is None:
            blank.append(k + 1); continue
        if f0.std() < 6:
            blank.append(k + 1)
        if np.abs(f0.astype(int) - f1.astype(int)).mean() < 1.2:
            still.append(k + 1)
    lens = [e - s for s, e, _ in shots]
    put(6, "motion", not still and not blank and max(lens) <= 6.5,
        f"still shots {still or '-'}; blank {blank or '-'}; longest shot {max(lens):.1f}s")
    subs = plan.get("subtitles", {})
    nseg = len(json.load(open(tpath, encoding="utf-8"))["segments"])
    badsub = [k for k, v in subs.items() if not uz_clean(v)]
    uncorr = [f for f in flags if f.startswith("subtitle")]
    sr = sub_review(subs)  # a strong editor when one answers ...
    ev_ok, ev = text_evidence(json.load(open(tpath, encoding="utf-8")), subs)  # ... otherwise measured evidence
    lang_ok = (not sr.get("bad") or (ev_ok and len(sr["bad"]) <= 0.1 * max(1, nseg))) if sr is not None else ev_ok
    put(7, "subtitles", len(subs) == nseg and not badsub and not uncorr and plan.get("hook") and lang_ok,
        f"{len(subs)}/{nseg} segments; non-Latin {badsub or '-'}; not corrected {len(uncorr)}; editor: {sr.get('bad') if sr else 'no answer'} "
        f"{(sr or {}).get('note', '')[:120]}; {ev}")
    a, b = md5_audio(out), md5_audio(source)
    vlen = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                                capture_output=True, text=True).stdout or 0)
    slen = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", source],
                                capture_output=True, text=True).stdout or 0)
    put(8, "audio", a == b and a[1] > 0 and abs(vlen - slen) < 0.6, f"md5 {'same' if a == b else 'DIFFERENT'}, {vlen:.1f}s of source {slen:.1f}s")
    cap = plan.get("caption", "")
    put(9, "caption/hashtags/comment/cover", "#eslarma" in cap and cap.count("#") >= 4 and 0 < len(plan.get("comment", "")) <= 290
        and len(cap) < 2200, "cover 800 ms (hook frame); story is posted after the reel (non-fatal)")
    ok = all(v["ok"] for v in res.values())
    rep = {"src": src, "pass": ok, "items": dict(sorted(res.items(), key=lambda x: int(x[0]))), "reviewer": rmodel,
           "flags": flags, "sheet": f"out/qa_{rid}.jpg"}
    json.dump(rep, open(os.path.join(ROOT, "data/qa", f"{rid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("QA", "PASS" if ok else "FAIL")
    for n, v in rep["items"].items():
        print(f" {n}. {'OK ' if v['ok'] else 'NO '} {v['name']}: {v['note']}")
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"pass={'1' if ok else '0'}\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
