# Qualcomm Offline Doc Simplifier

**Offline vernacular legal & financial document simplifier — built for Snapdragon-powered HP PCs.**

> Submitted to the [Snapdragon® AI Lab Build & Present Challenge](https://unstop.com) (Qualcomm)

## The problem

Insurance policies, rental agreements, loan documents, and court notices are written in dense
English legalese. For a huge number of people in India, that's a second (or third) language
barrier on top of an already confusing document. Uploading these documents to a cloud AI service
also means sending sensitive financial/legal/personal data off-device — not something most people
should have to accept just to understand their own paperwork.

## What this does

Point your laptop's camera (or load a scanned file) at a multi-page document. DastaavezAI:

1. Reads it (OCR, layout-aware)
2. Breaks it into meaningful pieces (clauses/sections, not arbitrary chunks)
3. Explains each piece in plain language, in your language
4. Gives you one coherent overview of the whole document
5. Lets you ask follow-up questions ("what's my premium?", "when does this expire?") and get
   grounded answers pulled from the actual document

**Everything runs on-device.** No document content leaves the laptop. Validated to run on the
Hexagon NPU / Adreno GPU via Qualcomm AI Hub.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full pipeline design (OCR → chunking →
per-chunk simplification → embedding/indexing → hierarchical merge → on-device Q&A → vector store
lifecycle).

## Getting started

See [`docs/SETUP.md`](docs/SETUP.md) for prerequisites and environment setup, and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the build plan against the Sep 30, 2026 submission
deadline.

```bash
git clone <your-repo-url>
cd dastaavez-ai
conda create -n dastaavez python=3.10
conda activate dastaavez
pip install -r requirements.txt
```

## Project status

🚧 Early scaffold — see [`docs/ROADMAP.md`](docs/ROADMAP.md) for current phase.

## Repo layout

```
dastaavez-ai/
├── src/
│   ├── ocr/            # document capture + layout-aware text extraction
│   ├── chunking/        # structure-aware splitting into clauses/sections
│   ├── glossary/        # defined-term extraction pass
│   ├── simplify/        # per-chunk plain-language explanation (local LLM)
│   ├── embed_index/     # local embedding + vector store for retrieval
│   ├── qa/               # RAG-based question answering over the document
│   └── pipeline/         # orchestration tying the stages together
├── data/samples/         # sample documents for local testing (gitignored — don't commit real docs)
├── notebooks/             # exploration / model evaluation notebooks
├── tests/
└── docs/
    ├── ARCHITECTURE.md
    ├── SETUP.md
    └── ROADMAP.md
```

## Note on eligibility & ownership

Per the challenge rules, this submission must be solely owned by the participant, and a single
submission per participant is permitted. Keep this repo as your one canonical build.

## License

TBD — not required for submission; add one later if you open-source this beyond the challenge.
