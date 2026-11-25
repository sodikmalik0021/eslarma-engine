"""Publishing clock: reels are made in advance (status "ready") and released at fixed slots; a missed slot is caught up.

assign(queue, state) is called by bot.py on every tick: when a slot is due it marks the oldest ready reel "approved" (bot.yml publishes it).
"""
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=6))  # Bishkek
DEFAULT = ["09:00", "13:00", "17:00", "21:00"]
LATE = timedelta(hours=3, minutes=30)  # how long after a slot it may still be filled
GAP = timedelta(minutes=75)            # never two posts closer than this


def parse(x):
    try:
        d = datetime.fromisoformat(str(x))
        return d if d.tzinfo else d.replace(tzinfo=TZ)
    except Exception:
        return None


def due_slot(queue, state, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(TZ)
    used = {i.get("slot") for i in queue}
    for i in queue:  # posts made outside the clock (manual builds) also occupy the slot they fell on
        p = parse(i.get("published_at"))
        if p and now - p < GAP:
            return None
        sch = parse(i.get("scheduled_for"))
        if sch and i.get("status") != "published" and abs((sch - now).total_seconds()) < GAP.total_seconds():
            return None
    if any(i.get("status") == "approved" for i in queue):
        return None  # one is already on its way
    for hhmm in reversed(state.get("slots") or DEFAULT):
        h, m = map(int, hhmm.split(":"))
        s = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if s <= now <= s + LATE:
            return None if s.isoformat() in used else s.isoformat()
    return None


def assign(queue, state, now=None):
    """returns (item, message) - message is for the owner, or None"""
    if (state.get("mode") or "auto") != "auto":
        return None, None
    slot = due_slot(queue, state, now)
    if not slot:
        return None, None
    ready = sorted((i for i in queue if i.get("status") == "ready"), key=lambda i: i.get("ready_at") or "")
    if ready:
        ready[0].update(status="approved", slot=slot)
        return ready[0], None
    if state.get("empty_slot_told") != slot:
        state["empty_slot_told"] = slot
        return None, f"⚠️ Слот {slot[11:16]}: нет готового ролика, прошедшего проверку. Выпущу, как только появится."
    return None, None


def stock(queue):
    return (sum(i.get("status") == "ready" for i in queue), sum(i.get("status") == "downloaded" for i in queue))
