"""
Independent, unthrottled haptic reflex loop.

WHY THIS IS SEPARATE FROM THE CAMERA/GEMINI PIPELINE: haptic feedback needs
to be as close to instantaneous as a physical reflex -- there's no room for
a Gemini round-trip, a cooldown, or a dedup window between "a sensor reads
close" and "the user feels a buzz." This module must never import from or
await throttle.py or gemini_stage.py; it stays fully independent so nothing
in the narration pipeline can ever add latency here, and nothing here can
ever be delayed by a slow Gemini call.

The one addition to that rule: an "up" trigger also gets a spoken
narration (the camera can't see overhead, so there'd otherwise be no
narration at all for overhead hazards -- see narration_templates.py). That
still can't be allowed to slow this loop down, so it's a fire-and-forget
push onto narration_queue -- narration_queue.push_nowait() is
non-blocking and never raises, and everything downstream of it (throttle,
template lookup, broadcast) happens entirely in narration_worker.py, on
its own task, on its own time.
"""

from __future__ import annotations

import asyncio
import logging

from pipeline import narration_queue, tof_input
from pipeline.haptic_trigger import check_thresholds
from pipeline.server import broadcast_haptic

logger = logging.getLogger(__name__)

# ~15Hz. check_thresholds() is deliberately stateless (fires on every tick
# a sensor reads close, no debouncing -- see haptic_trigger.py), so a
# sustained single-direction hazard sends one message per tick for as long
# as it stays close. At 15Hz that tops out at 15 msgs/sec on that direction
# -- comfortably under the /ws/haptics safety valve's 20 msgs/sec cap, so
# the cap stays a true rare-bug guard rather than binding during ordinary
# sustained proximity. (An earlier 100Hz default was tried and reliably hit
# the cap during any 1+ second sustained-proximity scenario -- pure
# arithmetic, not a bug -- so the poll rate was brought down to match the
# cap instead of loosening the cap's framing.) 15Hz is still far faster
# than a human can perceive as anything but continuous buzzing, and vastly
# faster than the narration path's multi-second cooldowns.
DEFAULT_POLL_INTERVAL_S = 1 / 15


async def run_haptic_loop(poll_interval_s: float = DEFAULT_POLL_INTERVAL_S) -> None:
    """
    Runs forever as its own independent asyncio background task: read all
    ToF sensors, check thresholds, broadcast any triggered directions,
    sleep briefly, repeat. Never awaits anything from the camera/Gemini
    pipeline, so it can't be slowed down by it.
    """
    logger.info("Haptic loop started (poll_interval_s=%s)", poll_interval_s)
    while True:
        distances = tof_input.read_all_tof()
        for direction in check_thresholds(distances):
            # Unchanged, immediate, non-blocking -- the haptic buzz itself
            # never waits on anything narration-related.
            await broadcast_haptic(direction)
            if direction == "up":
                narration_queue.push_nowait({"source": "tof_up", "distance_m": distances["up"]})
        await asyncio.sleep(poll_interval_s)
