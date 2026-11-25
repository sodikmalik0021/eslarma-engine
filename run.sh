#!/usr/bin/env bash
# Engine entry points. Code is here (public); all content lives in the private repository checked out into ./priv.
#   run.sh setup | beat | produce
# Stage output goes to priv/data/logs (private), the public log shows only step names and results.
set -uo pipefail
cd "$(dirname "$0")"
P=priv
pg() { git -C $P "$@"; }

save() { # save "<message>" paths... : commit to the private repo, survive concurrent pushes
  local m="$1"; shift
  pg add -A "$@" 2>/dev/null
  pg diff --cached --quiet && return 0
  pg commit -qm "$m"
  for k in 1 2 3 4 5; do pg pull -q --rebase && pg push -q origin HEAD:main && return 0; pg rebase --abort 2>/dev/null; sleep $((k * 4)); done
  echo "save failed"; return 1
}
fresh() { pg pull -q --rebase || { pg rebase --abort 2>/dev/null; pg fetch -q origin main && pg reset -q --hard FETCH_HEAD; }; }
count() { python3 -c "import json,sys;q=json.load(open('data/queue.json'));print(sum(i.get('status') in sys.argv[1:] for i in q))" "$@"; }

setup() {
  [ -d $P/data ] || { echo "private data not checked out"; exit 1; }
  ln -sfn $P/data data; ln -sfn $P/growth growth; mkdir -p data/logs out
  pg config user.name "eslarma-bot"; pg config user.email "eslarma-bot@users.noreply.github.com"
  C=$(python3 -c "import json;print(json.load(open('data/state.json')).get('owner_chat_id') or '')"); [ -n "$C" ] && echo "::add-mask::$C"
  return 0
}

beat() { # wake the private publisher (a push by the deploy key starts its workflow)
  fresh; date -u +%FT%TZ > data/tick; save "tick" data
}

produce() { # make ONE reel and put it into the stock
  fresh
  S=$(python3 - <<'EOF'
import json
q = json.load(open("data/queue.json"))
for i in q:  # only one production runs at a time, so anything left "in_progress" by the engine is an orphan of a crashed run
    if i.get("engine") and i.get("status") == "in_progress":
        i["orphans"] = i.get("orphans", 0) + 1
        i["status"] = "downloaded" if i["orphans"] < 3 else "needs_owner"
it = next((i for i in q if i.get("status") == "downloaded" and i.get("video_asset")), None)
if it:
    it["status"] = "in_progress"; it["engine"] = True
    json.dump(q, open("data/queue.json", "w"), ensure_ascii=False, indent=1); print(it["video_asset"])
EOF
)
  [ -z "$S" ] && { echo "no source videos"; return 0; }
  ID=${S#src_}; ID=${ID%.mp4}; LOG=data/logs/$ID.log; : > $LOG
  save "engine: $S in_progress" data || true
  fail() { echo "stage failed: $1"; tail -c 60000 $LOG > /tmp/l && cp /tmp/l $LOG; pg checkout -q -- data/queue.json 2>/dev/null; fresh; python3 tools/route.py fail "$S" "$1" >> /dev/null 2>&1; save "engine: return $S" data; return 1; }
  pg fetch -q --depth 1 origin refs/heads/videos && pg show "FETCH_HEAD:$S" > /tmp/$S && [ -s /tmp/$S ] || { fail "исходное видео"; return 1; }
  for st in "plan:план:60m" "render:рендер:285m" "check:проверка звука:15m" "qa:чек-лист качества:40m"; do
    IFS=: read -r a name lim <<< "$st"; echo "== $a $(date +%H:%M)"
    if [ $a = qa ]; then C="python3 tools/qa.py $S /tmp/$S"; else C="python3 tools/auto_reel.py $a $S /tmp/$S"; fi
    timeout $lim $C >> $LOG 2>&1 || { fail "$name"; return 1; }
  done
  rm -rf /tmp/media; pg worktree prune
  pg fetch -q --depth 1 origin refs/heads/media && pg worktree add -q --detach /tmp/media FETCH_HEAD || { fail "сохранение видео"; return 1; }
  mkdir -p /tmp/media/out; cp out/eslarma_$ID.mp4 /tmp/media/out/; cp out/qa_$ID.jpg /tmp/media/out/ 2>/dev/null
  (cd /tmp/media && git add -A out && git commit -qm "media: eslarma_$ID (engine)" && git push -q origin HEAD:refs/heads/media) || { fail "сохранение видео"; return 1; }
  save "engine: plan + QA $ID" data || true
  fresh
  python3 tools/route.py ok "$S" out/eslarma_$ID.mp4 1 >> $LOG 2>&1
  save "engine: route $S" data
  echo "finished; ready: $(count ready)"
}

cycle() { # beat.yml: keep the stock full, wake the publisher
N=$(python3 -c "import json;q=json.load(open('data/queue.json'));c=lambda s:sum(i.get('status')==s for i in q);print(int(c('ready')+c('approved')+c('awaiting_approval')<6 and c('downloaded')>0))")
if [ "$N" = 1 ] && [ -z "$(gh run list -w produce.yml -L 6 --json status -q '.[]|select(.status!="completed").status')" ]; then gh workflow run produce.yml; fi

W=$(python3 - <<'EOF'
import json, sys
sys.path.insert(0, "tools"); import slots
from datetime import datetime
st, q = json.load(open("data/state.json")), json.load(open("data/queue.json"))
now, w = datetime.now(slots.TZ), -1
for x in st.get("slots") or slots.DEFAULT:
    h, m = map(int, x.split(":")); d = (now.replace(hour=h, minute=m, second=20, microsecond=0) - now).total_seconds()
    if 0 < d <= 100 * 60: w = int(d)
if w < 0 and slots.due_slot(q, st) and any(i.get("status") == "ready" for i in q): w = 0   # a missed slot
if w < 0:  # otherwise look at Telegram about once an hour
    try: last = datetime.fromisoformat(open("data/tick").read().strip().replace("Z", "+00:00"))
    except Exception: last = None
    if not last or (now - last).total_seconds() > 3300: w = 0
print(w)
EOF
)
if [ "$W" -ge 0 ]; then sleep "$W"; bash run.sh beat; fi

}

need() {
python3 -c "import json;q=json.load(open('data/queue.json'));c=lambda s:sum(i.get('status')==s for i in q);print(int(c('ready')+c('approved')+c('awaiting_approval')<6 and c('downloaded')>0))"
}

machine() { # packages and models
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL /usr/local/share/boost || true
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg librsvg2-bin fonts-inter > /dev/null
pip install --quiet "opencv-python-headless<5" numpy pillow faster-whisper

curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
sudo systemctl stop ollama 2>/dev/null || true
nohup env OLLAMA_MODELS=$HOME/.ollama/models ollama serve > /tmp/ollama.log 2>&1 &
for i in $(seq 1 30); do curl -s 127.0.0.1:11434 > /dev/null && break; sleep 2; done
for k in 1 2 3; do ollama pull $LOCAL_MODEL > /dev/null 2>&1 && break; sleep 20; done

}

make() { # produce.yml: whole job
  setup || return 1
  [ "$(need)" = 1 ] || { echo "stock is full"; return 0; }
  machine; produce; rm -f /tmp/took; [ -n "$S" ] && touch /tmp/took; return 0
}

next() { # tell the publisher, then queue the following reel here: the beat would still see this run as active
  setup; beat
  if [ -f /tmp/took ] && [ "$(need)" = 1 ]; then gh workflow run produce.yml || true; fi
}

"$@"
