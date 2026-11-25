"""Transcribe a release video with faster-whisper (word timestamps) -> data/transcripts/<name><suffix>.json

Default: large-v3. OUT_SUFFIX .rubai / .kotib / .navai = open whisper models fine-tuned on Uzbek (Hugging Face, apache-2.0,
safetensors only, converted to CTranslate2 here, no remote code).
"""
import json, os, subprocess, sys

UZ_MODELS = {".rubai": "islomov/rubaistt_v2_medium", ".kotib": "Kotib/uzbek_stt_v1", ".navai": "navai-uz/whisper-medium-uzbek"}


def uz_model(suffix):
    """path of the converted model (cached under ~/.ollama/models/uzstt, which auto.yml already caches between runs)"""
    repo = UZ_MODELS[suffix]
    out = os.path.expanduser("~/.ollama/models/uzstt/" + repo.replace("/", "__"))
    if not os.path.exists(out + "/model.bin"):
        pip = [sys.executable, "-m", "pip", "install", "--quiet"]
        subprocess.run(pip + ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
        subprocess.run(pip + ["transformers<5", "sentencepiece", "ctranslate2", "faster-whisper"], check=True)
        from huggingface_hub import snapshot_download
        src = snapshot_download(repo, allow_patterns=["*.json", "*.txt", "*.safetensors"])
        tok = os.path.join(src, "tokenizer.json")
        if not os.path.exists(tok):
            from transformers import WhisperTokenizerFast
            WhisperTokenizerFast.from_pretrained(src).save_pretrained(src)
        copy = [f for f in ("tokenizer.json", "preprocessor_config.json") if os.path.exists(os.path.join(src, f))]
        subprocess.run(["ct2-transformers-converter", "--model", src, "--output_dir", out, "--quantization", "int8", "--force",
                        "--copy_files", *copy], check=True)
    return out


def transcribe(video, model_name, prompt=None, vad=False):
    import numpy as np
    from faster_whisper import WhisperModel
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language="uz", word_timestamps=True, beam_size=5, vad_filter=vad,
                                  initial_prompt=prompt, condition_on_previous_text=not vad)
    out = {"language": info.language, "model": os.path.basename(model_name), "audio_seconds": len(audio) / 16000, "segments": []}
    for s in segs:
        out["segments"].append({"start": s.start, "end": s.end, "text": s.text.strip(), "avg_logprob": round(s.avg_logprob, 3),
                                "words": [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for w in s.words]})
    return out


def main(name):
    subprocess.run(["gh", "release", "download", "videos", "-p", name, "-D", "work", "--clobber"], check=True)
    suffix = os.environ.get("OUT_SUFFIX", "")
    prompt, vad = os.environ.get("WHISPER_PROMPT") or None, os.environ.get("WHISPER_VAD", "") == "1"
    if suffix in UZ_MODELS:
        out = transcribe(f"work/{name}", uz_model(suffix), None, False)
    else:
        out = transcribe(f"work/{name}", os.environ.get("WHISPER_MODEL", "large-v3"), prompt, vad)
    os.makedirs("data/transcripts", exist_ok=True)
    json.dump(out, open(f"data/transcripts/{name}{suffix}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(f"SEG {s['start']:.1f}-{s['end']:.1f} {s['text']}" for s in out["segments"]))


if __name__ == "__main__":
    main(sys.argv[1])
