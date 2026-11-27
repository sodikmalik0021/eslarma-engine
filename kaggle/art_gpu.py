# Paintings on a free Kaggle GPU (Tesla T4): full SDXL model, 30 steps, higher resolution, negative prompt.
# Same rules as tools/open_art.py: a picture with a face is redrawn as silhouettes, a picture that misses its phrase is repainted.
import json, os, subprocess, time
subprocess.run("pip install -q -U diffusers transformers accelerate safetensors opencv-python-headless", shell=True)
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
import open_art as A

ITEMS = json.load(open("/kaggle/working/src/" + [n for n in FILES if n.endswith(".json")][0], encoding="utf-8"))
OUT = "/kaggle/working/out"; os.makedirs(OUT, exist_ok=True)
W, H, STEPS, CFG, BUDGET = 832, 1472, 30, 5.0, 75 * 60
NEG = ("church, christian cross, crucifix, stained glass window, gothic cathedral, chapel, western suburban house, cemetery with crosses, "
       "text, letters, watermark, signature, logo, frame, border, blurry, lowres, jpeg artifacts, deformed hands, extra fingers, "
       "close-up face, portrait, nudity")
t0 = time.time()
p = StableDiffusionXLPipeline.from_pretrained("RunDiffusion/Juggernaut-XL-v9", torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
p.scheduler = DPMSolverMultistepScheduler.from_config(p.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++")
p.enable_vae_tiling()
print(f"model ready {time.time()-t0:.0f}s", flush=True)
clip, scores, tries, faces = A.Clip(), {}, {}, set()
st = [A.STYLE.format(palette=A.PALETTES.get(it.get("palette"), A.PALETTES["golden"]), style=A.STYLES.get(it.get("style"), A.STYLES["watercolor"])) for it in ITEMS]
plain = [[it["prompt"], A.faceless(it["prompt"])] + list(it.get("alts") or [])[:2] for it in ITEMS]


def paint(i):
    it, k = ITEMS[i], tries.get(i, 0)
    alts = list(range(2, len(plain[i])))
    x = alts[(k - 2) % len(alts)] if k >= 2 and alts else (1 if i in faces else 0)
    text = plain[i][x]; tries[i] = k + 1
    t = time.time()
    im = p(prompt=st[i] + text + ", " + st[i].split(",")[0] + ", masterpiece, highly detailed", negative_prompt=NEG, num_inference_steps=STEPS,
           guidance_scale=CFG, width=W, height=H, generator=torch.Generator("cuda").manual_seed(it.get("seed", 7) + 100 * k)).images[0]
    face, sc = A.has_face(im), clip.score(im, text)
    print(f"ok {it['name']} try {k + 1} {time.time()-t:.0f}s clip {sc:.3f}" + (" FACE - redraw" if face else ""), flush=True)
    if face:
        faces.add(i)
    elif sc > scores.get(it["name"], -1):
        im.save(os.path.join(OUT, it["name"] + ".jpg"), quality=95); scores[it["name"]] = round(sc, 3)


for i in range(len(ITEMS)):
    paint(i)
while time.time() - t0 < BUDGET:
    todo = sorted([i for i in range(len(ITEMS)) if ITEMS[i]["name"] not in scores and tries[i] < 5], key=lambda i: tries[i]) or \
           [i for i in range(len(ITEMS)) if scores.get(ITEMS[i]["name"], 1) < A.CLIP_MIN and tries[i] < 6]
    if not todo:
        break
    paint(todo[0])
json.dump(scores, open(os.path.join(OUT, "_clip.json"), "w"))
json.dump([it["name"] for it in ITEMS if it["name"] not in scores], open(os.path.join(OUT, "_faces.json"), "w"))
print(f"done {len(scores)}/{len(ITEMS)} in {time.time()-t0:.0f}s", flush=True)
