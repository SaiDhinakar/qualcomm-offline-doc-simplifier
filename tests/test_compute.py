"""Tests for compute unit detection (FR-22)."""

from src.utils.compute import (
    ComputeUnit,
    detect_compute_units,
    get_compute_unit_indicator,
    get_preferred_compute_unit,
    is_on_device,
)


def test_detect_compute_units_returns_all():
    units = detect_compute_units()
    assert len(units) == 3
    unit_types = [u.unit for u in units]
    assert ComputeUnit.NPU in unit_types
    assert ComputeUnit.GPU in unit_types
    assert ComputeUnit.CPU in unit_types


def test_cpu_always_available():
    units = detect_compute_units()
    cpu = next(u for u in units if u.unit == ComputeUnit.CPU)
    assert cpu.available is True


def test_get_preferred_returns_available():
    preferred = get_preferred_compute_unit()
    assert preferred.available is True


def test_compute_unit_indicator_format():
    indicator = get_compute_unit_indicator()
    assert indicator.startswith("[")
    assert "]" in indicator


def test_is_on_device():
    # CPU is always available, so is_on_device should always be True
    assert is_on_device() is True
