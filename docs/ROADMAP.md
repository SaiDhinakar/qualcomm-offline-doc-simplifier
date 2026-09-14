# Roadmap

Submission deadline: **Sep 30, 2026, 11:59 PM IST**. Submissions can't be edited once made, so plan
to submit a day or two early, not at the deadline.

- [ ] **Sep 14–16 — Decisions & setup**
  - Choose OCR approach, local LLM, embedding model
  - Choose target vernacular language(s) for the demo
  - Set up Qualcomm AI Hub account, local Python env
  - Push this repo to GitHub

- [ ] **Sep 17–20 — Core pipeline (no LLM validation yet)**
  - OCR + layout-aware extraction working on sample docs
  - Structure-aware chunking
  - Glossary/defined-term extraction pass

- [ ] **Sep 21–24 — Simplification pipeline end-to-end**
  - Per-chunk simplification via local LLM (running anywhere, not yet Snapdragon-validated)
  - Hierarchical merge into one overview
  - Get a rough end-to-end demo working locally

- [ ] **Sep 25–27 — Qualcomm AI Hub validation + Q&A**
  - Compile/quantize/profile the LLM (and embedding model) via AI Hub
  - Confirm compute unit utilization (actually running on NPU)
  - Wire up local vector store + RAG Q&A
  - Implement vector store cleanup/session lifecycle

- [ ] **Sep 28–29 — Polish & submission materials**
  - Demo UI pass
  - Record a backup demo video (in case live demo has issues)
  - Write up documentation & presentation (judged criterion — don't leave this to the last hour)

- [ ] **Sep 29–30 — Submit**
  - Final review of all intake form fields (can't be edited after submission)
  - Submit before the deadline, not at it
