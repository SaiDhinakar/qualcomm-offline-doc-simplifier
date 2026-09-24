# Product Requirements Document (PRD)

| | |
|---|---|
| **Product** | Qualcomm Doc Simplifier |
| **Prepared for** | Snapdragon® AI Lab Build & Present Challenge (Qualcomm) |
| **Status** | Implemented — requirements met in the current build |
| **Version** | 0.2 |
| **Owner** | Solo participant (individual entry) |
| **Maintainer** | [SaiDhinakar](https://github.com/SaiDhinakar) |

---

## 1. Executive summary

Qualcomm Doc Simplifier is an **offline, on-device application** that turns dense, multi-page
legal and financial documents (insurance policies, rental agreements, loan paperwork, court
notices) into plain-language explanations in the user's own language — without the document ever
leaving the device. It is built to run on Snapdragon-powered HP PCs, using Qualcomm AI Hub to
compile, quantize, and validate every on-device model against real hardware.

The product exists to solve two problems at once: **document literacy** (legal/financial English
is genuinely hard to parse for a huge population) and **data privacy** (understanding your own
sensitive paperwork shouldn't require uploading it to a cloud service).

---

## 2. Problem statement

- Legal and financial documents in India are almost always written in formal English, full of
  domain jargon, cross-references, and clause numbering that's hard to follow even for fluent
  English readers.
- Existing "explain my document" tools are cloud-based: the document (often containing PII,
  financial account numbers, medical/legal history) is uploaded to a third-party server.
- Many people most affected by this problem are also the ones with the least reason to trust a
  cloud upload of their financial/legal documents to a stranger's server.
- There is no widely available tool that does this **entirely offline**, in **Indian vernacular
  languages**, running efficiently on consumer hardware.

---

## 3. Goals

### 3.1 Product goals
- G1: Let a user go from "photo of a multi-page document" to "plain-language explanation in their
  language" with no internet connection required at run time.
- G2: Support follow-up, specific questions about the document ("what's my premium?") with
  answers grounded in the actual document content, not hallucinated.
- G3: Never transmit document content off the device during normal use.
- G4: Run acceptably fast and light enough to be genuinely usable on a laptop, not just a proof of
  concept — validated on real Snapdragon hardware via Qualcomm AI Hub, not just claimed.

### 3.2 Challenge goals
- G5: Score well against the challenge's published evaluation criteria: **Technical
  Implementation**, **Application Use Case & Innovation**, **Deployment & Accessibility**, and
  **Presentation & Documentation** (see §9 for the mapping).
- G6: Produce a working, demoable build plus documentation and a presentation, submitted before
  Sep 30, 2026, 11:59 PM IST (submission cannot be edited afterward).

---

## 4. Non-goals / out of scope (for this challenge submission)

- Multi-user accounts, cloud sync, or team collaboration features.
- Legal advice or legally-binding interpretation — the product explains, it does not advise.
  This must be stated clearly in-product (a disclaimer), since misreading a legal document based
  on an AI explanation could cause real harm.
- Mobile app version (Android/iOS) — out of scope for this submission; desktop/laptop only.
- Support for every Indian language at launch — the demo will target a small set (to be decided)
  rather than claiming full coverage.
- Handwritten document support — typed/printed documents only, unless OCR testing shows
  handwriting recognition works well enough to include as a stretch feature.
- Persistent cross-session document history, by default (see §6.7 and ARCHITECTURE.md — vector
  store lifecycle is session-scoped unless explicitly enabled).

---

## 5. Target users & personas

**Primary persona — "Meena," 41, small business owner**
Received a commercial loan agreement from her bank. Comfortable with everyday spoken English but
the document's legal English is dense. Wants to know, in Kannada: what happens if she misses a
payment, what the total interest actually comes out to, and whether there's a penalty for early
repayment. Does not want to upload her loan documents to an unfamiliar website.

**Secondary persona — "Arjun," 26, first-time renter**
Just received a rental agreement PDF from his landlord's agent. Wants a quick plain-English (or
Hindi) summary of the deposit terms, notice period, and what counts as a lease violation, without
reading 8 pages of clauses. Wants to ask a couple of specific follow-up questions rather than
read the whole summary.

---

## 6. Features & functional requirements

Each requirement maps to a pipeline stage described in detail in `ARCHITECTURE.md`.

### 6.1 Document capture & OCR
- FR-1: User can provide a document as a photo (webcam capture) or an existing image/PDF file.
- FR-2: OCR extraction must be layout-aware — it must preserve page structure (headings, numbered
  clauses, paragraphs, tables) rather than producing a single flat text blob.
- FR-3: OCR must handle multi-page documents (tested up to at least 10 pages) as a single logical
  document, not independent pages.
- FR-4: The system should flag pages/sections where OCR confidence is low, so the explanation
  doesn't silently misrepresent unclear text.

### 6.2 Structure-aware chunking
- FR-5: The document must be split into chunks aligned to clause/section boundaries (not fixed
  token windows), so no individual chunk cuts a clause in half.
- FR-6: Each chunk must retain metadata: page number, section/clause identifier (if present), and
  its position in document order.

### 6.3 Glossary / defined-term extraction
- FR-7: The system performs a pass over all chunks to extract defined terms (e.g. "Insured",
  "Policy Period", "Sum Assured") into a local glossary table.
- FR-8: Later explanation steps must be able to reference this glossary instead of re-explaining
  the same term every time it appears, and must correctly resolve simple cross-references (e.g.
  "as defined in Section 3").

### 6.4 Per-chunk simplification
- FR-9: Each chunk is explained in plain language by a local LLM, in the user's selected target
  language.
- FR-10: The explanation must be understandable to someone without legal/financial background,
  while preserving the actual meaning/obligations of the clause (no oversimplification that
  changes the substance).
- FR-11: Numeric details (amounts, dates, percentages) must be preserved exactly as written in
  the source — this is a correctness-critical requirement, not just a style preference.

### 6.5 Hierarchical merge (overview)
- FR-12: After per-chunk simplification, the system produces one coherent overview of the whole
  document (not just a concatenation of chunk explanations).
- FR-13: The overview should surface the most consequential points first (obligations,
  penalties/risks, key dates/amounts) rather than following strict document order if that buries
  important information.

### 6.6 On-device question answering (RAG)
- FR-14: User can ask a free-text question about the document after the initial explanation.
- FR-15: The system retrieves the most relevant chunk(s) from the local index and answers using
  only that retrieved content — answers must be grounded in the document, not fabricated.
- FR-16: If no chunk is relevant to the question, the system must say so rather than guessing.

### 6.7 Vector store & data lifecycle
- FR-17: The local vector index (embeddings + chunk text) is session-scoped by default — cleared
  when the document view is closed.
- FR-18: If persistence is added as a later enhancement, it must be opt-in, time-boxed (e.g.
  auto-expire), and pair with a visible "clear analyzed documents" user action.
- FR-19: No document content is written anywhere outside the local device at any point in the
  runtime flow.

### 6.8 Language support
- FR-20: At minimum, support one Indian vernacular language end-to-end for the demo — **resolved:
  Hindi (`hi`) is the default output language**, with `--lang` accepting `kn`, `ta`, `te`, `bn`,
  `mr`, `gu`, `ml`, `pa`, `ur`, `en` as well. Additional languages beyond this set are a stretch
  goal, not a baseline requirement.

### 6.9 UI / demo surface
- FR-21: A minimal interface (CLI acceptable for MVP; a simple UI preferred for the live demo)
  that lets a judge see: document in → explanation out → a follow-up question answered — in one
  continuous flow.
- FR-22: The UI/CLI must visibly indicate when processing is happening on-device (e.g. showing
  which compute unit — NPU/GPU/CPU — a step is running on), since "genuinely on-device" is a core
  claim that should be demonstrable, not just asserted.

### 6.10 Implementation status

All of FR-1 through FR-22 are implemented in the current build. Where a requirement defers
something to a later stage, that is called out rather than silently dropped: FR-18's opt-in
persistence controls exist only as the visible `qds clear` action, because no persistence is
implemented yet (§11). Coverage is asserted by the test suite ([`TESTING.md`](TESTING.md)) and
exercised end-to-end by `tests/test_e2e.py`.

---

## 7. Non-functional requirements

| Category | Requirement |
|---|---|
| **Privacy** | No document content leaves the device during normal runtime use. |
| **Offline operation** | Core flow (capture → explain → ask questions) must work with no internet connection. (Model compilation/validation via Qualcomm AI Hub happens ahead of time, during development — not at runtime.) |
| **Performance** | Target: process a 10-page document end-to-end (OCR through overview) in a time that's demo-able live — first measurements recorded in [`PERFORMANCE.md`](PERFORMANCE.md); optimization of the per-chunk LLM loop still open. |
| **Accuracy** | Numeric/date/amount details must not be altered or hallucinated in explanations. |
| **Hardware validation** | Every on-device model component must be compiled, quantized, and profiled via Qualcomm AI Hub on a real Snapdragon device before being considered "done" — not just tested on a dev laptop's CPU. |
| **Resilience** | Pipeline should degrade gracefully on messy input (skewed photo, partial OCR failure) rather than crashing outright. |

---

## 8. Constraints & assumptions

This section records the constraints the design was written under, and where each stands now:

- **Available resources at project start: a Qualcomm AI Hub API token, and nothing else.** No
  physical Snapdragon/HP hardware, no pre-existing codebase, no pre-selected models. **Still
  true today:** no physical Snapdragon hardware is in hand, so hardware validation continues to
  run through AI Hub cloud device jobs.
- **Implication for architecture:** all development happens on whatever machine is available
  (any CPU/OS); all Snapdragon-specific compilation, quantization, and profiling happens via
  Qualcomm AI Hub's cloud-hosted device jobs, not on physical hardware in hand. This is a
  supported, intended use of AI Hub (see ARCHITECTURE.md §8) — not a workaround.
- The AI Hub API token must never be committed to the repository. It is provided via environment
  variable / local `qai-hub` CLI configuration (see `.env.example` and `SETUP.md`), and `.env` is
  git-ignored.
- Team size is 1 (individual participation, per challenge eligibility rules) — scope must be
  realistic for a solo build within the submission window.
- Model choices (OCR, LLM, embedding model) **have been finalized** — see §11, Resolved
  decisions. Requirements above were written to be model-agnostic, which is why they held across
  the swap.
- Qualcomm AI Hub job quotas/limits for the tier available under this token were checked early;
  a compile + profile job has completed (ARCHITECTURE §8.5), so validation work is not blocked.

---

## 9. Mapping to challenge evaluation criteria

| Evaluation criterion | How this product addresses it |
|---|---|
| **Technical Implementation** | Multi-stage on-device pipeline (OCR → structure-aware chunking → glossary → per-chunk LLM simplification → local embedding/retrieval → hierarchical merge → RAG Q&A), fully implemented and covered by an 83-test suite; on-device hardware validation via Qualcomm AI Hub cloud device jobs, with a completed compile + profile run on a Snapdragon X Elite showing NPU execution (ARCHITECTURE §8.5). |
| **Application Use Case & Innovation** | Addresses a real, widely-felt problem (document literacy) with a genuinely differentiated approach (fully offline, privacy-preserving, vernacular-language) rather than another generic AI chatbot. |
| **Deployment & Accessibility** | Runs fully offline on consumer Snapdragon-powered HP hardware; explanations in vernacular languages directly serve accessibility for non-native-English speakers; no cloud dependency or subscription needed to use it. |
| **Presentation & Documentation** | The documentation set (`README.md` plus `docs/` — PRD, Architecture, Setup, CLI, Testing, Performance, Roadmap, Contributing) gives a complete account of the problem, design, build and measurements; the live demo is designed (FR-21, FR-22) specifically to make the on-device claim visibly provable, not just stated. |

---

## 10. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| No physical Snapdragon hardware in hand | Can't do a live on-laptop demo without borrowed/available hardware | Rely on Qualcomm AI Hub's cloud-hosted device profiling as validated proof; show profiling dashboard/metrics in the presentation as evidence; seek hardware access if available before the deadline |
| OCR accuracy on vernacular scripts / poor photo quality | Wrong explanations from bad input text | OCR-confidence flagging (FR-4) implemented in `src/ocr/confidence.py` and surfaced by the CLI; Tesseract language packs + PaddleOCR fallback cover missing scripts; test on real sample documents, not synthetic ones |
| LLM quantization degrading numeric accuracy | Wrong amounts/dates in explanations — a correctness-critical failure | Explicit inference-job accuracy validation step in AI Hub workflow (compare quantized vs. reference output) before accepting a model |
| AI Hub job quota/turnaround limits | Validation work blocked or slow near the deadline | Confirm quota early (Roadmap Sep 14–16 phase); don't leave hardware validation to the last days |
| Scope too large for solo/limited timeframe | Incomplete submission | Roadmap phases prioritize a working end-to-end flow before polish; language support and UI polish are explicitly listed as stretch, not baseline (§6.8, §6.9) |
| Legal/financial explanations perceived as advice | Misuse risk / trust issue with judges | In-product disclaimer printed with every explanation and answer (`src/disclaimer.py`) |

---

## 11. Resolved decisions

These were open at draft time (v0.1). All are now decided and reflected in the code and in
`ARCHITECTURE.md` §7:

| Decision | Resolution |
|---|---|
| OCR approach/model | Tesseract 5.5.3 + PyMuPDF primary; PaddleOCR 3.x fallback for missing language packs; engine selectable via `QDS_OCR` (`tesseract` \| `paddle` \| `auto`) |
| Local LLM (simplification + merge + Q&A) | Ollama `qwen2.5:0.5b` via HTTP (`QDS_LLM=ollama`); `llama-cpp-python` retained as an alternative; deterministic `StubLLM` for tests/CI |
| Embedding model | fastembed `BAAI/bge-small-en-v1.5` (384-d, ONNX, no torch) via `QDS_EMBED=fastembed`; deterministic hash backend for tests/CI |
| Target language(s) for the demo | Hindi default (`--lang hi`); `kn`, `ta`, `te`, `bn`, `mr`, `gu`, `ml`, `pa`, `ur`, `en` accepted |
| UI approach (CLI-only vs. minimal GUI) | Click-based CLI (`qds`) for this submission; minimal GUI remains a stretch item |
| Persistence beyond session-scope | Not implemented — sessions are in-memory and process-scoped, with `qds clear` as the visible clear action (FR-17, FR-18). Persistence would be a later, opt-in feature |

---

## 12. Success metrics

Status of each metric against the current build:

| Metric | Target | Status |
|---|---|---|
| **Functional completeness** | All FRs in §6.1–§6.6 working end-to-end on at least one real sample document, in at least one target language | **Met** — full flow runs from file → overview → grounded answer (`tests/test_e2e.py`) |
| **Validated on-device** | Every model component shows a completed Qualcomm AI Hub profiling + inference-accuracy job, with results documented | **Partial** — compile + profile job `j5687vxyg` completed on Snapdragon X Elite with NPU execution (`data/ai_hub_profile_probe.json`); production LLM/embedding compile still open (Roadmap) |
| **Numeric fidelity** | 0 altered/hallucinated numeric values (amounts, dates, percentages) across demo documents | **Guarded** — golden-sample tests assert key figures; prompt rules require verbatim numbers (FR-11); ongoing manual verification on demo documents |
| **Demo reliability** | Live flow (capture → explain → ask) completes without manual intervention on 3 consecutive dry runs | **Pending** — scheduled for the polish phase (Roadmap, Sep 28–29) |
| **Documentation completeness** | PRD, Architecture, Setup and Roadmap reflect the actual final build | **Met** — full documentation set under `docs/` (index: [`README.md`](README.md)) kept in sync with the code |
