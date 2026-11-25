"""eslarma.uz bot, stage 1: receive Instagram links / videos from the owner and queue them."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}/"
STATE_PATH = "data/state.json"
QUEUE_PATH = "data/queue.json"
LINK_RE = re.compile(r"https?://(?:www\.)?instagram\.com/[^\s]+", re.I)


def call(method, **params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(API + method, data=data, timeout=30) as resp:
        result = json.load(resp)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {result.get('description')}")
    return result["result"]


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def reply(chat_id, text):
    call("sendMessage", chat_id=chat_id, text=text)


MODES = {"auto": "🤖 Режим auto: ролик, прошедший проверку, публикуется сам (09:00, 15:00, 21:00).",
         "approve": "👀 Режим approve: каждый ролик сначала приходит вам с кнопками «Опубликовать» / «Отклонить»."}


def handle_command(chat_id, text, state, queue):
    """Owner commands: /auto, /approve, /mode, /status. Deep links from the web panel arrive as '/start mode_auto'."""
    t = text.lower().split("@")[0]
    if t in ("/start mode_auto", "/auto"):
        state["mode"] = "auto"
    elif t in ("/start mode_approve", "/approve"):
        state["mode"] = "approve"
    elif t == "/mode":
        pass
    elif t == "/status":
        cnt = {}
        for i in queue:
            cnt[i.get("status")] = cnt.get(i.get("status"), 0) + 1
        reply(chat_id, "Очередь: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) +
              f"\n{MODES.get(state.get('mode') or 'auto')}")
        return True
    else:
        return False
    reply(chat_id, MODES[state.get("mode") or "auto"] + "\nСменить: /auto или /approve")
    return True


def handle_button(cb, state, queue):
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    if chat_id != state.get("owner_chat_id"):
        return
    action, _, rid = (cb.get("data") or "").partition(":")
    it = next((i for i in queue if i.get("video_asset") == f"src_{rid}.mp4"), None)
    note = "Ролик не найден."
    if it and it.get("status") == "published":
        note = "Этот ролик уже опубликован."
    elif it and action == "pub":
        it["status"] = "approved"
        note = f"✅ Принято. Ролик {rid} будет опубликован в течение ~30 минут."
    elif it and action == "rej":
        it["status"] = "rejected"
        note = f"❌ Ролик {rid} отклонён и не будет опубликован."
    try:
        call("answerCallbackQuery", callback_query_id=cb["id"], text=note[:190])
    except Exception:
        pass
    reply(chat_id, note)


def main():
    state = load(STATE_PATH, {"offset": 0, "owner_chat_id": None})
    queue = load(QUEUE_PATH, [])
    known = {item.get("url") for item in queue} | {item.get("file_id") for item in queue}

    updates = call("getUpdates", offset=state["offset"], timeout=0)
    for upd in updates:
        state["offset"] = upd["update_id"] + 1
        cb = upd.get("callback_query")
        if cb:
            handle_button(cb, state, queue)
            continue
        msg = upd.get("message")
        if not msg:
            continue
        chat_id = msg["chat"]["id"]

        # The first private chat that writes to the bot becomes its owner.
        if state["owner_chat_id"] is None and msg["chat"].get("type") == "private":
            state["owner_chat_id"] = chat_id
        if chat_id != state["owner_chat_id"]:
            reply(chat_id, "Это личный бот.")
            continue

        text = msg.get("text") or msg.get("caption") or ""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        added = 0
        if handle_command(chat_id, text.strip(), state, queue):
            continue

        for url in LINK_RE.findall(text):
            path = urllib.parse.urlsplit(url).path.rstrip("/")
            url = "https://www.instagram.com" + path + "/"
            if url in known:
                reply(chat_id, f"Эта ссылка уже в очереди:\n{url}")
                continue
            queue.append({"type": "link", "url": url, "status": "new", "received_at": now})
            known.add(url)
            added += 1

        video = msg.get("video")
        doc = msg.get("document")
        if not video and doc and str(doc.get("mime_type", "")).startswith("video/"):
            video = doc
        if video and video["file_id"] not in known:
            queue.append({"type": "file", "file_id": video["file_id"],
                          "size": video.get("file_size"), "status": "new", "received_at": now})
            known.add(video["file_id"])
            added += 1

        waiting = sum(1 for item in queue if item["status"] == "new")
        if added:
            reply(chat_id, f"Принял ✅ В очереди роликов: {waiting}")
        elif not LINK_RE.search(text):
            reply(chat_id, "Ассалому алайкум! Присылайте ссылку на ролик из Инстаграма "
                           "или само видео — я поставлю его в очередь.")

    import sys
    sys.path.insert(0, "tools")
    import slots
    item, msg = slots.assign(queue, state)
    if item:
        print("slot", item["slot"], "->", item["video_asset"])
    ready, raw = slots.stock(queue)
    if raw < 5 and state.get("low_stock_told") != str(datetime.now(timezone.utc).date()):
        state["low_stock_told"] = str(datetime.now(timezone.utc).date())
        msg = ((msg + "\n") if msg else "") + f"📥 Осталось мало исходных видео: {raw} (готовых роликов: {ready}). Пришлите ссылки на новые ролики домлы."
    if msg and state.get("owner_chat_id"):
        try:
            reply(state["owner_chat_id"], msg)
        except Exception as e:
            print("notice failed:", e)
    # outbox: messages for the owner queued by other scripts/sessions (data/outbox.json: [{"text", "send_after"}])
    outbox, left = load("data/outbox.json", []), []
    for m in outbox:
        due = m.get("send_after") or now_iso()
        if due <= now_iso() and state.get("owner_chat_id"):
            try:
                reply(state["owner_chat_id"], m["text"][:4000])
                continue
            except Exception as e:
                print("outbox send failed:", e)
        left.append(m)
    if outbox:
        save("data/outbox.json", left)

    save(STATE_PATH, state)
    save(QUEUE_PATH, queue)
    print(f"processed {len(updates)} updates, queue size {len(queue)}")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
