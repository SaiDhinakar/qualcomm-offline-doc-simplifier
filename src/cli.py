"""Qualcomm Doc Simplifier CLI (FR-21, FR-22).

Provides an interactive demo flow:
  document in → explanation out → follow-up question answered

Usage:
  qds analyze <path> [--lang hi]
  qds ask <document-id> "<question>" [--lang hi]
  qds interactive <path> [--lang hi]
  qds clear [--all]
  qds info

Or run as module: python -m src.cli <command>
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from src.disclaimer import get_disclaimer
from src.pipeline.run import Pipeline
from src.utils.compute import detect_compute_units, get_compute_unit_indicator


def _get_pipeline() -> Pipeline:
    return Pipeline()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Qualcomm Doc Simplifier — offline, on-device document explanations."""


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option("--lang", "-l", default="hi", help="Target language code (hi, kn, ta, en, ...)")
def analyze(document_path: Path, lang: str) -> None:
    """Analyze a document (image or PDF) and print the overview."""
    pipeline = _get_pipeline()

    click.echo(f"\n{get_compute_unit_indicator()}")  # FR-22
    click.echo(f"Analyzing: {document_path}")
    click.echo(f"Target language: {lang}")

    session = pipeline.analyze_document(document_path, target_language=lang)

    # FR-4: Surface OCR confidence flags
    if session.ocr_report is not None and session.ocr_report.has_issues:
        click.echo("\n⚠ OCR quality warnings:")
        click.echo(session.ocr_report.summary())

    click.echo(f"\n{'='*60}")
    click.echo("DOCUMENT OVERVIEW")
    click.echo(f"{'='*60}")
    click.echo(session.overview)

    click.echo(f"\n{'='*60}")
    click.echo(f"Glossary ({len(session.glossary)} terms)")
    click.echo(f"{'='*60}")
    for entry in session.glossary[:20]:
        click.echo(f"  {entry.term}: {entry.definition}")

    click.echo(f"\nDocument ID: {session.document_id}")
    click.echo(f"Chunks: {len(session.chunks)}")
    click.echo(f"\n{get_disclaimer(lang)}")  # Disclaimer
    click.echo(f"\nTo ask questions: qds ask {session.document_id} \"<question>\" --lang {lang}")


@main.command()
@click.argument("document_id")
@click.argument("question")
@click.option("--lang", "-l", default="hi", help="Target language code")
def ask(document_id: str, question: str, lang: str) -> None:
    """Ask a question about an analyzed document."""
    pipeline = _get_pipeline()
    session = pipeline.get_session(document_id)

    if session is None:
        click.echo(f"No active session for document '{document_id}'.")
        click.echo("Run 'qds analyze <path>' first.")
        sys.exit(1)

    click.echo(f"\n{get_compute_unit_indicator()}")  # FR-22
    result = pipeline.ask_question(session, question, target_language=lang)

    click.echo(f"\nQ: {question}")
    click.echo(f"A: {result['answer']}")
    if result.get("source_sections"):
        click.echo(f"\nSources: {', '.join(result['source_sections'])}")
    click.echo(f"\n{get_disclaimer(lang)}")


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option("--lang", "-l", default="hi", help="Target language code")
def interactive(document_path: Path, lang: str) -> None:
    """Run the full interactive demo: analyze → overview → ask questions."""
    pipeline = _get_pipeline()

    click.echo(f"\n{get_compute_unit_indicator()}")  # FR-22
    click.echo(f"Analyzing: {document_path}")
    session = pipeline.analyze_document(document_path, target_language=lang)

    # FR-4: OCR confidence flags
    if session.ocr_report is not None and session.ocr_report.has_issues:
        click.echo("\n⚠ OCR quality warnings:")
        click.echo(session.ocr_report.summary())

    click.echo(f"\n{'='*60}")
    click.echo("DOCUMENT OVERVIEW")
    click.echo(f"{'='*60}")
    click.echo(session.overview)
    click.echo(f"\n{get_disclaimer(lang)}")

    # Interactive Q&A loop
    click.echo(f"\n{'='*60}")
    click.echo("Ask questions (type 'quit' to exit):")
    click.echo(f"{'='*60}")

    while True:
        try:
            question = click.prompt("\nYour question", type=str)
        except (EOFError, KeyboardInterrupt):
            break
        if question.strip().lower() in ("quit", "exit", "q"):
            break
        if not question.strip():
            continue

        result = pipeline.ask_question(session, question, target_language=lang)
        click.echo(f"A: {result['answer']}")
        if result.get("source_sections"):
            click.echo(f"Sources: {', '.join(result['source_sections'])}")

    pipeline.clear_session(session.document_id)
    click.echo("\nSession cleared. Goodbye!")


@main.command()
@click.option("--all", "clear_all", is_flag=True, help="Clear all sessions")
def clear(clear_all: bool) -> None:
    """Clear analyzed documents (visible 'clear' action — FR-18)."""
    pipeline = _get_pipeline()
    if clear_all:
        count = pipeline.clear_all_sessions()
        click.echo(f"Cleared {count} session(s).")
    else:
        click.echo("Use --all to clear all sessions.")


@main.command()
def info() -> None:
    """Show system info: compute units, backends, session count."""
    pipeline = _get_pipeline()

    click.echo("Qualcomm Doc Simplifier — System Info")
    click.echo("=" * 40)

    # FR-22: Compute units
    click.echo("\nCompute Units (FR-22):")
    for info_item in detect_compute_units():
        status = "✓" if info_item.available else "✗"
        click.echo(f"  {status} [{info_item.unit.value}] {info_item.description}")

    click.echo(f"\nPreferred: {get_compute_unit_indicator()}")

    # Sessions
    session_ids = pipeline._session_manager.list_sessions()
    click.echo(f"\nActive sessions: {len(session_ids)}")
    for sid in session_ids:
        click.echo(f"  - {sid}")

    # Disclaimer
    click.echo(f"\n{get_disclaimer('en')}")


if __name__ == "__main__":
    main()
