"""Best Uzbek transcript: Kotib/uzbek_stt_v1 checked word by word against islomov/rubaistt_v2_medium.

build(src, video) -> data/transcripts/<src>.best.json  (short segments with word times + "alt" = second model's words, "agree" 0..1)
Generic whisper large-v3 heard nonsense on this speaker (src_0024: avg word p 0.59 vs 0.97), so it is not used for text.
"""
import difflib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def norm(w): return re.sub(r"[^a-z']", "", w.lower().replace("ʻ", "'").replace("’", "'").replace("‘", "'"))


def load(src, video, suffix):
    p = os.path.join(ROOT, "data/transcripts", src + suffix + ".json")
    if not os.path.exists(p):
        import transcribe
        json.dump(transcribe.transcribe(video, transcribe.uz_model(suffix)), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return json.load(open(p, encoding="utf-8"))


def glue(t):
    """whisper splits o'/g' words at the apostrophe ("ko" + "'r"): join them; drop empty tokens"""
    out = []
    for s in t["segments"]:
        for w in s["words"]:
            x = w["w"].strip().replace("ʻ", "'").replace("ʼ", "'").replace("’", "'").replace("‘", "'")
            if not x:
                continue
            if out and (x.startswith("'") or out[-1]["w"].endswith("'")) and w["s"] - out[-1]["e"] < 0.35:
                out[-1] = dict(out[-1], w=out[-1]["w"] + x, e=w["e"], p=min(out[-1]["p"], w["p"]))
            else:
                out.append(dict(w, w=x))
    return [w for w in out if norm(w["w"])]


def merge(a, b):
    """a, b = transcripts; returns segments of a (max ~7 s, cut at sentence ends / pauses), compared with b"""
    wa, wb = glue(a), glue(b)
    segs, cur = [], []
    for k, w in enumerate(wa):
        cur.append(w)
        nxt = wa[k + 1] if k + 1 < len(wa) else None
        d = w["e"] - cur[0]["s"]
        if nxt is None or (w["w"][-1] in ".?!" and d >= 1.2) or nxt["s"] - w["e"] > 0.9 or (d > 5 and w["w"][-1] in ",;:") or d > 7:
            segs.append(cur); cur = []
    out = []
    for c in segs:
        s, e = c[0]["s"], c[-1]["e"]
        alt = [w for w in wb if s - 0.3 <= (w["s"] + w["e"]) / 2 <= e + 0.3]
        agree = difflib.SequenceMatcher(None, " ".join(norm(w["w"]) for w in c), " ".join(norm(w["w"]) for w in alt)).ratio() if alt else 0.0
        out.append({"start": s, "end": e, "text": " ".join(w["w"] for w in c), "alt": " ".join(w["w"] for w in alt),
                    "agree": round(agree, 2), "p": round(sum(w["p"] for w in c) / len(c), 2), "words": c})
    while len(out) > 1 and len(out[-1]["words"]) <= 4 and out[-1]["agree"] < 0.6:  # invented words over the outro / silence
        print("dropped unsupported ending:", out.pop()["text"])
    return out


def build(src, video):
    a, b = load(src, video, ".kotib"), load(src, video, ".rubai")
    segs = merge(a, b)
    out = {"language": "uz", "model": "kotib+rubai", "duration": a.get("audio_seconds"), "segments": segs,
           "agreement": round(sum(s["agree"] * len(s["words"]) for s in segs) / max(1, sum(len(s["words"]) for s in segs)), 2)}
    json.dump(out, open(os.path.join(ROOT, "data/transcripts", src + ".best.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("stt best:", len(segs), "segments, two-model agreement", out["agreement"])
    for s in segs:
        print(f"  {s['start']:6.2f}-{s['end']:6.2f} agree {s['agree']:.2f} | {s['text']}" + ("" if s["agree"] > .9 else f"   <> {s['alt']}"))
    return out


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/tmp/" + sys.argv[1])
