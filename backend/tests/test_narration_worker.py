"""
Tests for narration_worker._handle_event(): confirms tof_up events never
call Gemini, camera events do, and the shared throttle still gates both.

Uses asyncio.run() directly (rather than pytest-asyncio) to avoid adding a
new test dependency for a handful of async test bodies.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import narration_worker
from pipeline.throttle import HazardThrottle


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def _fake_calls(monkeypatch):
    calls = {"analyze_hazard": 0, "broadcast_hazard": []}

    async def fake_analyze_hazard(frame, detection):
        calls["analyze_hazard"] += 1
        return {
            "hazard_type": "person",
            "direction": detection["direction"],
            "urgency": "medium",
            "spoken_description": "a person is nearby",
        }

    async def fake_broadcast_hazard(hazard):
        calls["broadcast_hazard"].append(hazard)

    monkeypatch.setattr(narration_worker, "analyze_hazard", fake_analyze_hazard)
    monkeypatch.setattr(narration_worker, "broadcast_hazard", fake_broadcast_hazard)
    return calls


def test_tof_up_event_never_calls_gemini(monkeypatch):
    calls = _fake_calls(monkeypatch)
    throttle = HazardThrottle(clock=FakeClock())
    event = {"source": "tof_up", "distance_m": 0.2}

    asyncio.run(narration_worker._handle_event(event, throttle))

    assert calls["analyze_hazard"] == 0
    assert len(calls["broadcast_hazard"]) == 1
    hazard = calls["broadcast_hazard"][0]
    assert hazard["direction"] == "up"
    assert hazard["hazard_type"] == "overhead_obstacle"
    assert hazard["urgency"] == "high"


def test_camera_event_calls_gemini(monkeypatch):
    calls = _fake_calls(monkeypatch)
    throttle = HazardThrottle(clock=FakeClock())
    detection = {
        "timestamp": 0,
        "object_class": "person",
        "direction": "left",
        "confidence": 0.9,
        "distance_m": 1.0,
    }
    event = {"source": "camera", "detection": detection, "frame": b"fake-jpeg-bytes"}

    asyncio.run(narration_worker._handle_event(event, throttle))

    assert calls["analyze_hazard"] == 1
    assert len(calls["broadcast_hazard"]) == 1


def test_throttled_camera_event_skips_gemini_and_broadcast(monkeypatch):
    calls = _fake_calls(monkeypatch)
    clock = FakeClock()
    throttle = HazardThrottle(cooldown_s=8.0, hard_cap_s=3.0, clock=clock)
    detection = {
        "timestamp": 0,
        "object_class": "person",
        "direction": "left",
        "confidence": 0.9,
        "distance_m": 1.0,
    }
    event = {"source": "camera", "detection": detection, "frame": b"jpeg"}

    asyncio.run(narration_worker._handle_event(event, throttle))  # narrates
    clock.advance(0.5)  # well within both cooldown and hard cap
    asyncio.run(narration_worker._handle_event(event, throttle))  # throttled out

    assert calls["analyze_hazard"] == 1
    assert len(calls["broadcast_hazard"]) == 1


def test_overhead_and_camera_hazards_use_independent_signatures(monkeypatch):
    calls = _fake_calls(monkeypatch)
    clock = FakeClock()
    throttle = HazardThrottle(cooldown_s=8.0, hard_cap_s=3.0, clock=clock)
    detection = {
        "timestamp": 0,
        "object_class": "person",
        "direction": "left",
        "confidence": 0.9,
        "distance_m": 1.0,
    }
    camera_event = {"source": "camera", "detection": detection, "frame": b"jpeg"}
    tof_up_event = {"source": "tof_up", "distance_m": 0.2}

    asyncio.run(narration_worker._handle_event(camera_event, throttle))
    clock.advance(3.5)  # past hard cap, well within cooldown
    # A different signature (overhead_obstacle, up) bypasses the camera
    # hazard's cooldown -- it's treated as its own distinct hazard, not a
    # re-narration of the same one.
    asyncio.run(narration_worker._handle_event(tof_up_event, throttle))

    assert calls["analyze_hazard"] == 1
    assert len(calls["broadcast_hazard"]) == 2
    assert calls["broadcast_hazard"][1]["direction"] == "up"
