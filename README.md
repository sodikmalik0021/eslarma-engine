# eslarma-engine

Code of an automatic reel studio: Uzbek speech recognition, shot planning, paintings with an open image model, 2.5D animation,
a quality gate and publishing at fixed slots. It runs on GitHub Actions. All content (queue, texts, videos) lives in a private repository.

- `run.sh beat` - wakes the private publisher around the slots (`tools/slots.py`)
- `run.sh produce` - makes one reel and puts it into the stock
- `workflows/` - copied to `.github/workflows` when the owner enables the engine
