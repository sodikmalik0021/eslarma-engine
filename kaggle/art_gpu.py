# Paintings on a free Kaggle GPU (Tesla T4): full SDXL model, 30 steps, higher resolution, negative prompt.
# Same rules as tools/open_art.py: a picture with a face is redrawn as silhouettes, a picture that misses its phrase is repainted.
import json, os, subprocess, time
subprocess.run("pip install -q -U diffusers transformers accelerate safetensors opencv-python-headless", shell=True)
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
import open_art as A

ITEMS = json.load(open("/kaggle/working/src/" + [n for n in FILES if n.endswith(".json")][0], encoding="utf-8"))
OUT = "/kaggle/working/out"; os.makedirs(OUT, exist_ok=True)
W, H, STEPS, CFG, BUDGET = 832, 1472, 30, 5.0, 40 * 60
NEG = ("photo, photorealistic, 3d render, watercolor bleed, church, christian cross, crucifix, stained glass window, gothic cathedral, chapel, western suburban house, cemetery with crosses, "
       "text, letters, watermark, signature, logo, frame, border, blurry, lowres, jpeg artifacts, deformed hands, extra fingers, "
       "close-up face, portrait, nudity")
t0 = time.time()
p = StableDiffusionXLPipeline.from_pretrained("RunDiffusion/Juggernaut-XL-v9", torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
p.scheduler = DPMSolverMultistepScheduler.from_config(p.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++")
p.vae.enable_tiling()
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

# ---------- motion: every painting becomes a real video clip (LTX-Video 2B on the GPU) ----------
import gc, subprocess as sp
import numpy as np
del p; gc.collect(); torch.cuda.empty_cache()
VB = 150 * 60  # whole kernel budget incl. paintings
try:
    from diffusers import LTXConditionPipeline, LTXVideoTransformer3DModel
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
    REPO = "Lightricks/LTX-Video-0.9.7-distilled"
    tr = LTXVideoTransformer3DModel.from_single_file("https://huggingface.co/Lightricks/LTX-Video/blob/main/ltxv-2b-0.9.8-distilled.safetensors",
                                                     config="Lightricks/LTX-Video", subfolder="transformer", torch_dtype=torch.float16)
    vp = LTXConditionPipeline.from_pretrained(REPO, transformer=tr, torch_dtype=torch.float16)
    vp.enable_model_cpu_offload(); vp.vae.enable_tiling(); vp.set_progress_bar_config(disable=True)
    from PIL import Image
    VW, VH, N, FPS = 512, 896, 97, 24
    print(f"video model ready {time.time()-t0:.0f}s", flush=True)
    for i, it in enumerate(ITEMS):
        jp = os.path.join(OUT, it["name"] + ".jpg")
        if not os.path.exists(jp) or time.time() - t0 > VB - 240:
            continue
        t = time.time()
        im = Image.open(jp).convert("RGB")
        k2 = max(VW / im.width, VH / im.height); im = im.resize((round(im.width * k2), round(im.height * k2)), Image.LANCZOS)
        x, y = (im.width - VW) // 2, (im.height - VH) // 2; im = im.crop((x, y, x + VW, y + VH))
        best = None
        for tryk in range(2):
            fr = vp(conditions=[LTXVideoCondition(image=im, frame_index=0)], prompt=it.get("motion") or it["prompt"],
                    negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, morphing faces, text",
                    width=VW, height=VH, num_frames=N, frame_rate=FPS, num_inference_steps=10, guidance_scale=1.0,
                    decode_timestep=0.05, image_cond_noise_scale=0.025, generator=torch.Generator("cuda").manual_seed(11 + i + 50 * tryk),
                    output_type="np").frames[0]
            fr = [(f * 255).clip(0, 255).astype(np.uint8) for f in fr]
            if not np.isfinite(np.array(fr[0], dtype=float)).all():
                continue
            face = any(A.has_face(Image.fromarray(fr[j])) for j in range(0, N, 12))
            move = float(np.mean([np.abs(fr[j + 8].astype(int) - fr[j]).mean() for j in range(0, N - 8, 8)]))
            print(f"video {it['name']} try {tryk+1} {time.time()-t:.0f}s motion {move:.1f}" + (" FACE" if face else ""), flush=True)
            if not face and 1.0 <= move <= 45:
                best = fr; break
        if best is None:
            continue
        pr = sp.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", os.path.join(OUT, "v_" + it["name"] + ".mp4")], stdin=sp.PIPE)
        for f in best:
            pr.stdin.write(f.tobytes())
        pr.stdin.close(); pr.wait()
except Exception as e:
    import traceback; traceback.print_exc()
print(f"all done in {time.time()-t0:.0f}s, clips: {len([f for f in os.listdir(OUT) if f.endswith('.mp4')])}", flush=True)
