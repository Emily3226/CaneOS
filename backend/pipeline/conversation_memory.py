"""
Conversation history for the "Hey Cane" on-demand Q&A feature, backed by
the SAME MongoDB Atlas database the vercel-backend/ project already uses
for contacts/incidents -- not a second, separate database. That project is
a Node.js/Vercel serverless app (a different language and process from
this Python backend), so the two sides can't literally share a client
instance -- but they read the same MONGODB_URI / MONGODB_DB_NAME env vars
(see vercel-backend/lib/mongodb.js and vercel-backend/README.md), so both
land in one logical database. This is the only place that talks to Mongo
from the hazard-pipeline side.

Uses motor (the async MongoDB driver) rather than plain pymongo, since
this FastAPI app is async throughout -- a blocking Mongo call here would
stall the same event loop serving the haptic loop and the WebSocket
connections in real time.

Collection name ("conversations") matches the existing "contacts" /
"incidents" naming convention: a plain singular English noun, no
underscores.

This is intentionally NOT wired into throttle.py, narration_queue.py, or
narration_worker.py -- every explicit question gets an answer, no
dedup/cooldown applies here, unlike the ambient hazard narration path.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

COLLECTION_NAME = "conversations"

# Created lazily on first use (not at import time), same reasoning as
# gemini_stage._get_client(): importing this module shouldn't require
# MONGODB_URI to already be set, which matters for running tests that
# never touch the network.
_client: Optional[AsyncIOMotorClient] = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError(
                "MONGODB_URI is not set. See .env.example -- this should be the "
                "same Atlas connection string vercel-backend/ uses."
            )
        _client = AsyncIOMotorClient(uri)
        db_name = os.getenv("MONGODB_DB_NAME", "caneos")
        _collection = _client[db_name][COLLECTION_NAME]
    return _collection


async def get_recent_context(session_id: str, limit: int = 5) -> List[dict]:
    """
    Returns the most recent `limit` Q&A exchanges for this session_id,
    ordered oldest-to-newest (so they read naturally when dropped into a
    prompt), each as {"question": ..., "answer": ...}. Returns an empty
    list if the session has no history yet -- never raises for that case.
    """
    collection = _get_collection()
    cursor = collection.find({"session_id": session_id}).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    docs.reverse()  # newest-first from the query -> oldest-first for the prompt
    return [{"question": doc["question"], "answer": doc["answer"]} for doc in docs]


async def save_exchange(session_id: str, question: str, answer: str) -> None:
    """Inserts a new Q&A exchange with the current UTC timestamp."""
    collection = _get_collection()
    await collection.insert_one(
        {
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "timestamp": datetime.now(timezone.utc),
        }
    )
