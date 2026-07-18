"""
Tests for narration_queue.push_nowait()'s core guarantee: it never blocks
and never raises, even when the queue is full -- haptic_loop.py depends on
that to stay fast regardless of what narration_worker is doing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import narration_queue


def _drain(q):
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    return items


def test_push_nowait_adds_event_to_queue():
    _drain(narration_queue.queue)
    narration_queue.push_nowait({"source": "tof_up", "distance_m": 0.3})
    items = _drain(narration_queue.queue)
    assert items == [{"source": "tof_up", "distance_m": 0.3}]


def test_push_nowait_never_raises_when_queue_is_full():
    _drain(narration_queue.queue)
    for i in range(narration_queue._MAX_QUEUE_SIZE + 5):
        narration_queue.push_nowait({"source": "tof_up", "distance_m": float(i)})

    # Should not have raised, and the queue should be capped, not
    # unbounded.
    assert narration_queue.queue.qsize() <= narration_queue._MAX_QUEUE_SIZE

    # The most recent pushes should have survived (oldest were dropped),
    # confirming drop-oldest rather than drop-newest.
    items = _drain(narration_queue.queue)
    last_distance = items[-1]["distance_m"]
    assert last_distance == float(narration_queue._MAX_QUEUE_SIZE + 4)
