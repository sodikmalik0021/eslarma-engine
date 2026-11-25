"""Telegram helpers for the owner chat (uses TELEGRAM_BOT_TOKEN + data/state.json owner_chat_id).

  python3 tools/tg.py text  "<message>"
  python3 tools/tg.py photo <jpg> "<caption>"
  python3 tools/tg.py approve <mp4> <id> "<caption>"     # video + buttons Опубликовать / Отклонить
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def owner():
    try:
        return json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("owner_chat_id")
    except Exception:
        return None


def _curl(method, fields, files=None):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = owner()
    if not tok or not chat:
        print("telegram: no token or owner"); return {}
    cmd = ["curl", "-s", "--max-time", "300", f"https://api.telegram.org/bot{tok}/{method}", "--form-string", f"chat_id={chat}"]
    for k, v in fields.items():
        cmd += ["--form-string", f"{k}={v}"]
    for k, p in (files or {}).items():
        cmd += ["-F", f"{k}=@{p}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        d = {"ok": False, "raw": r.stdout[:300]}
    if not d.get("ok"):
        print("telegram error", str(d)[:300])
    return d


def outbox(msg, **kw):
    p = os.path.join(ROOT, "data/outbox.json")
    try:
        o = json.load(open(p, encoding="utf-8"))
    except Exception:
        o = []
    o.append(dict({"text": msg[:3900]}, **kw))
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True}


def text(msg):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return outbox(msg)
    return _curl("sendMessage", {"text": msg[:4000], "disable_web_page_preview": "true"})


def photo(path, caption=""):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return {"ok": True}  # the text message follows
    return _curl("sendPhoto", {"caption": caption[:1000]}, {"photo": path})


def approve(mp4, rid, caption):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return outbox(caption, approve=rid)
    kb = {"inline_keyboard": [[{"text": "✅ Опубликовать", "callback_data": f"pub:{rid}"},
                               {"text": "❌ Отклонить", "callback_data": f"rej:{rid}"}]]}
    d = _curl("sendVideo", {"caption": caption[:1000], "reply_markup": json.dumps(kb), "supports_streaming": "true"}, {"video": mp4})
    if not d.get("ok"):  # video too big for the bot API -> send buttons with a text message
        d = _curl("sendMessage", {"text": caption[:3500] + "\n\n(видео не отправилось, оно в ветке media)", "reply_markup": json.dumps(kb)})
    return d


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "text":
        text(sys.argv[2])
    elif c == "photo":
        photo(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif c == "approve":
        approve(sys.argv[2], sys.argv[3], sys.argv[4])
