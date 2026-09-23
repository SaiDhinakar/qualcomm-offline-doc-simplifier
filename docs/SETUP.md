# Setup & Prerequisites

## Current status (updated Sep 24, 2026)

- **AI Hub:** token configured (`qai-hub configure`); real compile + profile jobs completed on
  **Snapdragon X Elite CRD** (results in `data/ai_hub_profile_probe.json` — inference on **NPU**).
- **OCR:** Tesseract 5 (eng/afr/osd) primary; PaddleOCR 3.x fallback for missing packs (e.g. Hindi).
- **LLM:** Ollama `qwen2.5:0.5b` (`QDS_LLM=ollama`); stub for tests.
- **Embeddings:** fastembed `BAAI/bge-small-en-v1.5` (`QDS_EMBED=fastembed`); hash stub for tests.
- **Local env:** `uv` + `.venv` (Python 3.10); 80+ tests green; ruff clean.

**Never commit the token.** Copy `.env.example` to `.env` and put the real token there — `.env` is
already git-ignored. The `qai-hub configure` command below also stores it in a local config file
outside the repo (`~/.qai_hub/client.ini`).

## Accounts you need

- [ ] **GitHub account** — to host this repo.
- [x] **Qualcomm ID + Qualcomm AI Hub account** — API token configured. Used to compile,
      quantize, and profile models on real cloud-hosted Snapdragon devices (you don't need to own
      the hardware).
- [ ] **Unstop / challenge submission account** — for the actual entry.

## Local dev environment

- [x] **Python 3.10** via `uv` (`.venv/`).
- [x] **Git**.
- [x] A code editor.

```bash
# Preferred (this repo):
uv venv --python 3.10 && source .venv/bin/activate
uv pip install -e ".[embed,paddle,qai]"   # or pip install -r requirements.txt

# Qualcomm AI Hub:
uv pip install qai-hub
qai-hub configure --api_token <YOUR_API_TOKEN>   # AI Hub → Account → Settings → API Token

# Optional local LLM:
ollama pull qwen2.5:0.5b
export QDS_LLM=ollama QDS_EMBED=fastembed QDS_OCR=auto
```

### Backend selection (env vars read by the CLI)

| Var | Values | Default |
|-----|--------|---------|
| `QDS_LLM` | `stub` \| `ollama` \| `llamacpp` | `stub` |
| `QDS_EMBED` | `hash` \| `fastembed` \| `sentence-transformers` | `hash` |
| `QDS_OCR` | `tesseract` \| `paddle` \| `auto` | `auto` |
| `QDS_OLLAMA_MODEL` | e.g. `qwen2.5:0.5b` | `qwen2.5:0.5b` |

### True end-to-end test

```bash
python -m pytest tests/test_e2e.py -v          # file → OCR → answer (stub backends)
QDS_E2E_REAL=1 python -m pytest tests/test_e2e.py -v   # Ollama + fastembed
```

## Windows on ARM64 caveat

If/when you're working directly on Snapdragon X/X2 Windows-on-ARM hardware (e.g. if you get access
to the actual HP Omnibook), note: some Qualcomm AI Hub Models tooling requires **AMD64 Python**,
not ARM64 Python — installs will fail on native ARM64 Python for some of that tooling. This doesn't
block using the cloud device farm from a regular x86/ARM dev laptop in the meantime.

## Model-related tools (finalized)

- [x] **OCR:** Tesseract 5.5.3 + PyMuPDF (primary); PaddleOCR 3.7 / Paddle 3.3 (fallback for
      missing Tesseract language packs — set `PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False` to avoid
      a oneDNN/PIR crash on some CPUs; the code sets this automatically).
- [x] **Local LLM:** Ollama (`qwen2.5:0.5b`) via HTTP — no compile step. `llama-cpp-python` has
      no prebuilt wheels on this host (source build times out); use Ollama instead.
- [x] **Embeddings:** fastembed (`BAAI/bge-small-en-v1.5`, 384-d ONNX, no torch).
- [x] **`qai-hub` / `qai-hub-models`:** installed; real compile+profile job run on
      Snapdragon X Elite CRD (NPU). See `data/ai_hub_profile_probe.json`.

## Sample documents for testing

Put test documents (insurance policies, rental agreements, etc.) in `data/samples/`. This folder
is **gitignored** — don't commit real documents with real personal/financial information, even
your own. Use sample/dummy documents, or anonymized ones, for anything you commit or demo.
