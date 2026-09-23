"""Tests for the disclaimer (PRD §4)."""

from src.disclaimer import DISCLAIMER_EN, DISCLAIMER_HI, get_disclaimer


def test_disclaimer_english():
    d = get_disclaimer("en")
    assert "does NOT provide legal or financial advice" in d
    assert d == DISCLAIMER_EN


def test_disclaimer_hindi():
    d = get_disclaimer("hi")
    assert "अस्वीकरण" in d or "कानूनी" in d
    assert d == DISCLAIMER_HI


def test_disclaimer_fallback():
    d = get_disclaimer("xx")  # unsupported language
    assert d == DISCLAIMER_EN
