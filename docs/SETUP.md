# Setup & Prerequisites

## Accounts you need

- [ ] **GitHub account** — to host this repo.
- [ ] **Qualcomm ID + Qualcomm AI Hub account** — sign up at https://aihub.qualcomm.com. Needed to
      compile, quantize, and profile models on real cloud-hosted Snapdragon devices (you don't need
      to own the hardware).
- [ ] **Unstop / challenge submission account** — for the actual entry.

## Local dev environment

- [ ] **Python 3.10** (via Miniconda, per Qualcomm AI Hub's documented setup).
- [ ] **Git**.
- [ ] A code editor (VS Code recommended — good Python + Jupyter support).

```bash
conda create -n qualcomm-offline-doc-simplifier python=3.10
conda activate qualcomm-offline-doc-simplifier
pip install qai-hub
qai-hub configure --api_token <YOUR_API_TOKEN>   # from AI Hub > Account > Settings > API Token
```

## Windows on ARM64 caveat

If/when you're working directly on Snapdragon X/X2 Windows-on-ARM hardware (e.g. if you get access
to the actual HP Omnibook), note: some Qualcomm AI Hub Models tooling requires **AMD64 Python**,
not ARM64 Python — installs will fail on native ARM64 Python for some of that tooling. This doesn't
block using the cloud device farm from a regular x86/ARM dev laptop in the meantime.

## Model-related tools (finalize once models are chosen)

- [ ] OCR library/model — TBD
- [ ] Local LLM runtime — TBD (via AI Hub GenieX: llama.cpp or QAIRT plugin)
- [ ] Embedding model — TBD
- [ ] `qai-hub-models` package if using a pre-optimized model from the AI Hub Model Zoo

## requirements.txt

See [`requirements.txt`](../requirements.txt) in the repo root — currently a starter file with
placeholders; we'll pin exact packages once models are chosen.

## Sample documents for testing

Put test documents (insurance policies, rental agreements, etc.) in `data/samples/`. This folder
is **gitignored** — don't commit real documents with real personal/financial information, even
your own. Use sample/dummy documents, or anonymized ones, for anything you commit or demo.
