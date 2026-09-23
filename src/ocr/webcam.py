"""Webcam capture for document input (FR-1)."""

from __future__ import annotations

from pathlib import Path


def capture_from_webcam(output_path: Path, camera_index: int = 0) -> Path:
    """Capture a single frame from the webcam and save it as an image.

    Requires OpenCV (`opencv-python`). Raises RuntimeError if unavailable.

    Args:
        output_path: path to save the captured image.
        camera_index: webcam device index (default 0).

    Returns:
        The path to the saved image.
    """
    try:
        import cv2
    except ImportError:
        raise RuntimeError(
            "Webcam capture requires opencv-python. "
            "Install with: uv pip install opencv-python"
        )

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam (index {camera_index})")

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture frame from webcam")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), frame)
    return output_path
