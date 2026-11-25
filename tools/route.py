"""After render + QA: decide what happens to the reel.

  python3 tools/route.py ok   <src> <mp4> <publish 0|1>   -> writes action=publish|none to $GITHUB_OUTPUT
  python3 tools/route.py fail <src> "<step/reason>"         -> item back to queue (max 2 tries), owner informed

mode (data/state.json "mode"): "auto" (default) publishes a reel that passed QA; "approve" sends it to the owner
with buttons first. A reel that failed QA is NEVER published automatically.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import tg

Q = os.path.join(ROOT, "data/queue.json")
MAX_TRIES = 2


def mode():
    try:
        return json.load(open(os.path.join(ROOT, "data/state.json"), encoding="utf-8")).get("mode") or "auto"
    except Exception:
        return "auto"


def set_item(src, **kw):
    q = json.load(open(Q, encoding="utf-8"))
    for i in q:
        if i.get("video_asset") == src and i.get("status") != "published":
            i.update(kw)
    json.dump(q, open(Q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def item(src):
    return next((i for i in json.load(open(Q, encoding="utf-8")) if i.get("video_asset") == src), {})


def out(action):
    print("action:", action)
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"action={action}\n")


def qa_text(rid):
    try:
        qa = json.load(open(os.path.join(ROOT, "data/qa", f"{rid}.json"), encoding="utf-8"))
    except Exception:
        return False, "проверка качества не выполнена"
    lines = [f"{'✅' if v['ok'] else '❌'} {n}. {v['name']}" + ("" if v["ok"] else f" — {v['note'][:140]}") for n, v in qa["items"].items()]
    return qa.get("pass"), "\n".join(lines)


def give_back(src, reason):
    tries = int(item(src).get("auto_tries", 0)) + 1
    st = "downloaded" if tries < MAX_TRIES else "needs_owner"
    set_item(src, status=st, auto_tries=tries, last_error=reason[:300])
    return st, tries


def ok(src, mp4, publish):
    rid = src.split("_")[-1].split(".")[0]
    plan = json.load(open(os.path.join(ROOT, "data/plans", f"{rid}.json"), encoding="utf-8"))
    passed, txt = qa_text(rid)
    sheet = os.path.join(ROOT, "out", f"qa_{rid}.jpg")
    if publish != "1":
        set_item(src, status="downloaded", test_render=True)  # test run: nothing goes out, item stays in the queue
        return out("none")
    m = mode()
    if m == "approve":
        set_item(src, status="awaiting_approval", qa_pass=bool(passed))
        warn = "" if passed else "\n\n⚠️ Проверка нашла проблемы — лучше отклонить."
        tg.approve(mp4, rid, f"Новый ролик ждёт решения: «{plan.get('hook', '')}»\n\n{txt}{warn}")
        return out("none")
    if passed:
        from datetime import datetime, timezone
        set_item(src, status="ready", qa_pass=True, ready_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), hook=plan.get("hook"))
        return out("none")  # tools/slots.py (bot tick) releases it at the next slot
    st, tries = give_back(src, "QA failed")
    if os.path.exists(sheet):
        tg.photo(sheet, f"Ролик {rid} не прошёл проверку — НЕ опубликован.")
    nxt = "Попробую ещё раз в следующий слот." if st == "downloaded" else "Две попытки не прошли — ролик ждёт вас (статус needs_owner)."
    tg.text(f"⚠️ Ролик {rid} «{plan.get('hook', '')}» не опубликован: проверка качества не пройдена.\n\n{txt}\n\n{nxt}")
    out("none")


def fail(src, reason):
    if os.environ.get("TEST") == "1":  # manual test run: just put it back, don't wake the owner
        set_item(src, status="downloaded", last_error=reason[:300])
        return
    st, tries = give_back(src, reason)
    nxt = "Вернул в очередь, попробую в следующий слот." if st == "downloaded" else "Две попытки подряд не удались — ролик отложен (needs_owner)."
    tg.text(f"⚠️ Автопрограмма: ролик {src} не сделан — ошибка на шаге «{reason}». Ничего не опубликовано.\n{nxt}")


if __name__ == "__main__":
    if sys.argv[1] == "ok":
        ok(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        fail(sys.argv[2], sys.argv[3])
