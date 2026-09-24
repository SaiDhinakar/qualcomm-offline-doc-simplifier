# Architecture

| | |
|---|---|
| **Product** | Qualcomm Doc Simplifier |
| **Status** | Implemented — working end-to-end build |
| **Version** | 0.2 |
| **Companion doc** | See `PRD.md` for requirements this design satisfies |
| **Maintainer** | [SaiDhinakar](https://github.com/SaiDhinakar) |

---

## 1. Design principles

1. **Offline-first.** The runtime flow never depends on network access. Any use of Qualcomm AI
   Hub happens ahead of time, during development, to compile/quantize/validate models — not at
   inference time in the shipped product. (One-time model downloads during setup — Ollama,
   Hugging Face — are installation steps, not part of the document flow.)
2. **Privacy by construction, not by policy.** Document content should be architecturally
   incapable of leaving the device during normal use, not merely "not sent" by convention.
3. **Small-model orchestration over one giant model.** A 10-page document is too large to reason
   about in a single LLM call on an on-device quantized model. The system is built as a pipeline
   of small, focused steps instead.
4. **Structure over raw text.** Legal/financial documents carry meaning in their structure
   (clause numbers, defined terms, cross-references). The pipeline preserves and uses that
   structure rather than flattening documents into plain text early.
5. **Validate on real hardware, not assumptions.** Every on-device component must go through
   Qualcomm AI Hub compilation, quantization, and profiling against a real Snapdragon device
   before being considered functional — "should work on NPU" is not sufficient.

---

## 2. System overview

```
                     ┌────────────────────────────────────────────────────┐
                     │                  Pipeline Orchestrator               │
                     └────────────────────────────────────────────────────┘
                                          │
      ┌───────────┬───────────┬──────────┼───────────┬───────────┬──────────┐
      ▼           ▼           ▼          ▼           ▼           ▼          ▼
  ┌───────┐  ┌──────────┐ ┌─────────┐┌─────────┐┌───────────┐┌────────┐┌──────────┐
  │  OCR &  │  │Structure-│ │Glossary ││Per-chunk││ Embed &   ││Hierarch││ On-device │
  │ Layout  │─▶│  aware   │▶│Extractor│▶│Simplify ││  Index    ││-ical   ││  Q&A (RAG)│
  │Extraction│  │ Chunker  │ │         ││ (LLM)   ││ (local)   ││ Merge  ││           │
  └───────┘  └──────────┘ └─────────┘└─────────┘└───────────┘└────────┘└──────────┘
                                                        │
                                              ┌──────────────────┐
                                              │ Vector Store      │
                                              │ Lifecycle Manager │
                                              └──────────────────┘
```

All components run on-device at inference time. Qualcomm AI Hub is used **only** during the
build/validation phase to produce the compiled, quantized model artifacts these components load.

---

## 3. Component breakdown

### 3.1 OCR & Layout Extraction (`src/ocr`)
- **Responsibility:** convert a photographed or scanned document into text while preserving page
  structure (headings, clause numbers, paragraphs, tables).
- **Input:** image(s) (PNG/JPG/TIFF/BMP/WEBP) or PDF — PDFs are rasterized at 150 DPI via PyMuPDF
  before OCR.
- **Output:** per-page structured text with layout metadata (bounding boxes, detected headings,
  table regions) and a per-region OCR confidence score.
- **Engines:** Tesseract 5 (primary), PaddleOCR 3.x (fallback for missing language packs and
  engine failures); `auto` tries Tesseract first. Text is assembled per OCR block, so layout
  regions stay distinct rather than collapsing into one blob.
- **Notes:** confidence scores feed FR-4 (flagging low-confidence regions rather than silently
  guessing); webcam capture lives in `src/ocr/webcam.py` (FR-1).

### 3.2 Structure-Aware Chunker (`src/chunking`)
- **Responsibility:** split the extracted document into chunks aligned to clause/section
  boundaries rather than fixed token windows.
- **Input:** structured text + layout metadata from OCR.
- **Output:** ordered list of `Chunk` objects (see §7 data model).
- **Notes:** target chunk size must comfortably fit the chosen LLM's practical context window;
  exact size is tuned once the LLM is chosen (§11 of PRD).

### 3.3 Glossary Extractor (`src/glossary`)
- **Responsibility:** scan all chunks once to identify defined terms and their definitions.
- **Input:** all chunks for a document.
- **Output:** a `Glossary` table (`term → definition`, plus the source chunk id(s)).
- **Notes:** enables later stages to resolve references like "as defined in Section 3" without
  needing the whole document in context at once.

### 3.4 Per-Chunk Simplifier (`src/simplify`)
- **Responsibility:** explain each chunk in plain language, in the target language, using the
  glossary for term resolution.
- **Input:** one `Chunk` + relevant `Glossary` entries + target language.
- **Output:** a plain-language explanation string per chunk, with numeric values
  (amounts/dates/percentages) preserved verbatim from the source.
- **Model:** local LLM behind the `LLMBackend` abstraction — Ollama (`qwen2.5:0.5b`) in the
  current build, with a `llama-cpp-python` path and a deterministic stub for tests (see §7).
  Target: an AI Hub GenieX-validated, quantized artifact for the shipped on-device build (§8.3).

### 3.5 Embedding & Local Vector Index (`src/embed_index`)
- **Responsibility:** produce a vector representation of each chunk and support similarity search
  over them, entirely in-memory/on-device.
- **Input:** chunks (raw text) from the chunker.
- **Output:** an in-memory index (embedding vectors + references back to chunk text).
- **Scale note:** a 10-page document yields roughly 30–50 chunks — small enough that a
  brute-force cosine-similarity search over an array is sufficient. A dedicated vector database is
  not necessary at this scale and would add complexity without benefit.

### 3.6 Hierarchical Merge (`src/simplify`, merge path)
- **Responsibility:** combine per-chunk explanations into one coherent document overview,
  surfacing the most consequential points (obligations, risks, key dates/amounts) rather than
  strictly following document order.
- **Input:** all per-chunk explanations for a document.
- **Output:** a single overview explanation.
- **Notes:** operates over already-simplified text, which is why it stays within context limits
  even though the source document was long.

### 3.7 On-Device Q&A / RAG (`src/qa`)
- **Responsibility:** answer a free-text user question using only retrieved, relevant document
  content.
- **Flow:** embed the question → retrieve top-k relevant chunks from the local index → pass
  question + retrieved chunk text to the LLM → return an answer grounded in that content.
- **Failure mode handling:** if retrieval similarity is below a defined threshold, respond that
  the document doesn't appear to address the question, rather than answering from general
  knowledge (this is a correctness/trust requirement, not just UX polish).

### 3.8 Vector Store Lifecycle Manager (`src/embed_index`, lifecycle path)
- **Responsibility:** own the lifetime of the in-memory (or, if enabled later, persisted) index
  and associated chunk text.
- **Default behavior:** session-scoped — index and chunk text are dropped when the document view
  is closed.
- **If persistence is added (stretch feature):** must be opt-in, time-boxed (e.g. auto-expire
  after a defined window), and paired with a visible "clear analyzed documents" user action.
  Persisted data relies on OS-level full-disk encryption (e.g. BitLocker) as the real protection
  layer — not on "secure delete," since overwrite-based deletion is unreliable on SSDs due to wear
  leveling.

### 3.9 Pipeline Orchestrator (`src/pipeline`)
- **Responsibility:** sequences the above stages for two flows — "analyze a new document" and
  "ask a question about an already-analyzed document" — and owns error handling/fallback behavior
  between stages.

---

## 4. Data flow — "Analyze Document" sequence

1. User provides a document (photo/scan) → **OCR & Layout Extraction**.
2. Structured text + layout → **Structure-Aware Chunker** → ordered `Chunk[]`.
3. `Chunk[]` → **Glossary Extractor** → `Glossary`.
4. For each `Chunk` (with `Glossary` available) → **Per-Chunk Simplifier** → `Explanation` per
   chunk. (Independent per chunk — parallelizable.)
5. `Chunk[]` → **Embedding & Local Vector Index** → in-memory index (can run concurrently with
   step 4).
6. All `Explanation`s → **Hierarchical Merge** → single `Overview`.
7. `Overview` (+ underlying index, held by the **Vector Store Lifecycle Manager**) returned to the
   UI for display.

## 5. Data flow — "Ask a Question" sequence

1. User submits a free-text `Question` for an already-analyzed document (index must still be
   live — see §3.8 lifecycle).
2. `Question` → embedded using the same embedding model as indexing.
3. Similarity search against the local index → top-k relevant `Chunk`s.
4. If best similarity < threshold → return "not addressed in this document" response.
5. Else → `Question` + retrieved `Chunk` text → LLM → grounded `Answer`.
6. `Answer` returned to the UI, ideally with a reference to which chunk/section it came from.

---

## 6. Data model

```
Document
  - id
  - source_type: "photo" | "scan" | "pdf"
  - pages: Page[]
  - language: str   # target explanation language

Page
  - page_number: int
  - raw_text: str
  - layout_regions: Region[]   # headings, paragraphs, tables, with bounding boxes
  - ocr_confidence: float

Chunk
  - id
  - document_id
  - page_number: int
  - section_id: str | None      # e.g. "Clause 4.2", if detected
  - order_index: int            # position within document
  - raw_text: str
  - embedding: float[]          # populated by embed_index stage
  - explanation: str | None     # populated by simplify stage

GlossaryEntry
  - term: str
  - definition: str
  - source_chunk_ids: str[]

DocumentSession
  - document_id
  - chunks: Chunk[]
  - glossary: GlossaryEntry[]
  - overview: str
  - index_handle: <in-memory index reference>
  - ocr_report: OCRQualityReport     # populated for FR-4 flagging
  - compute_unit: str                # "[NPU] ..." indicator — FR-22
  - created_at, expires_at (if persistence enabled)
```

---

## 7. Technology stack

All previously open decisions (PRD §11) are now resolved. Actual choices in use:

| Layer | Choice | Status |
|---|---|---|
| Language | Python 3.10 (`.venv` via `uv`; `requires-python = ">=3.10"`) | Confirmed (per Qualcomm AI Hub's documented environment) |
| Hardware validation | Qualcomm AI Hub (`qai-hub` client) — compile + profile job `j5687vxyg` completed on Snapdragon X Elite | Confirmed; results in `data/ai_hub_profile_probe.json` |
| LLM runtime | Ollama `qwen2.5:0.5b` over HTTP (default real backend); `llama-cpp-python` path retained as an alternative; `StubLLM` for tests | Confirmed in use |
| Embeddings | fastembed `BAAI/bge-small-en-v1.5` (384-d, ONNX, no torch); `sentence-transformers` optional; deterministic hash backend for tests | Confirmed in use |
| OCR | Tesseract 5.5.3 + PyMuPDF (primary), PaddleOCR 3.x fallback for missing language packs; `auto` engine selection | Confirmed in use |
| Custom model compilation | AI Hub Workbench (compile → quantize → profile → validate) | Confirmed approach; applied to the probe model, full LLM/embedding compile still open (Roadmap) |
| Local vector search | Brute-force cosine similarity (NumPy) | Confirmed — ~30–50 vectors/doc; revisit only if profiling shows a need |
| UI | Click-based CLI (`qds`) for MVP | Confirmed for this submission; minimal GUI is a stretch item |
| Data models | Pydantic v2 (`src/models.py`) | Confirmed |
| Secrets management | Environment variable / `qai-hub configure`, via `.env` (git-ignored) | Confirmed |
| Lint / type-check | Ruff (`E,F,I,N,W,UP`, line length 100); mypy configured in `pyproject.toml` | Ruff enforced; mypy has known outstanding findings |

---

## 8. Qualcomm AI Hub integration & validation strategy

**Context:** at project start, the only asset available is a Qualcomm AI Hub API token — no
physical Snapdragon/HP hardware. The architecture is built around this deliberately, not as a
workaround:

- All hardware-specific work (compilation, quantization, profiling, numerical accuracy
  validation) happens via **Qualcomm AI Hub's cloud-hosted device jobs**, which run the actual
  model on a real physical Snapdragon device remotely.
- Local development happens on whatever machine is available, using the reference (unquantized)
  model for logic/pipeline development, then swapping in the AI Hub-compiled artifact for final
  validated runs.

### 8.1 Setup
```bash
pip install qai-hub
qai-hub configure --api_token <token-from-env-var>
```
The token is read from an environment variable (see `.env.example`), never hardcoded or committed.

### 8.2 Validation workflow (per model component)
1. **Compile** — submit the model (PyTorch/ONNX/TorchScript) with a target device + runtime
   (QNN/QAIRT, TFLite, or ONNX Runtime) to AI Hub.
2. **Quantize** — apply hardware-aware quantization (e.g. INT8/INT4) as part of the compile step;
   this is usually what makes an LLM practically fast enough on-device.
3. **Profile** — run the compiled model on a real cloud-hosted Snapdragon device; collect latency,
   memory footprint, and **compute unit utilization** (confirms the model is actually running on
   the Hexagon NPU rather than silently falling back to CPU).
4. **Validate accuracy** — run an inference job with real input data and compare the on-device
   output against the original framework's output, to confirm quantization didn't meaningfully
   change results (critical for FR-11 — numeric fidelity).
5. **Download** — retrieve the compiled, validated model artifact for bundling into the
   application.

### 8.3 Which AI Hub product for which component
- **Local LLM** (simplification, merge, Q&A): **AI Hub GenieX**, built specifically for running
  language/vision-language models on Hexagon NPU / Adreno GPU / CPU.
- **Any custom-trained or fine-tuned component** (e.g. a custom embedding or OCR model): **AI Hub
  Workbench**, for the full compile → quantize → profile → validate flow described above.

### 8.4 Known constraint
Qualcomm AI Hub Models tooling requires AMD64 Python on Windows — native ARM64 Python installs
fail for some of this tooling. This only matters if/when working directly on Windows-on-ARM
hardware; it doesn't block using the cloud device farm from a regular dev machine.

### 8.5 Validation runs completed so far
A compile + profile job has been run end-to-end through the workflow in §8.2 on a
**Snapdragon X Elite (SOC SC8380XP)** cloud device via `qai-hub`:

- Job ID: `j5687vxyg`; runtime QNN HTP with FP16 precision enabled.
- Compute unit for every node in the profiled graph: **NPU** (no CPU/GPU fallback).
- Results: `data/ai_hub_profile_probe.json`, full profiler log:
  `data/ai_hub_profile_probe_runtime.log`.
- Measured numbers and interpretation: [`PERFORMANCE.md`](PERFORMANCE.md).

Still open (tracked in `ROADMAP.md`): compiling/quantizing the actual production LLM and
embedding model — the completed job used a small ONNX probe model to validate the toolchain,
device access and NPU execution path.

---

## 9. Security & privacy design

- No document content, chunk text, or embeddings are transmitted over the network at runtime.
  Network access (to Qualcomm AI Hub, and one-time Ollama/Hugging Face model downloads) is a
  **build-time / first-run setup** concern, not part of the document flow.
- API tokens/secrets live in environment variables (`.env`, git-ignored) or the AI Hub client
  config outside the repo (`~/.qai_hub/client.ini`), never in source code or commit history.
- `data/samples/` (used for local testing) is git-ignored — real documents, even the developer's
  own, should never be committed.
- Vector store lifecycle defaults to session-scoped and **in-memory only** (§3.8): sessions live
  in the process that created them and are dropped on exit or via `qds clear`. No persistence is
  implemented, so no opt-in/time-boxing controls are needed yet; if persistence is added it must
  be opt-in, time-boxed, and paired with a visible "clear analyzed documents" user action.
- Real confidentiality guarantee for any persisted data rests on OS-level full-disk encryption,
  not application-level "secure delete."

---

## 10. Error handling & edge cases

| Case | Handling |
|---|---|
| Blurry/skewed photo, low OCR confidence | Flag affected regions and pages (FR-4) rather than silently explaining garbled text — see `src/ocr/confidence.py` |
| Missing Tesseract language pack | `auto` engine falls back to PaddleOCR; if no engine can handle the language, the failure is raised with the list of installed packs (`src/ocr/extract.py`) |
| Multi-column layout or embedded tables | Text is assembled per Tesseract/Paddle **block** with bounding boxes and classified as heading/paragraph/table/list/footer; explicit column re-ordering is a known limitation |
| Chunk still exceeds context window after structural split | Secondary split at sub-clause boundaries, then sentence boundaries, preserving as much structural integrity as possible (`_split_oversized_chunk`) |
| Question doesn't match any indexed content | Return an explicit "not addressed in this document" response (§5, step 4) rather than answering from general knowledge |
| OCR engine or LLM backend unavailable | Backend availability is checked (`is_available()`); tests and CI use stub/hash backends so the pipeline stays exercisable without models |
| AI Hub job fails or times out | Development flow must not silently proceed with an unvalidated model — treat as a blocking issue for that component |
| Model falls back to CPU instead of NPU | Surface this in profiling results and in the CLI's compute-unit indicator (FR-22) rather than hiding it |

---

## 11. Performance targets & measured results

Design target: a multi-page document processable end-to-end (OCR through overview) in a time
that is demo-able live, with retrieval-based Q&A feeling responsive.

Measured to date (see [`PERFORMANCE.md`](PERFORMANCE.md) for method and caveats):

| Measurement | Result |
|---|---|
| AI Hub profiled model, steady-state inference on Snapdragon X Elite | ≈0.16–0.18 ms (median of 100 runs), all nodes on NPU |
| AI Hub model load (cold / warm) | ≈2.58 s / ≈0.56 s |
| Local end-to-end `analyze` — 1-page sample, 5 chunks, Ollama `qwen2.5:0.5b` on CPU | ≈75–80 s (6 sequential LLM calls; dominated by generation, not OCR) |
| Local `ask` (RAG Q&A, warm) | ≈3–4 s |

The per-chunk simplification loop in `src/pipeline/run.py` is sequential today; chunks are
independent by design (§4, step 4), so parallelising that loop is the primary optimisation lever
before submission. This section is updated with new numbers as profiling data lands — not left as
an aspiration.

---

## 12. Testing strategy

- **Unit tests per module** (`tests/`, 83 tests) covering chunking, glossary, simplification,
  merge, embedding/index, QA, OCR confidence, lifecycle, models, compute-unit detection, CLI and
  disclaimer — run with stub/hash backends so no model or server is required.
- **Integration test** (`tests/test_integration.py`) exercises Document → chunk → glossary →
  simplify → embed → merge → Q&A without OCR, keeping the orchestration honest.
- **True end-to-end test** (`tests/test_e2e.py`) starts from a file on disk and runs every stage
  through `Pipeline.analyze_document` / `Pipeline.ask_question`. Default run uses stub backends;
  `QDS_E2E_REAL=1` switches to Ollama + fastembed.
- **Golden sample fixture** (`tests/fixtures/golden_sample.txt`) — a fixed, anonymized document
  whose facts (dates, amounts, defined terms) are asserted in tests, so changes can't silently
  alter structure detection or numeric fidelity (FR-11).
- **AI Hub profiling as a validation gate** — no model component is considered "done" until it has
  a completed AI Hub profiling job and passed the inference-accuracy check (§8.2, steps 3–4).

Details, commands and conventions: [`TESTING.md`](TESTING.md).

---

## 13. Future work / explicitly out of scope for this submission

See PRD §4 for the full non-goals list. Architecturally relevant follow-ups if the project
continues past the challenge: persistent opt-in document history, broader language coverage,
handwriting support, mobile port, and a packaged installer for end-user distribution.

---

## 14. Appendix — glossary of acronyms

| Term | Meaning |
|---|---|
| NPU | Neural Processing Unit — the Hexagon NPU on Snapdragon chips, used for efficient on-device model inference |
| RAG | Retrieval-Augmented Generation — answering a question by retrieving relevant source content first, then generating an answer grounded in it |
| OCR | Optical Character Recognition |
| QAIRT | Qualcomm AI Runtime — the runtime used to execute compiled models on Qualcomm hardware |
| AI Hub | Qualcomm AI Hub — Qualcomm's platform for compiling, quantizing, profiling, and validating models on real cloud-hosted Snapdragon devices |
