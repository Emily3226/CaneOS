"""
Tests for gemini_stage.answer_query(): confirms the fallback string is
returned on failure without raising, and that a successful call returns
the (stripped) model text.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import gemini_stage


def test_answer_query_returns_fallback_on_failure(monkeypatch):
    async def failing_call(client, image_bytes, question, recent_context):
        raise RuntimeError("simulated Gemini failure")

    monkeypatch.setattr(gemini_stage, "_call_gemini_query", failing_call)
    monkeypatch.setattr(gemini_stage, "_get_client", lambda: object())

    answer = asyncio.run(gemini_stage.answer_query(b"fake-jpeg", "what's around me?", []))

    assert answer == gemini_stage._QUERY_FALLBACK_ANSWER


def test_answer_query_returns_model_text_on_success(monkeypatch):
    async def fake_call(client, image_bytes, question, recent_context):
        return "You're in a hallway with a chair ahead."

    monkeypatch.setattr(gemini_stage, "_call_gemini_query", fake_call)
    monkeypatch.setattr(gemini_stage, "_get_client", lambda: object())

    answer = asyncio.run(gemini_stage.answer_query(b"fake-jpeg", "what's around me?", []))

    assert answer == "You're in a hallway with a chair ahead."


def test_answer_query_retries_once_before_falling_back(monkeypatch):
    calls = {"count": 0}

    async def flaky_call(client, image_bytes, question, recent_context):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient failure")
        return "Recovered on retry."

    monkeypatch.setattr(gemini_stage, "_call_gemini_query", flaky_call)
    monkeypatch.setattr(gemini_stage, "_get_client", lambda: object())

    answer = asyncio.run(gemini_stage.answer_query(b"fake-jpeg", "what's ahead?", []))

    assert answer == "Recovered on retry."
    assert calls["count"] == 2


def test_build_query_prompt_includes_context_and_question():
    prompt = gemini_stage._build_query_prompt(
        "what's around me?",
        [{"question": "is it safe to cross?", "answer": "Yes, no cars visible."}],
    )
    assert "what's around me?" in prompt
    assert "is it safe to cross?" in prompt
    assert "Yes, no cars visible." in prompt


def test_build_query_prompt_handles_no_context():
    prompt = gemini_stage._build_query_prompt("what's around me?", [])
    assert "(none yet)" in prompt
