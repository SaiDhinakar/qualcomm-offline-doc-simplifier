# Roadmap

**Submission deadline: Sep 30, 2026, 11:59 PM IST.** Submissions cannot be edited once made —
plan to submit a day or two early, not at the deadline.

Maintainer: [SaiDhinakar](https://github.com/SaiDhinakar). Last updated: **Sep 24, 2026**.

Status legend: `[x]` done · `[~]` partially done · `[ ]` open.

---

## Phase 1 — Decisions & setup (Sep 14–16)

- [x] Choose OCR approach, local LLM, embedding model (now recorded in `PRD.md` §11)
- [x] Choose target vernacular language for the demo (Hindi default; 11 codes accepted)
- [x] Set up Qualcomm AI Hub account and local Python environment
- [x] Push repository to GitHub

## Phase 2 — Core pipeline without LLM (Sep 17–20)

- [x] OCR + layout-aware extraction on sample documents (Tesseract primary, Paddle fallback)
- [x] Structure-aware chunking with clause/section boundaries and metadata
- [x] Glossary / defined-term extraction pass
- [x] OCR confidence flagging (FR-4)

## Phase 3 — Simplification end-to-end (Sep 21–24)

- [x] Per-chunk simplification via local LLM (Ollama `qwen2.5:0.5b`)
- [x] Hierarchical merge into one overview
- [x] Local vector store + RAG Q&A (fastembed + cosine index)
- [x] Vector store session lifecycle and visible clear action (FR-17, FR-18)
- [x] CLI: `analyze`, `interactive`, `ask`, `clear`, `info` (FR-21) with compute-unit indicator (FR-22)
- [x] True end-to-end test from file to grounded answer (82 passing tests)
- [x] Real end-to-end demo run on a sample document (OCR → overview → grounded answer)

## Phase 4 — Qualcomm AI Hub validation (Sep 25–27)

- [~] Compile + profile via AI Hub on a real device — **done** (job `j5687vxyg`, Snapdragon X
      Elite, all nodes on NPU; see `data/ai_hub_profile_probe.json` and
      [`PERFORMANCE.md`](PERFORMANCE.md))
- [x] Confirm compute-unit utilization rather than assuming it — profiler shows NPU execution
- [ ] Compile + quantize the **production** LLM via AI Hub and re-profile
- [ ] Run the inference-accuracy check (quantized vs. reference output) for numeric fidelity
      (FR-11)
- [ ] Embedding model compile/profile (lower priority — currently a small ONNX model)

## Phase 5 — Polish & submission materials (Sep 28–29)

- [x] Documentation set: README, PRD, Architecture, Setup, CLI, Testing, Performance,
      Contributing (this pass, Sep 24)
- [ ] Demo pass: 3 consecutive clean dry runs of capture → explain → ask
- [ ] Demo UI polish (stretch — CLI is the baseline surface)
- [ ] Record a backup demo video in case the live demo has issues
- [ ] Presentation deck citing the profiling evidence
- [ ] Optimize per-chunk simplification (parallelise LLM calls) if timings allow
- [ ] Decide on a license for any post-challenge open-sourcing

## Phase 6 — Submit (Sep 29–30)

- [ ] Final review of all intake-form fields (cannot be edited after submission)
- [ ] Verify the repository state: no `.env`, no real documents in `data/samples/`
- [ ] Run the full gate one last time: `python -m pytest tests -q && ruff check src tests`
- [ ] Submit before the deadline, not at it

---

## Current standing (Sep 24, 2026)

| Area | State |
|---|---|
| Pipeline | Complete and working end-to-end |
| Tests | 82 passed, 1 skipped (opt-in real-backend e2e); ruff clean |
| On-device evidence | Probe model profiled on Snapdragon X Elite, NPU execution confirmed |
| Documentation | Complete set under `docs/` plus README |
| Open risk | Production LLM/embedding not yet compiled/quantized through AI Hub |
| Open risk | 10-page end-to-end timing not yet measured; LLM loop still sequential |
| Open risk | Demo reliability (3 clean dry runs) not yet demonstrated |

## Change control

Scope discipline for the remaining days: only items that affect a judged criterion
(technical implementation, use case/innovation, deployment/accessibility, presentation &
documentation) or that block the submission itself. New features — GUI, extra languages,
handwriting, persistence — stay out of scope for this submission (see `PRD.md` §4).
