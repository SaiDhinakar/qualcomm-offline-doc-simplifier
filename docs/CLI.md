# CLI Reference

`qds` is the command-line interface for the Qualcomm Doc Simplifier (FR-21, FR-22): one
continuous flow from document in, to explanation out, to follow-up questions answered.

Maintainer: [SaiDhinakar](https://github.com/SaiDhinakar).

---

## Invocation

```bash
qds <command> [options]            # installed console script
python -m src.cli <command> [...]  # equivalent, run from the repository root
qds --version                      # 0.1.0
qds --help / <command> --help      # generated help
```

| Command | Purpose |
|---|---|
| [`analyze`](#qds-analyze) | Analyze a document and print the overview, glossary and session ID |
| [`interactive`](#qds-interactive) | Analyze, then answer follow-up questions in the same session |
| [`ask`](#qds-ask) | Ask one question about an already-active session |
| [`clear`](#qds-clear) | Explicitly drop analyzed documents (visible clear action) |
| [`info`](#qds-info) | Compute units, active sessions, disclaimer |

---

## `qds analyze`

```text
qds analyze DOCUMENT_PATH [--lang CODE]
```

Runs the full pipeline (OCR → chunking → glossary → simplification → embedding/indexing →
hierarchical merge) and prints the overview.

| Option | Default | Description |
|---|---|---|
| `--lang`, `-l` | `hi` | Target language for the explanation: `hi`, `kn`, `ta`, `te`, `bn`, `mr`, `gu`, `ml`, `pa`, `ur`, `en` |

`DOCUMENT_PATH` must exist and be a `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp` or `.webp`
file.

Example output (real run against a one-page insurance policy sample):

```text
[NPU] Qualcomm Hexagon NPU
Analyzing: data/samples/sample_insurance_policy.pdf
Target language: en

⚠ OCR quality warnings:
OCR quality: 1 low-confidence area(s) found
  - [LOW OCR CONFIDENCE 26%] Page 1 @ (105, 755, 118, 772) (region): Very low confidence
    region — possibly blurred or skewed — "..."

============================================================
DOCUMENT OVERVIEW
============================================================
The insurance policy is issued by ABC Insurance Company to the Insured named in the
Schedule of this Policy. The Policy Period is the duration of coverage from
January 1, 2025 to December 31, 2025. The Sum Assured is $50,000 ...

============================================================
Glossary (3 terms)
============================================================
  Insured: the person named in the Schedule of this Policy
  Policy Period: the duration of coverage from the start date to the end date
  Sum Assured: the maximum amount payable under this Policy

Document ID: sample_insurance_policy
Chunks: 5

DISCLAIMER: This tool explains documents in plain language. It does NOT provide legal or
financial advice. For important decisions, consult a qualified professional.

To ask questions: qds ask sample_insurance_policy "<question>" --lang en
```

Notes:

- The compute-unit line at the top is the FR-22 on-device indication.
- The OCR quality block appears only when low-confidence regions were detected (FR-4).
- The glossary listing is capped at 20 terms in the output; the session holds all of them.

---

## `qds interactive`

```text
qds interactive DOCUMENT_PATH [--lang CODE]
```

Analyzes the document, prints the overview, then opens a prompt loop for follow-up questions.
Type `quit`, `exit` or `q` (or press Ctrl-D / Ctrl-C) to leave; the session is cleared on exit.

```text
============================================================
Ask questions (type 'quit' to exit):
============================================================

Your question: What is the premium and the late payment penalty?
A: The Premium for this policy is $1,200 per year. The late payment penalty is 5% per month
on the outstanding amount.
Sources: 2., 5., 3., 1., 4.

Your question: quit

Session cleared. Goodbye!
```

This is the recommended command for demos: analysis and Q&A happen in one process, so retrieval
always sees a live index (see [Session semantics](#session-semantics)).

---

## `qds ask`

```text
qds ask DOCUMENT_ID QUESTION [--lang CODE]
```

Answers a single question against an **already active** session in the current process.

```bash
qds ask sample_insurance_policy "What is the deductible?" --lang en
```

```text
[NPU] Qualcomm Hexagon NPU

Q: What is the deductible?
A: The deductible is $500 per claim ...

Sources: 3.
DISCLAIMER: ...
```

If no session exists for that ID:

```text
No active session for document 'sample_insurance_policy'.
Run 'qds analyze <path>' first.
```

…and the command exits with status `1`. Because sessions are not persisted between processes,
`qds ask` is intended for programmatic use (calling `Pipeline` from Python) or for shells where
analysis ran in the same process; for interactive use, prefer [`qds interactive`](#qds-interactive).

Answers carry a `status` of `answered` or `not_addressed` — when nothing in the document is
similar enough to the question (cosine similarity below the threshold), the engine replies that
the document does not appear to address it rather than guessing (FR-16).

---

## `qds clear`

```bash
qds clear --all      # drop every active session
qds clear            # prints usage hint — the flag is required
```

The visible "clear analyzed documents" action required by FR-18. Sessions are in-memory only,
so anything not explicitly cleared is also gone when the process exits (FR-17).

---

## `qds info`

```text
Qualcomm Doc Simplifier — System Info
========================================

Compute Units (FR-22):
  ✓ [NPU] Qualcomm Hexagon NPU
  ✓ [GPU] GPU acceleration
  ✓ [CPU] CPU (always available)

Preferred: [NPU] Qualcomm Hexagon NPU

Active sessions: 0

DISCLAIMER: This tool explains documents in plain language. It does NOT provide legal or
financial advice. For important decisions, consult a qualified professional.
```

Detection is ordered by preference (NPU → GPU → CPU). Availability of NPU/GPU is probed on the
host; it does **not** by itself prove the current run executed there — for hardware-level proof,
see the AI Hub profiling results in [`PERFORMANCE.md`](PERFORMANCE.md).

---

## Session semantics

| Property | Behaviour |
|---|---|
| Storage | In-memory only — nothing is written to disk |
| Scope | Per process; a session created by one `qds` invocation is invisible to the next |
| Lifetime | Until `qds clear --all`, an explicit `clear_session()` call, process exit, or (if configured) timeout expiry |
| Index | The vector index lives on the session and is dropped with it |

This is deliberate (FR-17, FR-18, FR-19): analyzing a document should leave no residue once the
view is closed.

---

## Environment variables

| Variable | Values | Default | Effect |
|---|---|---|---|
| `QDS_LLM` | `stub` \| `ollama` \| `llamacpp` | `stub` | LLM backend for simplification, merge and Q&A |
| `QDS_EMBED` | `hash` \| `fastembed` \| `sentence-transformers` | `hash` | Embedding backend for indexing and retrieval |
| `QDS_OCR` | `tesseract` \| `paddle` \| `auto` | `auto` | OCR engine selection |
| `QDS_OLLAMA_MODEL` | model name | `qwen2.5:0.5b` | Ollama model used when `QDS_LLM=ollama` |
| `QDS_LLAMA_PATH` | file path | — | `.gguf` model file used when `QDS_LLM=llamacpp` |
| `QDS_E2E_REAL` | `1` | unset | Opt-in real-backend end-to-end test (test suite only) |

```bash
QDS_LLM=ollama QDS_EMBED=fastembed qds analyze scan.png --lang hi
```

---

## Output conventions

- **Compute-unit indicator** — printed by every command that processes a document (FR-22).
- **Disclaimer** — printed with every explanation and answer; the product explains documents,
  it does not give legal or financial advice.
- **OCR warnings** — printed before the overview when confidence issues exist (FR-4).
- **Sources** — answers list the section IDs retrieved for them, so a reader can check the
  grounding.
