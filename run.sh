#!/usr/bin/env bash
# Engine entry points. Code is here (public); all content lives in the private repository checked out into ./priv.
#   run.sh setup | tick | produce
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

tick() { # one beat of the clock: Telegram, downloads, publishing at slots
  fresh
  python3 bot.py >> data/logs/bot.log 2>&1 || echo "bot tick failed"
  if grep -qE '"status": "(new|retry)"' data/queue.json; then
    pip install --quiet --upgrade yt-dlp && python3 download.py >> data/logs/bot.log 2>&1 || echo "download failed"
    for f in videos/*.mp4; do [ -e "$f" ] && store_video "$f"; done
  fi
  tail -n 400 data/logs/bot.log > /tmp/bl && cp /tmp/bl data/logs/bot.log
  save "queue update" data
  for S in $(python3 -c "import json;print(' '.join(i['video_asset'] for i in json.load(open('data/queue.json')) if i.get('status')=='approved'))"); do
    ID=${S#src_}; ID=${ID%.mp4}
    pg fetch -q --depth 1 origin refs/heads/media && pg show "FETCH_HEAD:out/eslarma_$ID.mp4" > /tmp/$ID.mp4 || { echo "no video for an approved item"; continue; }
    if APPROVED=1 python3 tools/publish_item.py "$S" /tmp/$ID.mp4 >> data/logs/publish.log 2>&1; then echo "published one reel"; else
      echo "publish failed"
      python3 - "$S" <<'EOF'
import json, sys
sys.path.insert(0, "tools"); import tg
q = json.load(open("data/queue.json"))
for i in q:
    if i.get("video_asset") == sys.argv[1] and i.get("status") == "approved":
        i["publish_tries"] = i.get("publish_tries", 0) + 1
        if i["publish_tries"] >= 4:
            i["status"] = "needs_owner"
            tg.text(f"⚠️ Ролик {sys.argv[1]} не публикуется (4 попытки). Отложил, беру следующий.")
json.dump(q, open("data/queue.json", "w"), ensure_ascii=False, indent=1)
EOF
    fi
    save "publish" data
  done
}

store_video() { # private branch "videos"
  local f="$1"; rm -rf /tmp/vid; pg worktree prune
  pg fetch -q --depth 1 origin refs/heads/videos && pg worktree add -q --detach /tmp/vid FETCH_HEAD && cp "$f" /tmp/vid/ &&
    (cd /tmp/vid && git add -A && git commit -qm "source video" && git push -q origin HEAD:refs/heads/videos) && rm -f "$f" || echo "video not stored"
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
  for st in "plan:план:60m" "render:рендер:150m" "check:проверка звука:15m" "qa:чек-лист качества:40m"; do
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
