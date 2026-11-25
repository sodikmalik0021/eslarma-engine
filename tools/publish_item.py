"""Publish one rendered reel to Instagram (Composio) and mark it in the queue. Used by auto.yml and by the approve button.

  python3 tools/publish_item.py <src_name> <mp4>
Safety: refuses an item that is already published, a reel whose QA did not pass (unless APPROVED=1, i.e. the owner
pressed the button), and more than 50 posts in 24 h (Instagram limit). Never deletes anything.
"""
import json, os, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import composio_publish, tg

Q = os.path.join(ROOT, "data/queue.json")


def load():
    return json.load(open(Q, encoding="utf-8"))


def save(q):
    json.dump(q, open(Q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def already(caption):
    """a previous try may have gone out although its answer was lost: never post the same caption twice"""
    d = composio_publish.tool("INSTAGRAM_GET_IG_USER_MEDIA", {"ig_user_id": "me", "limit": 8, "fields": "id,caption,permalink"}, composio_publish.account())
    rows = d.get("data", []) if isinstance(d, dict) else []
    rows = rows.get("data", []) if isinstance(rows, dict) else rows
    for m in rows:
        if caption and (m.get("caption") or "").strip()[:300] == caption.strip()[:300]:
            return {"media_id": m["id"], "permalink": m.get("permalink"), "found": True}
    return None


def main(src, mp4):
    rid = src.split("_")[-1].split(".")[0]
    q = load()
    it = next((i for i in q if i.get("video_asset") == src), None)
    if not it:
        raise SystemExit(f"{src} not in queue")
    if it.get("status") == "published" or it.get("ig_media_id"):
        raise SystemExit(f"{src} already published - refusing to post twice")
    qa = {}
    try:
        qa = json.load(open(os.path.join(ROOT, "data/qa", f"{rid}.json"), encoding="utf-8"))
    except Exception:
        pass
    if not qa.get("pass") and os.environ.get("APPROVED") != "1":
        raise SystemExit(f"{src}: QA not passed and not approved by owner - not publishing")
    now = datetime.now(timezone.utc)
    recent = [i for i in q if i.get("published_at") and datetime.fromisoformat(i["published_at"]) > now - timedelta(hours=24)]
    if len(recent) >= 45:  # Instagram limit 50/24h, keep a margin for stories
        raise SystemExit("daily Instagram limit reached")
    plan0 = json.load(open(os.path.join(ROOT, "data/plans", f"{rid}.json"), encoding="utf-8"))
    res = already(plan0.get("caption", "")) or composio_publish.main(mp4, os.path.join(ROOT, "data/plans", f"{rid}.json"))
    if not res.get("media_id"):
        raise SystemExit(f"publish failed: {res}")
    plan = json.load(open(os.path.join(ROOT, "data/plans", f"{rid}.json"), encoding="utf-8"))
    q = load()  # re-read, the bot may have changed it meanwhile
    for i in q:
        if i.get("video_asset") == src:
            i.update(status="published", ig_media_id=res.get("media_id"), permalink=res.get("permalink"),
                     story_id=res.get("story_id"), published_at=now.isoformat(timespec="seconds"), auto=True,
                     hook=plan.get("hook"), topic=plan.get("topic"), approved=os.environ.get("APPROVED") == "1",
                     output=f"media branch: out/eslarma_{rid}.mp4")
    save(q)
    extra = "" if res.get("story_id") else f"\n(сторис не вышла: {res.get('story_error', '')[:120]})"
    tg.text(f"✅ Ролик опубликован: «{plan.get('hook', '')}»\n{res.get('permalink') or res.get('media_id')}{extra}")
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
