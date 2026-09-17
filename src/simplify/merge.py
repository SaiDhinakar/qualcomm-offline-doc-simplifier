"""Hierarchical Merge module.

Combines per-chunk explanations into one coherent document overview,
surfacing the most consequential points first.
"""

from __future__ import annotations

from src.models import Chunk
from src.simplify.llm import LLMBackend


def merge_explanations(
    chunks: list[Chunk],
    target_language: str,
    llm: LLMBackend,
    language_names: dict[str, str] | None = None,
) -> str:
    """Merge per-chunk explanations into a single document overview.

    Args:
        chunks: List of Chunk objects with populated 'explanation' field.
        target_language: ISO language code for output.
        llm: LLM backend for generating the merge.
        language_names: optional mapping of ISO codes to full language names.

    Returns:
        A coherent document overview explanation.
    """
    lang_names = language_names or {
        "hi": "Hindi", "ta": "Tamil", "kn": "Kannada", "te": "Telugu",
        "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "ml": "Malayalam",
        "pa": "Punjabi", "ur": "Urdu", "en": "English",
    }
    target_name = lang_names.get(target_language, target_language)

    # Collect all explanations in document order
    explanations: list[str] = []
    for chunk in sorted(chunks, key=lambda c: c.order_index):
        if chunk.explanation:
            section_hint = f"[Section: {chunk.section_id}] " if chunk.section_id else ""
            explanations.append(f"{section_hint}{chunk.explanation}")

    if not explanations:
        return "No explanations available for this document."

    combined = "\n\n".join(explanations)

    # If combined text is very short, just return it directly
    if len(combined) < 500:
        return combined

    prompt = (
        f"You are a document summarizer. Create a clear, organized overview "
        f"of this document in {target_name}.\n\n"
        f"The document has been broken into sections and each section has been "
        f"explained in simple language below.\n"
        f"Your job is to combine these into ONE coherent overview that:\n\n"
        f"1. Starts with the MOST IMPORTANT information "
        f"(obligations, risks, key dates/amounts, penalties)\n"
        f"2. Groups related points together even if they came from different sections\n"
        f"3. Maintains ALL specific numbers, dates, amounts, and percentages exactly as stated\n"
        f"4. Uses clear headings or bullet points for readability\n"
        f"5. Does NOT add any information not present in the original explanations\n"
        f"6. Does NOT provide legal or financial advice\n\n"
        f"Section explanations:\n{combined}\n\n"
        f"Provide the merged overview in {target_name}:"
    )

    return llm.generate(prompt, max_tokens=1024, temperature=0.3)
