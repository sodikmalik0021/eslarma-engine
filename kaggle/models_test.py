# Which open model draws a flat 2D Uzbek illustration best (not a photo). Same prompts, same seeds.
import os, subprocess, time
subprocess.run("pip install -q -U diffusers transformers accelerate safetensors", shell=True)
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler, AutoencoderKL
OUT = "/kaggle/working/out"; os.makedirs(OUT, exist_ok=True)
S = "flat 2D Uzbek illustration, vector art, cobalt blue and white Pakhta-gul ornaments, ikat adras textile patterns, turquoise tiled domes, warm sand and gold accents, subtle paper grain, clean simple shapes, faceless people, flat colors, "
NEG = "photo, photograph, photorealistic, realistic, 3d render, cgi, depth of field, bokeh, church, cross, text, letters, watermark, blurry, deformed"
P = ["Uzbek man in white skullcap and dark blue chapan seen from behind sitting on a hill at sunrise",
     "round carpet with blue Pakhta-gul teapot and tea bowls under an old mulberry tree in an Uzbek courtyard",
     "Uzbek mahalla street with arched wooden doors and a mosque with turquoise dome, a man walking seen from behind"]
M = {"sdxl": ("stabilityai/stable-diffusion-xl-base-1.0", 28, 6.0), "dreamshaper": ("Lykon/dreamshaper-xl-v2-turbo", 8, 2.0)}
vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
for d, (name, (repo, steps, cfg)) in enumerate(M.items()):
    p = StableDiffusionXLPipeline.from_pretrained(repo, vae=vae, torch_dtype=torch.float16, use_safetensors=True).to(f"cuda:{d}")
    p.scheduler = DPMSolverMultistepScheduler.from_config(p.scheduler.config, use_karras_sigmas=True)
    for k, x in enumerate(P):
        t = time.time()
        im = p(prompt=S + x, negative_prompt=NEG, num_inference_steps=steps, guidance_scale=cfg, width=832, height=1472,
               generator=torch.Generator(f"cuda:{d}").manual_seed(7 + k)).images[0]
        im.save(f"{OUT}/{name}_{k}.jpg", quality=92); print(name, k, f"{time.time()-t:.0f}s", flush=True)
