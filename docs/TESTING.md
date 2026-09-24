# Testing

How the test suite is organised, how to run it, and the conventions to follow when adding
coverage.

Maintainer: [SaiDhinakar](https://github.com/SaiDhinakar).

---

## Quick start

```bash
source .venv/bin/activate
python -m pytest tests -q          # 82 passed, 1 skipped (~5 s, stub/hash backends)
python -m pytest tests -v          # verbose, one line per test
python -m pytest tests/test_qa.py -q            # a single module
ruff check src tests               # lint — must be clean before committing
```

The default run uses the **stub LLM** and **hash embedding** backends: no model download, no
Ollama server, no network. That is what makes the suite fast enough to run on every change.

---

## Test layout

| File | Covers |
|---|---|
| `test_models.py` | Pydantic data models — `Document`, `Page`, `Region`, `Chunk`, `GlossaryEntry`, `DocumentSession` validation and session clearing |
| `test_chunking.py` | Section-boundary detection, section IDs, oversized-chunk fallback, chunk metadata and ordering |
| `test_glossary.py` | Defined-term extraction, cleaning, Unicode quote handling, invalid-term rejection |
| `test_simplify.py` | Per-chunk simplification, glossary context, numeric preservation rules |
| `test_merge.py` | Hierarchical merge into one overview; empty/short explanation handling |
| `test_embed_index.py` | Embedding backends (hash), index add/search/cosine ranking, chunk lookup |
| `test_qa.py` | Retrieval-grounded answers, similarity threshold refusal (`not_addressed`), source sections |
| `test_lifecycle.py` | Session create/get/clear/clear-all, expiry, in-memory scoping |
| `test_pipeline.py` | `Pipeline.analyze_document` / `ask_question` orchestration |
| `test_pipeline_stub.py` | Original pipeline stub behaviour |
| `test_confidence.py` | OCR quality reports, low-confidence flagging, summaries (FR-4) |
| `test_compute.py` | Compute-unit detection and indicator strings (FR-22) |
| `test_disclaimer.py` | Disclaimer presence and language fallback |
| `test_cli.py` | CLI commands and error paths through Click's test runner |
| `test_integration.py` | Full flow without OCR: Document → chunk → glossary → simplify → embed → merge → Q&A |
| `test_e2e.py` | **True end-to-end**: file on disk → OCR → every stage → answer |

Fixture: `tests/fixtures/golden_sample.txt` — an anonymized insurance-policy sample whose facts
(dates, amounts, defined terms) are mirrored into `tests/test_e2e.py` and asserted there. It is
the regression baseline for structure detection and numeric fidelity (FR-11).

---

## Test modes

### Default (stub) run

```bash
python -m pytest tests -q
```

`test_e2e.py` runs the whole pipeline with `StubLLM` + `HashEmbeddingBackend`, so the file → OCR
→ answer path is genuinely exercised even without models.

### Real-backend run

```bash
# requires: Ollama serving qwen2.5:0.5b, fastembed installed
QDS_E2E_REAL=1 python -m pytest tests/test_e2e.py -v
```

The one skipped test in the default run is exactly this opt-in case — it is skipped, not
silently passed.

### Manual smoke test

```bash
qds info
qds analyze path/to/document.pdf --lang en
qds interactive path/to/document.pdf --lang en     # then ask questions in the prompt
```

---

## Conventions

1. **Every bug fix gets a test.** Reproduce it in `tests/` first where practical, then fix.
2. **Every new pipeline behaviour gets a test** in the module's existing test file — add a file
   only for a genuinely new module.
3. **No network, no models in the default suite.** Anything requiring Ollama, fastembed downloads
   or an AI Hub token must be opt-in via an environment variable, exactly as `QDS_E2E_REAL` is.
4. **No real documents.** Test inputs must be synthetic or anonymized; `data/samples/` is
   git-ignored for that reason.
5. **Numeric assertions matter.** Where a test touches amounts, dates or percentages, assert the
   exact value — that is the regression net for FR-11.
6. **Lint is part of done.** `ruff check src tests` must pass (configuration in
   `pyproject.toml`: `E`, `F`, `I`, `N`, `W`, `UP`, line length 100).

### Type checking

`mypy` is configured in `pyproject.toml` (`disallow_untyped_defs`, Python 3.10) and currently
reports known findings across `src/`. Treat new code as type-annotated, but be aware that a
clean full-repo mypy run is not yet part of the gate — `ruff` is.

---

## Mapping tests to requirements

| Requirement | Where it is covered |
|---|---|
| FR-4 OCR confidence flagging | `test_confidence.py`, `test_cli.py` |
| FR-5 / FR-6 structure-aware chunking with metadata | `test_chunking.py` |
| FR-7 / FR-8 glossary extraction and resolution | `test_glossary.py` |
| FR-9 / FR-10 / FR-11 simplification and numeric fidelity | `test_simplify.py`, golden-sample assertions |
| FR-12 / FR-13 hierarchical overview | `test_merge.py` |
| FR-14 / FR-15 / FR-16 grounded Q&A and refusal | `test_qa.py`, `test_e2e.py` |
| FR-17 / FR-18 session lifecycle and clear action | `test_lifecycle.py`, `test_cli.py` |
| FR-19 no off-device writes | Design (in-memory sessions) + `test_lifecycle.py` |
| FR-21 CLI flow | `test_cli.py`, `test_e2e.py` |
| FR-22 compute-unit indication | `test_compute.py`, `test_cli.py` |

---

## Continuous integration

No hosted CI is configured yet. The local gate before any commit is:

```bash
python -m pytest tests -q && ruff check src tests
```

Adding a GitHub Actions workflow that runs exactly those two commands is a low-cost,
high-value follow-up (see [`CONTRIBUTING.md`](CONTRIBUTING.md)).
