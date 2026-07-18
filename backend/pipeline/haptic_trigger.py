"""
Direct haptic reflex threshold check.

Deliberately stateless -- no debouncing, no memory of previous calls. This
is the reflex path: if a sensor currently reads too close, the user needs
to feel that buzz right now, not after some cooldown or dedup window
decides it's "new enough" to bother with. That kind of smoothing is exactly
right for spoken narration (see throttle.py's HazardThrottle, which exists
precisely to avoid repeating itself) but wrong here -- for a physical
collision-avoidance signal, a missed or delayed buzz is far worse than an
occasional repeated one. Immediacy matters more than avoiding repeats.
"""

from __future__ import annotations


def check_thresholds(distances: dict, near_threshold_m: float = 0.75) -> list:
    """
    Given a {"left": ..., "right": ..., "up": ...} distance reading (as
    returned by tof_input.read_all_tof()), returns the list of directions
    currently closer than near_threshold_m. Can be empty, one direction,
    or all of them -- every call is evaluated fresh, independent of any
    previous call.
    """
    return [
        direction
        for direction, distance_m in distances.items()
        if distance_m < near_threshold_m
    ]
