"""Tests for the CLI (FR-21)."""

from click.testing import CliRunner

from src.cli import main


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Qualcomm Doc Simplifier" in result.output


def test_cli_info():
    runner = CliRunner()
    result = runner.invoke(main, ["info"])
    assert result.exit_code == 0
    assert "Compute Units" in result.output
    assert "DISCLAIMER" in result.output or "disclaimer" in result.output.lower()


def test_cli_clear_requires_all():
    runner = CliRunner()
    result = runner.invoke(main, ["clear"])
    assert result.exit_code == 0
    assert "--all" in result.output


def test_cli_clear_all():
    runner = CliRunner()
    result = runner.invoke(main, ["clear", "--all"])
    assert result.exit_code == 0
    assert "Cleared" in result.output


def test_cli_ask_missing_session():
    runner = CliRunner()
    result = runner.invoke(main, ["ask", "nonexistent_doc", "What is this?"])
    assert result.exit_code == 1
    assert "No active session" in result.output
