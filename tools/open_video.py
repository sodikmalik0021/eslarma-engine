"""Bring paintings to life: image-to-video with the open LTX-Video 2B model on a CPU; a 3D camera from a depth map when there is no time.

  python3 tools/open_video.py <items.json> <budget seconds>    items: [{"jpg", "mp4", "prompt", "seconds"}]
Writes <mp4> for every item (1080x1920 is done by the renderer). A clip in which a face appears is replaced by the 3D camera.
"""
import gc, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
W, H, FPS = 416, 736, 24
REPO = "Lightricks/LTX-Video-0.9.7-distilled"
MODEL = "https://huggingface.co/Lightricks/LTX-Video/blob/main/ltxv-2b-0.9.8-distilled.safetensors"
STEPS = [1000, 993, 987, 981, 975, 909, 725]


def write(frames, path, fps):
    h, w = frames[0].shape[:2]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg")


def camera3d(items):
    """the near parts of the painting move more than the far ones; about 5 s per picture"""
    import cv2, numpy as np
    from PIL import Image
    from transformers import pipeline
    d = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device="cpu")
    for k, it in enumerate(items):
        im = cv2.resize(cv2.imread(it["jpg"]), (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
        z = np.array(d(Image.open(it["jpg"]).convert("RGB"))["depth"]).astype(np.float32)
        z = cv2.resize(z, (1080, 1920))
        z = (z - z.min()) / (z.max() - z.min() + 1e-6)
        z = cv2.GaussianBlur(cv2.dilate(z, np.ones((15, 15))), (0, 0), 9)
        yy, xx = np.mgrid[0:1920, 0:1080].astype(np.float32)
        n, side, fr = max(40, int(it["seconds"] * FPS)), (1, -1)[k % 2], []
        for j in range(n):
            e = j / (n - 1); a = (e - .5) * 2 * side
            zoom = 1.06 + .05 * e + .10 * e * z
            fr.append(cv2.remap(im, 540 + (xx - 540) / zoom + a * 60 * (z - .4), 960 + (yy - 960) / zoom + a * 14 * (z - .4),
                                cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
        write(fr, it["mp4"], FPS)
        print("3d", os.path.basename(it["mp4"]), flush=True)


def animate(items, budget):
    """returns the items that got no clip"""
    import cv2, numpy as np, torch
    from PIL import Image
    from diffusers import AutoencoderKLLTXVideo, FlowMatchEulerDiscreteScheduler, LTXConditionPipeline, LTXVideoTransformer3DModel
    from transformers import T5EncoderModel, T5TokenizerFast
    import open_art
    t0, dt = time.time(), torch.bfloat16
    tok = T5TokenizerFast.from_pretrained(REPO, subfolder="tokenizer")
    te = T5EncoderModel.from_pretrained(REPO, subfolder="text_encoder", torch_dtype=dt, low_cpu_mem_usage=True)
    emb = []
    for it in items:
        x = tok([it["prompt"]], padding="max_length", max_length=128, truncation=True, return_tensors="pt")
        with torch.no_grad():
            emb.append((te(x.input_ids, attention_mask=x.attention_mask)[0], x.attention_mask))
    del te; gc.collect()
    tr = LTXVideoTransformer3DModel.from_single_file(MODEL, config="Lightricks/LTX-Video", subfolder="transformer", torch_dtype=dt)
    vae = AutoencoderKLLTXVideo.from_pretrained(REPO, subfolder="vae", torch_dtype=dt)
    vae.enable_tiling()
    pipe = LTXConditionPipeline(scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(REPO, subfolder="scheduler"), vae=vae,
                                text_encoder=None, tokenizer=tok, transformer=tr)
    pipe.set_progress_bar_config(disable=True)
    print(f"video model ready in {time.time()-t0:.0f}s", flush=True)
    left, per = [], 0
    for k, it in enumerate(items):
        if time.time() - t0 + per * 1.15 > budget:
            left += items[k:]
            break
        t = time.time()
        try:
            im = Image.open(it["jpg"]).convert("RGB")
            k2 = max(W / im.width, H / im.height)
            im = im.resize((round(im.width * k2), round(im.height * k2)), Image.LANCZOS)
            x, y = (im.width - W) // 2, (im.height - H) // 2
            im = im.crop((x, y, x + W, y + H))
            n = 49 if it["seconds"] < 3.2 else 65
            fr = pipe(image=im, prompt_embeds=emb[k][0], prompt_attention_mask=emb[k][1], width=W, height=H, num_frames=n, frame_rate=FPS,
                      timesteps=STEPS, guidance_scale=1.0, decode_timestep=0.05, image_cond_noise_scale=0.025,
                      generator=torch.Generator().manual_seed(3 + k), output_type="np").frames[0]
            fr = [(f * 255).astype(np.uint8) for f in fr]
            face = any(open_art.has_face(Image.fromarray(fr[j])) for j in range(0, n, 8))
            move = float(np.mean([np.abs(fr[j + 8].astype(int) - fr[j]).mean() for j in range(0, n - 8, 8)]))
            per = max(per * .5, time.time() - t)
            print(f"video {os.path.basename(it['mp4'])} {time.time()-t:.0f}s motion {move:.1f}" + (" FACE" if face else ""), flush=True)
            if face or move < 0.8 or move > 60:
                left.append(it)
                continue
            write([cv2.cvtColor(f, cv2.COLOR_RGB2BGR) for f in fr], it["mp4"], FPS)
        except Exception as e:
            print("video failed:", str(e)[:200], flush=True)
            left.append(it)
    return left


if __name__ == "__main__":
    items, budget = json.load(open(sys.argv[1], encoding="utf-8")), float(sys.argv[2])
    pip = [sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir"]
    subprocess.run(pip + ["-U", "protobuf>=5.29", "sentencepiece"], check=False)
    try:  # when the paintings came from the Kaggle GPU, nothing installed torch on this runner yet
        import torch  # noqa: F401
    except ImportError:
        subprocess.run(pip + ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"], check=False)
        subprocess.run(pip + ["diffusers", "transformers<5", "accelerate", "safetensors", "pillow", "huggingface_hub", "opencv-python-headless<5"], check=False)
        import importlib, site
        site.addsitedir(site.getusersitepackages()); importlib.invalidate_caches()
    try:
        left = animate(items, budget)
    except Exception as e:
        print("video model failed:", str(e)[:400], flush=True)
        left = [it for it in items if not os.path.exists(it["mp4"])]
    gc.collect()
    if left:
        camera3d(left)
    print(f"animated {len(items) - len(left)} of {len(items)}, 3d camera {len(left)}")
