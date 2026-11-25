"""Illustrations with an OPEN model running on the runner itself (SDXL base + SDXL-Lightning, 4 steps, CPU). No external service,
no watermark, no limits.  python3 tools/open_art.py prompts.json outdir     prompts: [{"name", "prompt", "seed", "palette"}]
"""
import json, os, subprocess, sys, time

# CLIP reads only 77 tokens: the style comes first and stays short, the visual must be <= 35 words
# no "storybook" / "paper" / "book" words here: the model then paints pages with gibberish
STYLE = "{palette}, fine watercolor and ink painting, full bleed scene of: "
PALETTES = {"golden": "golden afternoon light, ochre and olive", "rose": "dusty rose sunset light, mauve and peach", "mint": "fresh morning light, sage green and cream",
            "night": "moonlit evening, indigo and warm lantern light", "desert": "warm sand, terracotta and turquoise", "rain": "soft overcast light, blue-grey and amber",
            "spring": "bright spring light, soft green and white", "amber": "deep amber and teal evening light"}


def pipe():
    pip = [sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir"]
    subprocess.run(pip + ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
    subprocess.run(pip + ["diffusers", "transformers<5", "accelerate", "safetensors", "pillow", "huggingface_hub", "opencv-python-headless<5"], check=True)
    import importlib, site
    site.addsitedir(site.getusersitepackages()); importlib.invalidate_caches()  # pip --user dir may be new in this process
    import torch
    # some runners have CPUs without bf16: there bf16 is emulated and one picture takes > 20 min (run 45545929383) -> float32
    flags = open("/proc/cpuinfo").read()
    dt = torch.bfloat16 if ("avx512_bf16" in flags or "amx_bf16" in flags) else torch.float32
    print("cpu dtype", dt, flush=True)
    from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler, AutoencoderKL
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    base = "stabilityai/stable-diffusion-xl-base-1.0"
    unet = UNet2DConditionModel.from_config(UNet2DConditionModel.load_config(base, subfolder="unet")).to(dt)
    unet.load_state_dict(load_file(hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors")))
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=dt)
    p = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, vae=vae, torch_dtype=dt, variant="fp16", use_safetensors=True)
    p.scheduler = EulerDiscreteScheduler.from_config(p.scheduler.config, timestep_spacing="trailing")
    p.vae.enable_tiling()
    p.set_progress_bar_config(disable=True)
    return p


def encode(p, texts):
    """all prompts first, then drop both text encoders: saves ~3 GB while painting"""
    import gc, torch
    with torch.no_grad():
        e = [p.encode_prompt(x, device="cpu", num_images_per_prompt=1, do_classifier_free_guidance=False) for x in texts]
    p.text_encoder = p.text_encoder_2 = None
    gc.collect()
    return [(x[0], x[2]) for x in e]


def has_face(im, thr=0.7):
    """a visible face (OpenCV YuNet, MIT) -> the picture is redrawn (owner rule: no faces)"""
    import cv2, numpy as np
    from huggingface_hub import hf_hub_download
    model = hf_hub_download("opencv/face_detection_yunet", "face_detection_yunet_2023mar.onnx")
    a = cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)
    d = cv2.FaceDetectorYN.create(model, "", (a.shape[1], a.shape[0]), thr, 0.3, 50)
    _, f = d.detect(a)
    return f is not None and any(x[2] >= 26 for x in f)


class Clip:
    def __init__(self):
        from transformers import CLIPModel, CLIPProcessor
        n = "openai/clip-vit-base-patch32"
        self.m, self.p = CLIPModel.from_pretrained(n, use_safetensors=True), CLIPProcessor.from_pretrained(n)

    def score(self, im, text):
        import torch
        x = self.p(text=[text], images=im, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            r = self.m(**x)
        return float((r.image_embeds * r.text_embeds).sum())


CLIP_MIN = 0.25  # below: the picture does not show its description -> repaint with another seed


def faceless(prompt):
    """the same scene with small dark silhouettes instead of people: used when the first painting showed a face"""
    import art_prompts as A
    t = prompt
    for a, b in ((A.M, "distant dark silhouette of a man in skullcap"), (A.W, "distant dark silhouette of a woman in long hijab"),
                 (A.K, "small distant dark silhouette of a boy")):
        t = t.replace(a, b)
    return t + ", tiny distant backlit silhouettes, figures facing away, wide view"


def generate(items, out, w=704, h=1216, budget=125 * 60):
    """first pass: every phrase once; then the time left goes to repaints (faces first, then pictures that miss their description)"""
    os.makedirs(out, exist_ok=True)
    t = time.time(); p = pipe(); print(f"model ready in {time.time()-t:.0f}s", flush=True)
    import torch
    t0, per = time.time(), 0
    clip, scores, tries, faces = Clip(), {}, {}, set()
    st = [STYLE.format(palette=PALETTES.get(it.get("palette"), PALETTES["golden"])) for it in items]
    n = len(items)
    emb = encode(p, [s + it["prompt"] for s, it in zip(st, items)] + [s + faceless(it["prompt"]) for s, it in zip(st, items)])

    def paint(i):
        nonlocal per
        it, k = items[i], tries.get(i, 0)
        tries[i] = k + 1
        t = time.time()
        pe, ppe = emb[i + n] if i in faces else emb[i]
        im = p(prompt_embeds=pe, pooled_prompt_embeds=ppe, num_inference_steps=4, guidance_scale=0, width=w, height=h,
               generator=torch.Generator().manual_seed(it.get("seed", 7) + 100 * k)).images[0]
        im = im.crop((int(w * .04), int(h * .03), int(w * .96), int(h * .97)))  # painted white borders
        per = time.time() - t
        face, sc = has_face(im), clip.score(im, it["prompt"])
        print(f"ok {it['name']} try {k + 1} {per:.0f}s clip {sc:.3f}" + (" FACE - redraw" if face else ""), flush=True)
        if face:
            faces.add(i)
        elif sc > scores.get(it["name"], -1):
            im.save(os.path.join(out, it["name"] + ".jpg"), quality=94)
            scores[it["name"]] = round(sc, 3)

    for i in range(n):
        paint(i)
    while time.time() - t0 + per * 1.1 < budget:
        missing = [i for i in range(n) if items[i]["name"] not in scores and tries[i] < 5]
        weak = [i for i in range(n) if scores.get(items[i]["name"], 1) < CLIP_MIN and tries[i] < 3]
        todo = sorted(missing, key=lambda i: tries[i]) or weak
        if not todo:
            break
        paint(todo[0])
    json.dump(scores, open(os.path.join(out, "_clip.json"), "w"))
    json.dump([it["name"] for it in items if it["name"] not in scores], open(os.path.join(out, "_faces.json"), "w"))


if __name__ == "__main__":
    items, out = json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]
    s = time.time()
    subprocess.run("df -h / | tail -1; free -g | head -2; nproc", shell=True)
    generate(items, out)
    print(f"total {time.time()-s:.0f}s")
