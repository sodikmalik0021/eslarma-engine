"""Align corrected Uzbek text to whisper word timestamps."""
import json

def build_words(transcript, fixed):
    """fixed: {segment_index: corrected text or None (skip = no subtitle)}."""
    segs = json.load(open(transcript))["segments"]
    words = []
    for i, seg in enumerate(segs):
        txt = fixed.get(i)
        if not txt: continue
        ww = seg["words"]; toks = [t for t in txt.split() if t not in ("—", "-")]
        if len(ww) == len(toks):
            words += [{"w": t, "s": w["s"], "e": w["e"]} for t, w in zip(toks, ww)]
            continue
        s0, e0 = (ww[0]["s"], ww[-1]["e"]) if ww else (seg["start"], seg["end"])
        tot = sum(len(t) + 2 for t in toks); acc = 0
        for t in toks:
            a = s0 + (e0 - s0) * acc / tot; acc += len(t) + 2
            words.append({"w": t, "s": round(a, 3), "e": round(s0 + (e0 - s0) * acc / tot, 3)})
    return words

def timing_table(plan, notes):
    """markdown: shot start-end -> spoken words in that window -> what is on screen."""
    rows = ["| # | time | words | on screen |", "|---|---|---|---|"]
    for i, s in enumerate(plan["scenes"]):
        ws = " ".join(w["w"] for w in plan["words"] if s["start"] - 0.05 <= w["s"] < s["end"] - 0.05)
        rows.append(f"| {i+1} | {s['start']:.2f}–{s['end']:.2f} | {ws or '(no subtitle)'} | {notes[i]} |")
    return "\n".join(rows)

def build_words2(transcript, fixed):
    """fixed value may also be a list of (text_chunk, n_whisper_words) pairs: each chunk is mapped onto exactly the
    next n whisper words of the segment (precise anchors when the corrected text differs a lot)."""
    segs = json.load(open(transcript))["segments"]
    out = []
    for i, seg in enumerate(segs):
        txt = fixed.get(i)
        if not txt: continue
        if isinstance(txt, str): txt = [(txt, len(seg["words"]))]
        k = 0
        for chunk, n in txt:
            ww = seg["words"][k:k + n]; k += n
            if chunk: out += _map(chunk, ww, seg)
    return out

def _map(txt, ww, seg):
    """Like build_words, but when token counts differ, map each corrected token by its character offset onto the
    whisper words' own time spans (piecewise-linear over whisper word chars), not over the whole segment."""
    words = []
    if True:
        toks = [t for t in txt.split() if t not in ("—", "-")]
        if len(ww) == len(toks):
            return [{"w": t, "s": w["s"], "e": w["e"]} for t, w in zip(toks, ww)]
        if not ww:
            ww = [{"w": seg["text"], "s": seg["start"], "e": seg["end"]}]
        # knots: (char fraction, time) over whisper words
        lens = [len(w["w"].strip()) + 1 for w in ww]; tot = sum(lens); acc = 0; knots = []
        for w, l in zip(ww, lens):
            knots.append((acc / tot, w["s"])); acc += l; knots.append((acc / tot, w["e"]))
        def at(f, late=False):
            segs_ = list(zip(knots, knots[1:]))
            for (f0, t0), (f1, t1) in (reversed(segs_) if late else segs_):
                if f0 <= f <= f1: return t0 if f1 == f0 else t0 + (t1 - t0) * (f - f0) / (f1 - f0)
            return knots[-1][1]
        tl = [len(t) + 1 for t in toks]; tt = sum(tl); acc = 0
        for t, l in zip(toks, tl):
            words.append({"w": t, "s": round(at(acc / tt, True), 3), "e": round(at((acc + l - 1) / tt), 3)}); acc += l
    return words
