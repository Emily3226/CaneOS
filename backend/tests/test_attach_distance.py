"""Unit tests for detection_input.attach_distance()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import detection_input


def _detection(direction: str) -> dict:
    return {
        "timestamp": 0,
        "object_class": "person",
        "direction": direction,
        "confidence": 0.9,
    }


def test_attach_distance_left(monkeypatch):
    monkeypatch.setattr(
        detection_input.tof_input,
        "read_all_tof",
        lambda: {"left": 1.1, "right": 2.2, "up": 3.3},
    )
    detection = _detection("left")
    result = detection_input.attach_distance(detection)

    assert result["distance_m"] == 1.1
    # Original fields preserved; input dict left untouched.
    assert result["object_class"] == "person"
    assert "distance_m" not in detection


def test_attach_distance_right(monkeypatch):
    monkeypatch.setattr(
        detection_input.tof_input,
        "read_all_tof",
        lambda: {"left": 1.1, "right": 2.2, "up": 3.3},
    )
    result = detection_input.attach_distance(_detection("right"))
    assert result["distance_m"] == 2.2


def test_attach_distance_center_uses_min_of_left_right(monkeypatch):
    monkeypatch.setattr(
        detection_input.tof_input,
        "read_all_tof",
        lambda: {"left": 1.1, "right": 0.9, "up": 3.3},
    )
    result = detection_input.attach_distance(_detection("center"))
    assert result["distance_m"] == 0.9

    monkeypatch.setattr(
        detection_input.tof_input,
        "read_all_tof",
        lambda: {"left": 0.4, "right": 2.5, "up": 3.3},
    )
    result = detection_input.attach_distance(_detection("center"))
    assert result["distance_m"] == 0.4
