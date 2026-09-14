# Architecture

## Why not just feed the whole document to the LLM?

A 10-page legal/financial document is far bigger than the context window an on-device quantized
LLM can hold while staying fast and accurate on an NPU. So instead of one giant prompt, the
document goes through a pipeline: read → split → explain piece-by-piece → merge → retrieve on
demand.

## Pipeline stages

### 1. Capture & OCR
Photo or scanned file → text, using a layout-aware OCR step that preserves structure (headings,
numbered clauses, tables) rather than flattening everything into raw text. Structure is what makes
later stages (chunking, cross-references) work correctly.

### 2. Structure-aware chunking
Split the document along its natural boundaries — clauses, sections, table rows — instead of
fixed token windows. A 10-page policy might become ~30–50 chunks, each small enough to comfortably
fit the local LLM's context window. This avoids severing a clause mid-sentence, which is where
naive fixed-size chunking breaks legal/financial text.

### 3. Glossary pass (defined terms)
A quick first scan across all chunks pulls out defined terms (e.g. "Insured", "Policy Period",
"Sum Assured") into a small local lookup table. Later stages can reference this instead of
re-explaining the same definition every time it's mentioned — this is what handles
cross-references ("as defined in Section 3") without needing the whole document in context.

### 4. Per-chunk simplification (local LLM)
The model runs once per chunk, explaining just that piece in plain language, in the target Indian
language. Cheap, parallelizable, and each call stays well within context limits.

### 5. Embed & index locally
While simplifying, generate a small embedding vector per chunk using a lightweight on-device
embedding model. At this scale (~30–50 vectors for a 10-page doc), a simple in-memory array with
brute-force cosine similarity is enough — no need for a heavy vector database.

### 6. Hierarchical merge
A second LLM pass combines the chunk-level simplified summaries (not the raw text) into one
coherent overview of the whole document. Because it works over already-simplified summaries
instead of raw pages, this stays within context even for a document that started out large.

### 7. On-device Q&A (RAG)
When the user asks a specific question, embed the question, retrieve the top few relevant chunks
from the local index, and feed just those (plus the question) to the LLM for a grounded answer —
no need to reprocess the whole document per question.

## Vector store lifecycle

Since this handles sensitive financial/legal data, the vector store is treated as ephemeral by
default:

- Default: **session-only**, held in memory, cleared when the document view closes.
- If persistence is added later (so users can ask follow-up questions across sessions), it should
  be opt-in, time-boxed (e.g. auto-expire after 24h), and paired with an explicit "clear analyzed
  documents" action in the UI.
- The raw chunk text (not just the vectors) must be cleared in the same step — that's the actually
  sensitive part.
- Real privacy guarantee rests on OS-level full-disk encryption (BitLocker) being enabled, not on
  "secure delete" tricks — SSD wear leveling makes overwrite-based deletion unreliable.

## Validation on Qualcomm hardware

- **LLM inference**: validate via Qualcomm AI Hub GenieX (built for running LLMs on Hexagon
  NPU / Adreno GPU / CPU via llama.cpp or QAIRT).
- **Custom/fine-tuned components** (e.g. a custom embedding or OCR model): validate via Qualcomm AI
  Hub Workbench — compile → quantize → profile on a real cloud-hosted device → check numerical
  accuracy against the original framework output → download the validated model.
- Track **compute unit utilization** in profiling results specifically — this confirms whether a
  component is actually running on the Hexagon NPU or silently falling back to CPU, which matters
  for the "offline, low battery cost" pitch.

## Open decisions (fill in as we choose models)

| Component | Candidate model(s) | Status |
|---|---|---|
| OCR | TBD | Not yet chosen |
| Local LLM (simplification + merge + Q&A) | TBD | Not yet chosen |
| Embedding model | TBD | Not yet chosen |
| Target languages | TBD | Not yet chosen |
