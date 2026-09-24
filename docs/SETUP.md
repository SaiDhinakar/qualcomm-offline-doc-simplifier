# Setup & Prerequisites

Everything needed to run the Qualcomm Offline Doc Simplifier locally, plus the optional
Qualcomm AI Hub configuration used for on-device validation.

Maintainer: [SaiDhinakar](https://github.com/SaiDhinakar).

---

## 1. Requirements at a glance

| Requirement | Required? | Notes |
|---|---|---|
| Python 3.10+ | Yes | Matches Qualcomm AI Hub's documented environment; the project is developed on 3.10 |
| Tesseract OCR 5.x | Yes | `tesseract-ocr` system package; language packs per target language |
| Git | Yes | For cloning |
| Ollama (or another local LLM) | For real explanations | Optional — stub backend works for development and tests |
| `fastembed` extra | For real embeddings | Optional — hash backend works for development and tests |
| Qualcomm AI Hub token | For hardware validation only | Not needed to run the pipeline |
| `opencv-python` | Optional | Only for webcam capture (`src/ocr/webcam.py`) |

PDF pages are rasterized with **PyMuPDF**, so Poppler/`pdf2image` is not needed at runtime
(`pdf2image` remains in the dependency list for compatibility but is unused by the pipeline).

### System packages

```bash
# Debian / Ubuntu
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
# additional OCR languages as needed, e.g. Hindi:
sudo apt-get install -y tesseract-ocr-hin

# macOS
brew install tesseract
```

Verify: `tesseract --version` (developed against 5.5.3).

---

## 2. Install the project

```bash
git clone https://github.com/SaiDhinakar/qualcomm-offline-doc-simplifier.git
cd qualcomm-offline-doc-simplifier
```

### Option A — `uv` (preferred)

```bash
uv venv --python 3.10
source .venv/bin/activate
uv pip install -e ".[embed,paddle,qai]"
```

### Option B — plain `venv` + pip

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[embed]"
```

### Extras

| Extra | Installs | Needed for |
|---|---|---|
| `embed` | `fastembed` | Real semantic embeddings (`QDS_EMBED=fastembed`) |
| `paddle` | `paddlepaddle`, `paddleocr` | OCR fallback for missing Tesseract language packs |
| `qai` | `qai-hub`, `qai-hub-models` | Compile/profile jobs on Qualcomm AI Hub |
| `ai` | `torch`, `sentence-transformers`, `llama-cpp-python` | Alternative LLM/embedding backends |
| `dev` | `ruff`, `mypy` | Linting and type checking |

`requirements.txt` is a flat equivalent of the core dependencies if you prefer
`pip install -r requirements.txt`.

The `qds` console script is installed as part of the editable install
(`[project.scripts] qds = "src.cli:main"`). If you skipped the editable install, run the CLI as
`python -m src.cli` from the repository root instead.

---

## 3. Backend selection

Backends are chosen through environment variables — no config file editing required:

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `QDS_LLM` | `stub` \| `ollama` \| `llamacpp` | `stub` | Simplification / merge / Q&A generator |
| `QDS_EMBED` | `hash` \| `fastembed` \| `sentence-transformers` | `hash` | Chunk + question embeddings |
| `QDS_OCR` | `tesseract` \| `paddle` \| `auto` | `auto` | OCR engine (`auto` = Tesseract, Paddle on failure) |
| `QDS_OLLAMA_MODEL` | e.g. `qwen2.5:0.5b` | `qwen2.5:0.5b` | Ollama model name |
| `QDS_LLAMA_PATH` | path to a `.gguf` file | — | Model file for `QDS_LLM=llamacpp` |
| `QDS_E2E_REAL` | `1` | unset | Run the end-to-end test against real backends |

Recommended for a real demo:

```bash
ollama pull qwen2.5:0.5b
export QDS_LLM=ollama QDS_EMBED=fastembed QDS_OCR=auto
```

Stub/hash backends are deterministic and dependency-free — they are what the default test suite
uses, so you can develop and run tests before downloading any model.

First run of `fastembed` downloads the ONNX embedding model (~100 MB) from Hugging Face, and
`ollama pull` downloads the LLM. Both are one-time, setup-time network operations; document
processing itself does not use the network.

---

## 4. Verify the installation

```bash
qds info                                   # compute units, sessions, disclaimer
python -m pytest tests -q                  # expected: 82 passed, 1 skipped
ruff check src tests                       # expected: All checks passed
```

`qds info` prints the compute-unit indicator (FR-22), e.g. `[CPU] CPU (always available)` on a
machine without Qualcomm hardware — the NPU line only appears where an NPU is actually
detectable.

---

## 5. Qualcomm AI Hub (hardware validation only)

Used to compile, quantize and profile model components on real cloud-hosted Snapdragon devices.
Not required to run the pipeline.

```bash
uv pip install qai-hub                      # or: pip install ".[qai]"
qai-hub configure --api_token <YOUR_TOKEN>  # AI Hub → Account → Settings → API Token
```

**Never commit the token.** Copy `.env.example` to `.env` for the environment-variable form —
`.env` is git-ignored. `qai-hub configure` writes to `~/.qai_hub/client.ini`, outside the
repository.

Profiling results from the completed run live in `data/ai_hub_profile_probe.json` with the full
profiler log alongside it; interpretation is in [`PERFORMANCE.md`](PERFORMANCE.md).

---

## 6. Sample documents

Put test documents (insurance policies, rental agreements, scans) in `data/samples/`.

That folder is **git-ignored** (only `.gitkeep` is tracked): never commit real documents with
real personal or financial information — not even your own. Use dummy or anonymized documents for
anything committed, shared or demoed. The test suite ships its own anonymized fixture at
`tests/fixtures/golden_sample.txt`.

---

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Tesseract language pack 'hin' not installed` | Install the pack (`sudo apt-get install tesseract-ocr-hin`) or rely on the PaddleOCR fallback with `QDS_OCR=auto` |
| `All OCR engines failed` | Neither engine could read the input — check the file type (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`) and that Tesseract is on `PATH` |
| `llama-cpp-python` build times out | No prebuilt wheel for this host — use `QDS_LLM=ollama` instead (the documented default) |
| PaddleOCR crashes with a oneDNN/PIR error | The code sets `PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False` automatically; if invoking Paddle directly, set it yourself |
| Warning about unauthenticated requests to the HF Hub | Harmless; set `HF_TOKEN` to raise rate limits on model downloads |
| `No active session for document '<id>'` | Sessions are in-process and session-scoped — run `qds interactive <path>` for analyze + ask in one process (see [`CLI.md`](CLI.md)) |
| `qds: command not found` | The editable install provides the script — re-run `pip install -e ".[embed]"`, or use `python -m src.cli` |
| Windows on ARM64: AI Hub Models tooling fails to install | Some Qualcomm tooling requires **AMD64 Python**, not ARM64 Python. Only relevant on Snapdragon Windows hardware; the cloud device farm works from any normal dev machine |

---

## 8. Current environment status

Recorded from the machine this documentation was written on (Sep 24, 2026):

- Python 3.10.20 in `.venv` via `uv`.
- Tesseract 5.5.3 (language packs: `eng`, `afr`, `osd`).
- Ollama 0.32.6 with `qwen2.5:0.5b`.
- fastembed 0.8.1 (`BAAI/bge-small-en-v1.5`).
- `qai-hub` configured; compile + profile job `j5687vxyg` completed on Snapdragon X Elite.
- Test suite: 82 passed, 1 skipped (the skipped test is the opt-in real-backend e2e).
- `ruff check src tests` clean.
