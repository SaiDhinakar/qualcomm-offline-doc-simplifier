# Performance & Hardware Validation

Measured results for the Qualcomm Offline Doc Simplifier, the method used to obtain them, and
what is still open.

Maintainer: [SaiDhinakar](https://github.com/SaiDhinakar).

---

## 1. What is being measured

Two distinct things, because they answer different questions:

| Question | Measurement |
|---|---|
| Does the on-device story hold on real Snapdragon hardware? | Qualcomm AI Hub cloud device jobs: compile → profile a model on a physical device, recording compute-unit utilization, latency and memory |
| Is the application usable end-to-end today? | Local wall-clock timings of each pipeline stage on the development machine |

AI Hub results are the hardware evidence (FR-22 and the PRD's "Hardware validation"
non-functional requirement). Local timings are the user-experience evidence, and they currently
reflect a CPU-only LLM runtime — see §4 and §5.

---

## 2. Qualcomm AI Hub validation run

| Field | Value |
|---|---|
| Job ID | `j5687vxyg` |
| Client | `qai-hub` |
| Device | Snapdragon X Elite — SOC `SC8380XP`, Hexagon architecture 73, 1 HTP core |
| Runtime | QNN HTP execution provider (`QnnHtp.dll`), FP16 precision enabled (`enable_htp_fp16_precision = 1`) |
| Input | `model.onnx` (probe model used to validate the toolchain and device access) |
| Artifacts | `data/ai_hub_profile_probe.json` (metrics), `data/ai_hub_profile_probe_runtime.log` (full profiler log) |
| Date | Sep 23, 2026 |

### 2.1 Compute-unit utilization (the core claim)

Every node in the profiled graph executed on the **NPU** — no silent CPU/GPU fallback:

| Node | Compute unit | Execution time | Execution cycles |
|---|---|---|---|
| Input | NPU | 10 µs | 14,281 |
| `node` (compute) | NPU | 259 µs | 363,432 |
| Output | NPU | 11 µs | 15,472 |

The layer-wise rows are per-layer measurements; whole-graph inference is reported separately in
§2.2 and is faster than their sum because they are measured by different profiler passes.

### 2.2 Latency

| Metric | Value | Notes |
|---|---|---|
| First (cold) inference | 1,325 µs | Includes first-touch overhead |
| Steady-state inference | 160–198 µs over 100 runs | Median **178 µs**, mean of the profiled set ≈200 µs |
| Reported estimated inference time | 160 µs | AI Hub summary field |
| Cold model load | 2,577,311 µs ≈ **2.58 s** | One-time, at process/model start |
| Warm model load | 561,389 µs ≈ **0.56 s** | Subsequent loads |

### 2.3 Memory

| Metric | Value |
|---|---|
| Inference memory increase | 3,854,336 bytes ≈ **3.7 MB** |
| Peak memory during inference | 32,415,744 bytes ≈ **30.9 MB** |
| Peak memory after cold load | ≈262 MB (page-level peak reported by the profiler) |
| Peak memory after warm load | ≈27.6 MB |

### 2.4 Interpretation

- **NPU execution is demonstrated, not assumed** — the profiler attributes every node to NPU on
  a physical Snapdragon X Elite, which is the evidence behind the CLI's compute-unit indicator.
- Steady-state inference for the profiled model is sub-millisecond, so inference is not the
  bottleneck; **model load** (≈2.6 s cold) is the one-time cost to design around.
- These numbers are for the **probe model**, not the production LLM. Compiling/quantizing the
  actual LLM and embedding model through the same flow remains open — tracked in
  [`ROADMAP.md`](ROADMAP.md).

---

## 3. How to reproduce the AI Hub run

```bash
pip install qai-hub            # or: pip install ".[qai]"
qai-hub configure --api_token <token>     # token from .env — never commit it
```

Then submit a profile job against a target device (compile → profile → validate, as described in
`ARCHITECTURE.md` §8.2) and download the resulting metrics JSON. Keep the raw JSON and profiler
log in `data/` — they are the evidence cited in the presentation.

---

## 4. Local end-to-end timings

Environment: Linux x86_64 development machine, Python 3.10.20, CPU-only (no Snapdragon NPU
locally), backends `QDS_LLM=ollama` (`qwen2.5:0.5b`), `QDS_EMBED=fastembed`
(`BAAI/bge-small-en-v1.5`), `QDS_OCR=auto` (Tesseract 5.5.3). Sample: one-page insurance-policy
PDF, 12 layout regions, 5 chunks, 3 glossary terms. Sep 24, 2026.

### 4.1 Stage breakdown

| Stage | Time | Share | Notes |
|---|---|---|---|
| OCR + layout extraction | 1.34 s | 1.8% | PyMuPDF rasterization at 150 DPI + Tesseract |
| OCR quality analysis (FR-4) | <0.01 s | — | |
| Chunking | <0.01 s | — | Pure regex/structure pass |
| Glossary extraction | <0.01 s | — | |
| Per-chunk simplification | **47.17 s** | 61.7% | 5 sequential LLM calls ≈9.4 s each |
| Hierarchical merge | **26.92 s** | 35.2% | 1 LLM call, up to 1024 output tokens |
| Embeddings | 1.00 s | 1.3% | First call includes ONNX model load |
| Vector index build | <0.01 s | — | |
| **Total (`analyze`)** | **≈76 s** | | Matches end-to-end runs (73–78 s) |
| **Q&A (`ask`, warm)** | **≈3.2–3.7 s** | | Embed question + retrieve + one LLM call |

### 4.2 What this says

- OCR, chunking, glossary, embedding and indexing together cost ~2.3 s — **the pipeline is
  LLM-bound**.
- All five simplification calls run **sequentially** today. Chunks are independent by design
  (`ARCHITECTURE.md` §4, step 4), so parallelising that loop is the single highest-value
  optimisation: with 5-way concurrency the same run would be bounded by the slowest stage pair
  (simplify ≈9 s + merge ≈27 s) rather than their sum.
- The merge call is the second-largest cost because it generates a long structured overview.
  Capping `max_tokens` or merging in two passes (headline summary + details) would cut it.
- Q&A at ~3.5 s is acceptable for a demo, but dominated by generation; a smaller answer budget
  (`max_tokens=512`, already in use) keeps it bounded.
- None of these numbers yet reflect NPU execution of the LLM — that requires the AI Hub-compiled
  artifact (§2.4).

---

## 5. Targets and gaps

| Item | Target | Current state |
|---|---|---|
| Compute unit for model execution | NPU, visible in the UI (FR-22) | **Met for the profiled probe model**; indicator shown by every CLI command |
| 10-page document, OCR → overview | Demo-able live (single-digit minutes, no manual steps) | **Not yet measured at 10 pages**; single-page run ≈76 s, so expect a few minutes if the LLM loop stays sequential |
| Retrieval Q&A responsiveness | No multi-second dead air per question | **≈3.5 s** per answer locally |
| Numeric fidelity under quantization | Quantized output matches reference (FR-11) | **Pending** — requires the production-model inference-validation job |
| Production LLM/embedding compiled + profiled | Required before a component is "done" | **Open** — tracked in `ROADMAP.md` |

### Planned optimisations, in order of value

1. Parallelise per-chunk simplification (embarrassingly parallel; biggest single win).
2. Reduce merge token budget / split the merge into two shorter calls.
3. Swap in the AI Hub-compiled, quantized LLM artifact for on-device inference.
4. Cache embeddings for repeated analysis of the same document.
5. Raise OCR DPI only if quality metrics demand it — 150 DPI keeps ≈91% confidence at roughly
   5× the speed of 300 DPI (`_PDF_DPI` in `src/ocr/extract.py`).

---

## 6. Recording new measurements

When adding numbers to this document, record: date, machine, backends and model versions,
document (pages/chunks), and the command used. Prefer raw artifacts in `data/` over transcribed
figures, and keep old measurements visible rather than overwriting them — the trend is part of
the evidence.
