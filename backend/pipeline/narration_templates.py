"""
Template-based spoken descriptions for overhead ("up") hazards.

The camera is aimed forward at cane/chest height -- it has no view of
overhead space, so there's no useful photo to hand Gemini for a "up" ToF
trigger. Rather than send a vision call that has nothing relevant to look
at (and would just be guessing), overhead hazards get a fixed template
sentence instead, picked by distance.
"""

from __future__ import annotations

# Below this distance, an overhead obstacle is urgent enough for "high";
# at or above it (but still close enough to have crossed
# haptic_trigger.check_thresholds()'s near-distance threshold in the first
# place), "medium". Kept separate from that threshold so either can be
# retuned independently.
HIGH_URGENCY_DISTANCE_M = 0.4

UP_HAZARD_TEMPLATES = {
    "high": "Watch your head, obstacle overhead",
    "medium": "Low object ahead, be careful",
}


def build_up_hazard(distance_m: float) -> dict:
    """
    Returns a hazard dict in the exact same shape gemini_stage.analyze_hazard()
    produces, so narration_worker.py can treat both narration origins
    identically from this point on (throttle -> broadcast).
    """
    urgency = "high" if distance_m < HIGH_URGENCY_DISTANCE_M else "medium"
    return {
        "hazard_type": "overhead_obstacle",
        "direction": "up",
        "urgency": urgency,
        "spoken_description": UP_HAZARD_TEMPLATES[urgency],
    }
