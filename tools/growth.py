"""Self-learning loop, every 2-3 days (deploy/growth.yml): our reel stats + competitor hashtags -> lessons for the planner.

  python3 tools/growth.py
Writes growth/stats.json, growth/competitors.json, growth/learned.json (prompt_notes read by auto_reel.py plan),
appends growth/journal.md and rows to growth/hooks.csv / topics.csv. Env: COMPOSIO_API_KEY, COMPOSIO_ACCOUNT, GEMINI_API_KEY.
Hashtag search (Graph API ig_hashtag_search -> top_media) only works for accounts connected through Facebook Login;
on Instagram Login it fails and the reason is recorded. Max 30 unique hashtags per 7 days (Instagram limit).
"""
import csv, json, os, re, statistics, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import composio_publish as cp

G = lambda p: os.path.join(ROOT, "growth", p)
TAGS = ["abdullohdomla", "eslatma", "islomiynasihat", "nasihat", "islom", "iymon", "duo", "sabr"]
NOW = datetime.now(timezone.utc)


def jload(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def ins(m):
    out = {}
    for x in (m.get("insights") or {}).get("data", []):
        out[x["name"]] = (x.get("values") or [{}])[0].get("value")
    return out


def our_stats(acc):
    rows, after = [], None
    for _ in range(4):
        args = {"ig_user_id": "me", "limit": 50, "fields": "id,caption,permalink,timestamp,media_product_type,like_count,comments_count,"
                "insights.metric(views,reach,saved,shares,total_interactions,ig_reels_avg_watch_time)"}
        if after:
            args["after"] = after
        d = cp.tool("INSTAGRAM_GET_IG_USER_MEDIA", args, acc)
        d = d.get("data", d) if isinstance(d, dict) else {}
        rows += d.get("data", []) if isinstance(d.get("data"), list) else []
        after = ((d.get("paging") or {}).get("cursors") or {}).get("after") if (d.get("paging") or {}).get("next") else None
        if not after:
            break
    stats = {}
    for m in rows:
        if m.get("media_product_type") != "REELS":
            continue
        i = ins(m)
        cap = m.get("caption") or ""
        stats[m["id"]] = {"permalink": m.get("permalink"), "timestamp": m.get("timestamp"), "hook": cap.split("\n")[0][:120],
                          "tags": re.findall(r"#(\w+)", cap), "views": i.get("views"), "reach": i.get("reach"), "saved": i.get("saved"),
                          "shares": i.get("shares"), "likes": m.get("like_count"), "comments": m.get("comments_count"),
                          "avg_watch": round((i.get("ig_reels_avg_watch_time") or 0) / 1000, 1)}
    return stats


def competitors(acc, ig_id):
    log = jload(G("hashtag_log.json"), [])
    week = {x["tag"] for x in log if datetime.fromisoformat(x["at"]) > NOW - timedelta(days=7)}
    top, errors = [], []
    for tag in TAGS:
        if tag not in week and len(week) >= 28:
            break
        try:
            h = cp.http("POST", f"{cp.BASE}/tools/execute/proxy", {"connected_account_id": acc, "method": "GET",
                        "endpoint": f"/ig_hashtag_search?user_id={ig_id}&q={tag}"})
            hid = ((h.get("data") or {}).get("data") or [{}])[0].get("id")
            if not hid:
                raise RuntimeError(str(h)[:200])
            week.add(tag); log.append({"tag": tag, "at": NOW.isoformat()})
            t = cp.http("POST", f"{cp.BASE}/tools/execute/proxy", {"connected_account_id": acc, "method": "GET",
                        "endpoint": f"/{hid}/top_media?user_id={ig_id}&fields=id,caption,permalink,like_count,comments_count,media_type,media_product_type&limit=50"})
            for m in (t.get("data") or {}).get("data", []):
                if m.get("media_type") == "VIDEO":
                    cap = m.get("caption") or ""
                    top.append({"hashtag": tag, "url": m.get("permalink"), "hook": cap.split("\n")[0][:120], "caption": cap[:400],
                                "likes": m.get("like_count"), "comments": m.get("comments_count")})
        except Exception as e:
            errors.append(f"#{tag}: {str(e)[:160]}")
            if len(errors) >= 2 and not top:
                break  # the API is not available for this connection; don't burn calls
    json.dump(log[-200:], open(G("hashtag_log.json"), "w", encoding="utf-8"), indent=1)
    top.sort(key=lambda x: (x.get("likes") or 0) + 3 * (x.get("comments") or 0), reverse=True)
    seen, uniq = set(), []
    for x in top:
        if x["url"] not in seen:
            seen.add(x["url"]); uniq.append(x)
    return {"updated": NOW.isoformat(timespec="minutes"), "top": uniq[:40], "errors": errors,
            "note": "" if uniq else "Поиск по хештегам недоступен: Instagram подключён через Instagram Login, а hashtag search в Graph API есть только при Facebook Login (страница Facebook + бизнес-аккаунт)."}


def lessons(stats, comp):
    reels = [s for s in stats.values() if s.get("views") is not None]
    notes = []
    if reels:
        by = sorted(reels, key=lambda s: (s["shares"] or 0) * 20 + (s["saved"] or 0) * 10 + (s["views"] or 0), reverse=True)
        med = statistics.median([s["views"] or 0 for s in reels])
        best = by[:3]
        notes.append("Best hooks so far (copy their shape, not words): " + " | ".join(f"\"{s['hook']}\" ({s['views']} views, {s['shares']} shares)" for s in best))
        q = [s for s in reels if s["hook"].strip().endswith("?")]
        st = [s for s in reels if not s["hook"].strip().endswith("?")]
        if len(q) >= 3 and len(st) >= 3:
            mq, ms = statistics.median([s["views"] or 0 for s in q]), statistics.median([s["views"] or 0 for s in st])
            notes.append(f"Question hooks median {mq:.0f} views vs statements {ms:.0f}: prefer {'questions' if mq >= ms else 'statements'}.")
        notes.append(f"Median views {med:.0f}; avg watch {statistics.median([s['avg_watch'] or 0 for s in reels]):.1f}s — open with the strongest sentence and motion in the first second.")
        notes.append("Shares win reach: end the caption with a concrete 'send this to the friend who ...' line about everyday life.")
    if comp.get("top"):
        notes.append("Competitor top reels hooks: " + " | ".join(f"\"{x['hook'][:60]}\"" for x in comp["top"][:5]))
    key = os.environ.get("GEMINI_API_KEY")
    if key and reels:
        try:
            from auto_reel import gemini
            prompt = ("You analyse an Uzbek Islamic reels account. Given our reels stats and competitor top posts, return ONLY JSON "
                      "{\"prompt_notes\": [max 6 short concrete English rules for the next reels: hook style, topics, first 3 seconds, caption share line]}.\n"
                      f"OUR REELS: {json.dumps(reels[:30], ensure_ascii=False)[:9000]}\nCOMPETITORS: {json.dumps(comp.get('top', [])[:20], ensure_ascii=False)[:5000]}")
            r, _ = gemini(prompt, tries=1)
            if isinstance(r.get("prompt_notes"), list) and r["prompt_notes"]:
                notes = [str(x) for x in r["prompt_notes"][:6]] + notes[:2]
        except BaseException as e:
            print("gemini lessons skipped:", str(e)[:150])
    return notes


def main():
    acc = cp.account()
    stats = our_stats(acc)
    json.dump(stats, open(G("stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    comp = competitors(acc, cp.IG)
    json.dump(comp, open(G("competitors.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    notes = lessons(stats, comp)
    json.dump({"updated": NOW.isoformat(timespec="minutes"), "prompt_notes": notes}, open(G("learned.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    q = jload(os.path.join(ROOT, "data/queue.json"), [])  # attach media ids to queue items by permalink
    by_link = {s["permalink"]: k for k, s in stats.items()}
    for i in q:
        if i.get("permalink") in by_link and not i.get("ig_media_id"):
            i["ig_media_id"] = by_link[i["permalink"]]
    json.dump(q, open(os.path.join(ROOT, "data/queue.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    known = {r.get("reel_uuid") for r in csv.DictReader(open(G("hooks.csv"), encoding="utf-8"))}
    with open(G("hooks.csv"), "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for k, s in stats.items():
            if k not in known and s["timestamp"] and datetime.strptime(s["timestamp"], "%Y-%m-%dT%H:%M:%S%z") < NOW - timedelta(hours=24):
                w.writerow([s["timestamp"][:10], k, s["hook"], "question" if s["hook"].strip().endswith("?") else "statement",
                            next((t for t in s["tags"] if t not in ("islom", "eslatma", "abdullohdomla", "eslarma")), ""),
                            s["views"], s["reach"], "", s["avg_watch"], s["saved"], s["shares"], "auto growth.py (lifetime, age >24h)"])
    reels = [s for s in stats.values() if s.get("views") is not None]
    groups = {}  # topics.csv: one row per topic hashtag, medians over our reels
    for s in reels:
        t = next((t for t in s["tags"] if t not in ("islom", "eslatma", "abdullohdomla", "eslarma")), "other")
        groups.setdefault(t, []).append(s)
    with open(G("topics.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["topic", "reels", "median_views_24h", "median_skip_3s", "median_saves", "median_shares", "last_update"])
        for t, ss in sorted(groups.items(), key=lambda x: -statistics.median([s["views"] or 0 for s in x[1]])):
            w.writerow([t, len(ss), statistics.median([s["views"] or 0 for s in ss]), "", statistics.median([s["saved"] or 0 for s in ss]),
                        statistics.median([s["shares"] or 0 for s in ss]), f"{NOW:%Y-%m-%d}"])
    with open(G("journal.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## {NOW:%Y-%m-%d} (growth.py, auto)\n- Our reels: {len(reels)}; median views "
                f"{statistics.median([s['views'] or 0 for s in reels]) if reels else 0:.0f}; total shares {sum(s['shares'] or 0 for s in reels)}.\n"
                f"- Competitors: {len(comp['top'])} reels from hashtags. {comp.get('note', '')}\n"
                + "".join(f"- Lesson: {n}\n" for n in notes))
    print("growth ok:", len(stats), "reels,", len(comp["top"]), "competitor reels; errors:", comp["errors"][:2])


if __name__ == "__main__":
    main()
