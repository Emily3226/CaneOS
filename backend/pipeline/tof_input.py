"""
Mock ToF (time-of-flight) sensor reads: three independent units, one each
facing left, right, and up/overhead.

INTEGRATION POINT (real hardware): read_all_tof() is the ONLY interface to
ToF hardware -- both the haptic loop (calling 50-100x/sec) and the camera
detection path (calling occasionally, via detection_input.attach_distance())
go through this same function. When the real hardware read is ready, swap
the body of read_all_tof() for the real sensor read and keep the signature
(-> dict with "left"/"right"/"up" float keys) identical so neither caller
needs to change.

Real ToF hardware is naturally pull-based (ask the sensor, get its current
reading) rather than push-based, which is why this is a plain function
rather than a stream/generator -- that matches how the real version will
work too.
"""

from __future__ import annotations

import random
import threading

_DIRECTIONS = ("left", "right", "up")

_BASELINE_MIN_M = 2.0
_BASELINE_MAX_M = 4.0
_NEAR_MIN_M = 0.2
_NEAR_MAX_M = 1.0

# Odds, on any single call where a direction isn't already "dipping", that
# it starts a new dip this call. Kept low so dips read as occasional
# (something passing through), not constant.
_DIP_START_CHANCE = 0.01
_DIP_MIN_CALLS = 5
_DIP_MAX_CALLS = 20

# Guards the shared per-direction dip state below. read_all_tof() is called
# concurrently and at very different rates by the haptic loop (50-100Hz)
# and the camera path (occasionally) -- without this lock, two calls
# interleaving their read-then-write of _dip_remaining could corrupt a
# direction's counter (e.g. both see 0, both decide to start a dip, one
# update clobbers the other's). A plain threading.Lock (not asyncio.Lock)
# is used deliberately: this function has no internal await points and may
# eventually be called from a real hardware SDK's own worker thread, not
# just asyncio tasks.
_lock = threading.Lock()
_dip_remaining = {direction: 0 for direction in _DIRECTIONS}


def read_all_tof() -> dict:
    """
    Returns the current mock distance reading (meters) for each of the
    three ToF sensors, e.g. {"left": 2.1, "right": 3.4, "up": 0.6}.

    Each direction independently sits at a baseline of 2-4m most of the
    time, occasionally dipping to 0.2-1.0m for a handful of consecutive
    calls (simulating something approaching and then clearing) before
    recovering. Safe to call rapidly and concurrently from multiple
    callers at once.
    """
    readings = {}
    with _lock:
        for direction in _DIRECTIONS:
            if _dip_remaining[direction] > 0:
                _dip_remaining[direction] -= 1
                readings[direction] = round(random.uniform(_NEAR_MIN_M, _NEAR_MAX_M), 2)
            elif random.random() < _DIP_START_CHANCE:
                _dip_remaining[direction] = random.randint(_DIP_MIN_CALLS, _DIP_MAX_CALLS) - 1
                readings[direction] = round(random.uniform(_NEAR_MIN_M, _NEAR_MAX_M), 2)
            else:
                readings[direction] = round(random.uniform(_BASELINE_MIN_M, _BASELINE_MAX_M), 2)
    return readings
