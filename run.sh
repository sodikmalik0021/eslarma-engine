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
  for st in "plan:план:60m" "render:рендер:200m" "check:проверка звука:15m" "qa:чек-лист качества:40m"; do
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

"$@"
