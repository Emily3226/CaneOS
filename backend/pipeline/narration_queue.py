"""
Shared queue where both narration origins -- camera detections (pushed by
main.py's run_pipeline) and overhead ToF triggers (pushed by
haptic_loop.py) -- land, to be consumed by narration_worker.py.

Two event shapes are pushed onto this queue:
- Camera-originated: {"source": "camera", "detection": <the enriched
  detection dict with distance_m already attached by attach_distance()>,
  "frame": <JPEG bytes>}
- ToF-up-originated: {"source": "tof_up", "distance_m": <float>}
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Generous, not a real backpressure mechanism -- HazardThrottle gates most
# events out long before they'd pile up here. This cap only exists so a
# stalled/crashed narration_worker can't let the queue grow unbounded.
_MAX_QUEUE_SIZE = 1000

queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)


def push_nowait(event: dict) -> None:
    """
    Fire-and-forget push: never blocks, never raises, no matter what.

    haptic_loop.py calls this from its ~15Hz polling cycle and must never
    be slowed down or crashed by anything narration-related -- if the
    queue is somehow full (narration_worker stalled, or a bug elsewhere),
    this drops the OLDEST queued event to make room for the new one rather
    than blocking the caller or silently discarding the new event, since a
    fresh reading is more useful than a stale queued one.
    """
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        try:
            queue.get_nowait()
        except Exception:  # noqa: BLE001 - best-effort, never let this raise
            pass
        try:
            queue.put_nowait(event)
        except Exception:  # noqa: BLE001 - see docstring: must never raise
            logger.warning("narration_queue full even after dropping oldest, discarding: %s", event)
    except Exception:  # noqa: BLE001 - see docstring: must never raise
        logger.warning("narration_queue push failed unexpectedly, discarding: %s", event)
