"""Camera scan configuration scaffold for TA6.

Fill pixel coordinates and RGB references after mounting and calibrating the camera.
This module deliberately does not guess image locations or classify uncalibrated colors.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypeAlias

RGB: TypeAlias = tuple[int, int, int]
Pixel: TypeAlias = tuple[int, int]
FACES = "URFDLB"
VISIBLE_FACES = ("U", "R", "F")  # Change to match the calibrated camera view.

# Facelet names use row-major 1..9 order per face. Set each pixel to (x, y).
# A fixed image samples only the visible faces; other faces need more views.
SAMPLE_PIXEL_COORDINATES: dict[str, Pixel | None] = {
    f"{face}{index}": None
    for face in VISIBLE_FACES
    for index in range(1, 10)
}

# Set calibrated representative RGB values measured with the actual camera.
COLOR_REFERENCE_RGB: dict[str, RGB | None] = {face: None for face in FACES}

# Named variables hold the latest observations for convenient inspection/debugging.
scan_rgb_variables: dict[str, RGB | None] = {name: None for name in SAMPLE_PIXEL_COORDINATES}
facelet_color_variables: dict[str, str | None] = {name: None for name in SAMPLE_PIXEL_COORDINATES}


def classify_rgb(rgb: RGB, references: Mapping[str, RGB | None] = COLOR_REFERENCE_RGB) -> str:
    """Return the nearest calibrated face color by squared RGB distance."""
    if any(references.get(face) is None for face in FACES):
        raise RuntimeError("Set all six COLOR_REFERENCE_RGB entries before classifying camera samples")
    return min(
        FACES,
        key=lambda face: sum(
            (rgb[channel] - references[face][channel]) ** 2  # type: ignore[index]
            for channel in range(3)
        ),
    )


def read_visible_scan(
    pixel_reader: Callable[[int, int], RGB],
    coordinates: Mapping[str, Pixel | None] = SAMPLE_PIXEL_COORDINATES,
    references: Mapping[str, RGB | None] = COLOR_REFERENCE_RGB,
) -> tuple[dict[str, RGB], dict[str, str]]:
    """Sample configured sticker centers and return raw RGB and facelet-label maps.

    pixel_reader reads an RGB value from an already captured camera frame. Camera
    capture and coordinate/color calibration are intentionally injected later.
    """
    missing_pixels = [name for name in SAMPLE_PIXEL_COORDINATES if coordinates.get(name) is None]
    if missing_pixels:
        raise RuntimeError("Set SAMPLE_PIXEL_COORDINATES for: " + ", ".join(missing_pixels))
    if any(references.get(face) is None for face in FACES):
        raise RuntimeError("Set all six COLOR_REFERENCE_RGB entries before scanning")

    raw_samples: dict[str, RGB] = {}
    color_labels: dict[str, str] = {}
    for name in SAMPLE_PIXEL_COORDINATES:
        point = coordinates[name]
        assert point is not None
        x, y = point
        rgb = pixel_reader(x, y)
        raw_samples[name] = rgb
        color_labels[name] = classify_rgb(rgb, references)

    scan_rgb_variables.update(raw_samples)
    facelet_color_variables.update(color_labels)
    return raw_samples, color_labels
