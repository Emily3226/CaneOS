"""Unit tests for haptic_trigger.check_thresholds()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.haptic_trigger import check_thresholds


def test_no_directions_triggered():
    assert check_thresholds({"left": 2.0, "right": 3.0, "up": 1.5}) == []


def test_one_direction_triggered():
    assert check_thresholds({"left": 0.5, "right": 3.0, "up": 1.5}) == ["left"]


def test_multiple_directions_triggered():
    result = check_thresholds({"left": 0.4, "right": 0.6, "up": 2.0})
    assert set(result) == {"left", "right"}


def test_all_directions_triggered():
    result = check_thresholds({"left": 0.1, "right": 0.2, "up": 0.3})
    assert set(result) == {"left", "right", "up"}


def test_custom_threshold():
    assert check_thresholds({"left": 1.0}, near_threshold_m=1.5) == ["left"]
    assert check_thresholds({"left": 1.0}, near_threshold_m=0.5) == []


def test_no_state_retained_between_calls():
    # A triggering call must not influence a later, non-triggering call --
    # check_thresholds() is stateless by design.
    assert check_thresholds({"left": 0.2}) == ["left"]
    assert check_thresholds({"left": 5.0}) == []
    assert check_thresholds({"left": 0.2}) == ["left"]
