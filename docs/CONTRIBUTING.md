# Contributing

Guidelines for working on the Qualcomm Offline Doc Simplifier.

Maintainer and sole contributor: **[SaiDhinakar](https://github.com/SaiDhinakar)**. This
repository is an individual entry for the Snapdragon® AI Lab Build & Present Challenge, so until
the challenge closes it must remain solely owned by the participant (see the README eligibility
note). Feedback, issue reports and post-challenge contributions are welcome.

---

## Before you start

1. Follow [`SETUP.md`](SETUP.md) to install the project and system dependencies.
2. Confirm the baseline is green:

   ```bash
   python -m pytest tests -q     # 82 passed, 1 skipped
   ruff check src tests          # clean
   ```

3. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the stages fit together, and
   [`TESTING.md`](TESTING.md) for test conventions.

---

## Workflow

```bash
git checkout -b <type>/<short-description>
# make changes, add tests
python -m pytest tests -q && ruff check src tests
git commit -m "<type>: <what and why>"
```

**Commit messages** follow the existing history: a lowercase type prefix and an imperative
subject — `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `perf:`, `chore:`. Include the
reason in the body when it isn't obvious from the diff.

**Keep changes focused.** One concern per commit or PR; unrelated cleanups go in their own
commit so they can be reviewed (or reverted) independently.

---

## Code conventions

- **Style is enforced by Ruff** — `E`, `F`, `I`, `N`, `W`, `UP`, line length 100
  (configuration in `pyproject.toml`). Run `ruff check src tests` before every commit.
- **Type annotations** on new functions, including return types. `mypy` is configured
  (`disallow_untyped_defs`); the repository does not yet pass a full mypy run, so treat
  annotations as a standard for new code rather than a green-CI gate.
- **Docstrings** on public functions and classes: one-line summary, then `Args:`/`Returns:`
  where non-obvious. Existing modules (`src/pipeline/run.py`, `src/qa/engine.py`) are the
  reference for tone.
- **Follow the existing structure.** Each pipeline stage lives in its own package under `src/`
  with a narrow interface; `src/pipeline/run.py` orchestrates and must not grow stage-specific
  logic.
- **No comments that restate the code.** Use a comment only for the non-obvious *why*.
- **Requirement IDs.** Reference FRs (`FR-4`, `FR-22`, …) from `PRD.md` in docstrings, tests and
  commit messages when the change implements one — that traceability is part of the deliverable.

### Adding a backend

OCR, LLM and embedding engines are pluggable by design. To add one:

1. Implement the relevant interface (`LLMBackend` in `src/simplify/llm.py`,
   `EmbeddingBackend` in `src/embed_index/embedding.py`, or an OCR path in `src/ocr/extract.py`).
2. Register it in the corresponding factory (`get_llm_backend`, `get_embedding_backend`, engine
   selection).
3. Expose it through a `QDS_*` environment variable and document it in `SETUP.md` and
   `CLI.md`.
4. Make sure the **default test suite still runs without it** — stubs must remain the default.

---

## Tests

- Every bug fix gets a test that fails before the fix.
- Every new behaviour gets coverage in the module's existing test file.
- The default suite must not require network, models or secrets.
- Numeric, date and amount assertions must be exact (FR-11).
- See [`TESTING.md`](TESTING.md) for the file-by-file map and the requirement-to-test table.

---

## Documentation

Documentation is a judged criterion, so it is part of "done", not a follow-up:

- User-visible behaviour change → update [`CLI.md`](CLI.md) (and the README usage table if the
  command surface changed).
- Dependency, backend or environment change → update [`SETUP.md`](SETUP.md).
- Pipeline/design change → update [`ARCHITECTURE.md`](ARCHITECTURE.md).
- New requirement or changed scope → update [`PRD.md`](PRD.md).
- Measured numbers → append to [`PERFORMANCE.md`](PERFORMANCE.md), never overwrite old ones.
- Status/schedule change → update [`ROADMAP.md`](ROADMAP.md).

Style rules for documentation: no emojis, no marketing hyperbole, tables for reference material,
every claim either linked to evidence or marked as a target. If something is unfinished, say so —
TBD is more credible than a quiet omission.

---

## Privacy and security rules (non-negotiable)

- Never commit `.env`, API tokens, or anything under `~/.qai_hub/`.
- Never commit real documents. `data/samples/` is git-ignored for this reason; use synthetic or
  anonymized fixtures.
- Do not add any runtime path that transmits document content off the device. Network use is
  limited to build-time validation and one-time model downloads.
- Do not log document text, chunk contents or embeddings to stdout/files in library code.

---

## Review expectations

Every contribution (including your own) should answer, before it is merged:

1. Do the tests pass, and are there tests for the new behaviour?
2. Is `ruff check src tests` clean?
3. Is the documentation updated to match?
4. Does anything leave the device, the process, or the repository that shouldn't?
5. Is the claim made in the diff actually true on the target hardware — or is it marked as a
   target rather than a result?

---

## Reporting problems

Open an issue with: what you ran, what you expected, what happened, your OS/Python version and
the `QDS_*` backend settings. For pipeline output problems, attach the OCR quality report
printed by `qds analyze` and the document type (with personal data removed).
