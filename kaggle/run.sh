#!/usr/bin/env bash
# kaggle/run.sh SCRIPT [extra files...]: push SCRIPT as a private GPU kernel, wait, download its output to /tmp/kout
set -u
U=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.json')))['username'])")
SLUG=eslarma-$(basename "$1" .py | tr '_' '-')
D=/tmp/kpush; rm -rf $D /tmp/kout; mkdir -p $D /tmp/kout
cp "kaggle/$1" $D/main.py
for f in "${@:2}"; do cp "$f" $D/; done
cat > $D/kernel-metadata.json <<J
{"id":"$U/$SLUG","title":"$SLUG","code_file":"main.py","language":"python","kernel_type":"script","is_private":true,"enable_gpu":true,"enable_internet":true,"dataset_sources":[],"competition_sources":[],"kernel_sources":[]}
J
kaggle kernels push -p $D || exit 1
for i in $(seq 1 200); do
  sleep 30; S=$(kaggle kernels status "$U/$SLUG" 2>&1 | tail -1); echo "$(date +%H:%M) $S"
  case "$S" in *complete*|*COMPLETE*) break;; *error*|*ERROR*|*cancel*|*CANCEL*) kaggle kernels output "$U/$SLUG" -p /tmp/kout >/dev/null 2>&1; tail -c 4000 /tmp/kout/*.log 2>/dev/null; exit 1;; esac
done
kaggle kernels output "$U/$SLUG" -p /tmp/kout
ls -la /tmp/kout; tail -c 3000 /tmp/kout/*.log 2>/dev/null || true
