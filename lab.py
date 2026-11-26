"""style samples for the owner's site: one scene in every style"""
import json, os, sys
sys.path.insert(0, "tools")
import open_art
os.makedirs("/tmp/lab", exist_ok=True)
scene = "Uzbek man in white skullcap and dark blue coat seen from behind walking up the path to a mosque with a blue dome and minaret, apricot trees"
items = [{"name": s, "prompt": scene, "palette": "golden", "style": s, "seed": 21} for s in open_art.STYLES]
open_art.generate(items, "/tmp/lab", budget=1500)
print(sorted(os.listdir("/tmp/lab")))
