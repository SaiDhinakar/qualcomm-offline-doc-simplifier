"""Compute unit detection and indication (FR-22).

Detects which compute unit (NPU/GPU/CPU) is available for on-device inference
and reports it so the UI can visibly indicate on-device processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComputeUnit(str, Enum):
    NPU = "NPU"
    GPU = "GPU"
    CPU = "CPU"
    UNKNOWN = "UNKNOWN"


@dataclass
class ComputeUnitInfo:
    unit: ComputeUnit
    available: bool
    description: str


def detect_compute_units() -> list[ComputeUnitInfo]:
    """Detect available compute units on this device.

    Returns a list of ComputeUnitInfo for each unit, ordered by preference
    (NPU > GPU > CPU).
    """
    results: list[ComputeUnitInfo] = []

    # Detect NPU (Qualcomm Hexagon) via qai-hub or platform-specific checks
    npu_available = _detect_npu()
    results.append(ComputeUnitInfo(
        unit=ComputeUnit.NPU,
        available=npu_available,
        description="Qualcomm Hexagon NPU" if npu_available else "Not detected",
    ))

    # Detect GPU via optional deps
    gpu_available = _detect_gpu()
    results.append(ComputeUnitInfo(
        unit=ComputeUnit.GPU,
        available=gpu_available,
        description="GPU acceleration" if gpu_available else "Not detected",
    ))

    # CPU always available
    results.append(ComputeUnitInfo(
        unit=ComputeUnit.CPU,
        available=True,
        description="CPU (always available)",
    ))

    return results


def _detect_npu() -> bool:
    """Detect Qualcomm Hexagon NPU availability."""
    try:
        import qai_hub as qai  # noqa: F401
        # qai-hub installed — NPU jobs can be submitted (cloud or local)
        return True
    except ImportError:
        pass

    # Check for Qualcomm-specific system files/drivers
    import os
    npu_paths = [
        "/dev/msm_subsys",
        "/sys/class/devfreq/soc:qcom,cpu-llcc-ddr-bw",
        "/sys/bus/platform/drivers/msm_thermal",
    ]
    return any(os.path.exists(p) for p in npu_paths)


def _detect_gpu() -> bool:
    """Detect GPU availability (OpenCL/CUDA/Vulkan)."""
    import shutil

    # Check for common GPU tools
    gpu_tools = ["nvidia-smi", "clinfo", "vulkaninfo"]
    if any(shutil.which(tool) for tool in gpu_tools):
        return True

    # Check for GPU device files
    import os
    gpu_paths = ["/dev/dri/renderD128", "/dev/nvidia0"]
    return any(os.path.exists(p) for p in gpu_paths)


def get_preferred_compute_unit() -> ComputeUnitInfo:
    """Get the preferred (highest available) compute unit."""
    units = detect_compute_units()
    for unit in units:  # already ordered NPU > GPU > CPU
        if unit.available:
            return unit
    return units[-1]  # CPU fallback


def get_compute_unit_indicator() -> str:
    """Get a human-readable compute unit indicator string for the UI.

    Returns something like: "[NPU] Qualcomm Hexagon NPU" or "[GPU] GPU acceleration"
    """
    unit = get_preferred_compute_unit()
    return f"[{unit.unit.value}] {unit.description}"


def is_on_device() -> bool:
    """Return True if any accelerated compute unit is available (NPU/GPU).

    CPU-only still counts as on-device (local), but NPU/GPU is preferred.
    """
    units = detect_compute_units()
    return any(u.available for u in units)
