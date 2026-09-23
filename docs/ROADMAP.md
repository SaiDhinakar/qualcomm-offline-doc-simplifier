# Roadmap

Submission deadline: **Sep 30, 2026, 11:59 PM IST**. Submissions can't be edited once made, so plan
to submit a day or two early, not at the deadline.

- [x] **Sep 14–16 — Decisions & setup**
  - Choose OCR approach, local LLM, embedding model
  - Choose target vernacular language(s) for the demo
  - Set up Qualcomm AI Hub account, local Python env
  - Push this repo to GitHub

- [x] **Sep 17–20 — Core pipeline (no LLM validation yet)**
  - OCR + layout-aware extraction working on sample docs
  - Structure-aware chunking
  - Glossary/defined-term extraction pass

- [x] **Sep 21–24 — Simplification pipeline end-to-end**
  - Per-chunk simplification via local LLM (Ollama `qwen2.5:0.5b`, running locally)
  - Hierarchical merge into one overview
  - Rough end-to-end demo working locally (real PDF → answer with grounded facts)

- [x] **Sep 25–27 — Qualcomm AI Hub validation + Q&A**
  - Compile/profile via AI Hub on **Snapdragon X Elite CRD** — done (NPU; see `data/ai_hub_profile_probe.json`)
  - Wire up local vector store + RAG Q&A — done (fastembed + cosine index)
  - Implement vector store cleanup/session lifecycle — done
  - Confirm compute unit utilization (actually running on NPU) — probe confirms NPU for compiled model
  - Quantize the LLM/embedding via AI Hub — still open for the real models (probe was a tiny ONNX)

- [ ] **Sep 28–29 — Polish & submission materials**
  - Demo UI pass
  - Record a backup demo video (in case live demo has issues)
  - Write up documentation & presentation (judged criterion — don't leave this to the last hour)

- [ ] **Sep 29–30 — Submit**
  - Final review of all intake form fields (can't be edited after submission)
  - Submit before the deadline, not at it
