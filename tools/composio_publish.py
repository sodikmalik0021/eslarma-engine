"""Publish a reel to Instagram through the Composio REST API (Instagram already connected in Composio).

  python3 tools/composio_publish.py <mp4> <plan.json>    -> prints {"media_id":..., "permalink":...}
Env: COMPOSIO_API_KEY, optional COMPOSIO_ACCOUNT (connected account id), IG_USER_ID (default eslarma.uz).
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error

BASE = "https://backend.composio.dev/api/v3"
KEY = os.environ.get("COMPOSIO_API_KEY", "").strip()
IG = os.environ.get("IG_USER_ID", "29915997264724810")


def http(method, url, body=None, headers=None, raw=None):
    h = {"x-api-key": KEY, "Content-Type": "application/json"}
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            t = r.read().decode() or "{}"
            return json.loads(t) if t.strip().startswith(("{", "[")) else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')[:600]}")


def account():
    if os.environ.get("COMPOSIO_ACCOUNT"):
        return os.environ["COMPOSIO_ACCOUNT"]
    d = http("GET", f"{BASE}/connected_accounts?toolkit_slugs=instagram&statuses=ACTIVE")
    items = d.get("items") or d.get("data") or []
    if not items:
        raise SystemExit("no active Instagram connection in Composio")
    return items[0]["id"]


def tool(slug, args, acc):
    d = http("POST", f"{BASE}/tools/execute/{slug}", {"connected_account_id": acc, "user_id": os.environ.get("COMPOSIO_USER", "eslarma"), "arguments": args})
    if not d.get("successful", True) and d.get("error"):
        raise RuntimeError(f"{slug}: {d.get('error')}")
    return d.get("data", d)


def upload(path, slug="INSTAGRAM_POST_IG_USER_MEDIA"):
    b = open(path, "rb").read()
    req = http("POST", f"{BASE}/files/upload/request", {"toolkit_slug": "instagram", "tool_slug": slug,
               "filename": os.path.basename(path), "mimetype": "video/mp4", "md5": hashlib.md5(b).hexdigest()})
    url = req.get("new_presigned_url") or req.get("newPresignedUrl") or req.get("presigned_url")
    key = req.get("key") or req.get("s3key")
    if url:
        r = urllib.request.Request(url, data=b, method="PUT", headers={"Content-Type": "video/mp4"})
        urllib.request.urlopen(r, timeout=600).read()
    return {"name": os.path.basename(path), "mimetype": "video/mp4", "s3key": key}


def main(mp4, plan_path):
    plan = json.load(open(plan_path))
    acc = account()
    vf = upload(mp4)
    c = tool("INSTAGRAM_POST_IG_USER_MEDIA", {"ig_user_id": IG, "media_type": "REELS", "share_to_feed": True,
             "thumb_offset": 800, "caption": plan["caption"], "video_file": vf}, acc)
    cid = c.get("id") or c.get("data", {}).get("id")
    p = tool("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {"ig_user_id": IG, "creation_id": cid, "max_wait_seconds": 240}, acc)
    mid = p.get("id") or p.get("data", {}).get("id")
    out = {"media_id": mid}
    if plan.get("comment"):
        try:
            tool("INSTAGRAM_POST_IG_MEDIA_COMMENTS", {"ig_media_id": mid, "message": plan["comment"][:290]}, acc)
        except Exception as e:
            out["comment_error"] = str(e)[:200]
    try:
        m = tool("INSTAGRAM_GET_IG_MEDIA", {"ig_media_id": mid, "fields": "permalink"}, acc)
        out["permalink"] = m.get("permalink") or m.get("data", {}).get("permalink")
    except Exception:
        pass
    if os.environ.get("POST_STORY", "1") == "1":  # Story with the same video; never fails the reel
        try:
            sf = upload(mp4)
            s = tool("INSTAGRAM_POST_IG_USER_MEDIA", {"ig_user_id": IG, "media_type": "STORIES", "video_file": sf}, acc)
            sid = s.get("id") or s.get("data", {}).get("id")
            sp = tool("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {"ig_user_id": IG, "creation_id": sid, "max_wait_seconds": 240}, acc)
            out["story_id"] = sp.get("id") or sp.get("data", {}).get("id")
        except Exception as e:
            out["story_error"] = str(e)[:200]
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
