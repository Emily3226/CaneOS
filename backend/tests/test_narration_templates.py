"""Unit tests for narration_templates.build_up_hazard()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.narration_templates import (
    HIGH_URGENCY_DISTANCE_M,
    UP_HAZARD_TEMPLATES,
    build_up_hazard,
)


def test_high_urgency_when_very_close():
    hazard = build_up_hazard(0.2)
    assert hazard["urgency"] == "high"
    assert hazard["spoken_description"] == UP_HAZARD_TEMPLATES["high"]


def test_medium_urgency_when_further():
    hazard = build_up_hazard(0.6)
    assert hazard["urgency"] == "medium"
    assert hazard["spoken_description"] == UP_HAZARD_TEMPLATES["medium"]


def test_boundary_at_threshold_is_medium_not_high():
    # distance_m < threshold is "high"; exactly at the threshold is not
    # "less than", so it falls to "medium".
    hazard = build_up_hazard(HIGH_URGENCY_DISTANCE_M)
    assert hazard["urgency"] == "medium"


def test_dict_shape_matches_gemini_contract():
    hazard = build_up_hazard(0.1)
    assert set(hazard.keys()) == {"hazard_type", "direction", "urgency", "spoken_description"}
    assert hazard["hazard_type"] == "overhead_obstacle"
    assert hazard["direction"] == "up"
