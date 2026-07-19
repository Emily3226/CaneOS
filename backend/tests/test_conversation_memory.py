"""
Tests for conversation_memory.py. Uses a small in-memory fake collection
(not a real MongoDB, not mongomock) that implements just the
find().sort().limit().to_list() / insert_one() surface these two
functions actually use -- enough to test the real ordering/limiting/
empty-session logic without touching production data or requiring a live
MongoDB connection for the test suite.

Uses asyncio.run() directly (rather than pytest-asyncio) to match the
convention already established in test_narration_worker.py.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import conversation_memory


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, key, direction):
        self._docs = sorted(self._docs, key=lambda d: d[key], reverse=(direction == -1))
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, filter_):
        matched = [d for d in self.docs if all(d.get(k) == v for k, v in filter_.items())]
        return FakeCursor(matched)

    async def insert_one(self, doc):
        self.docs.append(doc)
        return SimpleNamespace(inserted_id="fake_id")


def _patch_collection(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(conversation_memory, "_get_collection", lambda: fake)
    return fake


def _ts(seconds_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)


def test_get_recent_context_empty_for_unknown_session(monkeypatch):
    _patch_collection(monkeypatch)
    result = asyncio.run(conversation_memory.get_recent_context("nobody-yet"))
    assert result == []


def test_save_exchange_persists_a_document(monkeypatch):
    fake = _patch_collection(monkeypatch)
    asyncio.run(conversation_memory.save_exchange("s1", "where am I?", "In a hallway."))

    assert len(fake.docs) == 1
    doc = fake.docs[0]
    assert doc["session_id"] == "s1"
    assert doc["question"] == "where am I?"
    assert doc["answer"] == "In a hallway."
    assert "timestamp" in doc


def test_get_recent_context_orders_oldest_to_newest_and_respects_limit(monkeypatch):
    fake = _patch_collection(monkeypatch)
    # Insert out of chronological order to confirm sorting, not insertion
    # order, determines the result.
    fake.docs = [
        {"session_id": "s1", "question": "q3", "answer": "a3", "timestamp": _ts(10)},
        {"session_id": "s1", "question": "q1", "answer": "a1", "timestamp": _ts(30)},
        {"session_id": "s1", "question": "q2", "answer": "a2", "timestamp": _ts(20)},
        {"session_id": "s1", "question": "q0", "answer": "a0", "timestamp": _ts(40)},
        {"session_id": "other-session", "question": "qX", "answer": "aX", "timestamp": _ts(5)},
    ]

    result = asyncio.run(conversation_memory.get_recent_context("s1", limit=3))

    # Most recent 3 for s1 (q1, q2, q3), returned oldest-to-newest.
    assert result == [
        {"question": "q1", "answer": "a1"},
        {"question": "q2", "answer": "a2"},
        {"question": "q3", "answer": "a3"},
    ]


def test_get_recent_context_only_returns_matching_session(monkeypatch):
    fake = _patch_collection(monkeypatch)
    fake.docs = [
        {"session_id": "s1", "question": "q1", "answer": "a1", "timestamp": _ts(10)},
        {"session_id": "s2", "question": "qA", "answer": "aA", "timestamp": _ts(5)},
    ]
    result = asyncio.run(conversation_memory.get_recent_context("s2"))
    assert result == [{"question": "qA", "answer": "aA"}]
