"""Mongo persistence — sessions, events, transactions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.settings import settings

COL_EVENTS = "amd_hybrid_ops_events"
COL_TRANSACTIONS = "amd_hybrid_ops_transactions"
COL_SESSIONS = "amd_hybrid_ops_sessions"

_client: MongoClient | None = None


def db():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    return _client[settings.mongo_db]


def ping() -> dict[str, Any]:
    try:
        db().command("ping")
        return {"ok": True, "db": settings.mongo_db}
    except PyMongoError as exc:
        return {"ok": False, "error": str(exc)}


def append_event(event: dict[str, Any]) -> None:
    doc = {**event, "ts": datetime.now(timezone.utc).isoformat()}
    try:
        db()[COL_EVENTS].insert_one(doc)
    except PyMongoError:
        pass


def list_events(limit: int = 50) -> list[dict[str, Any]]:
    try:
        cur = db()[COL_EVENTS].find().sort("ts", -1).limit(limit)
        return [{k: v for k, v in d.items() if k != "_id"} for d in cur]
    except PyMongoError:
        return []


def upsert_session(session_id: str, data: dict[str, Any]) -> None:
    try:
        db()[COL_SESSIONS].update_one(
            {"session_id": session_id},
            {"$set": {**data, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    except PyMongoError:
        pass


def get_session(session_id: str) -> dict[str, Any] | None:
    try:
        doc = db()[COL_SESSIONS].find_one({"session_id": session_id})
        if doc:
            doc.pop("_id", None)
        return doc
    except PyMongoError:
        return None


def count_transactions() -> int:
    try:
        return db()[COL_TRANSACTIONS].count_documents({})
    except PyMongoError:
        return 0


def insert_transaction(txn: dict[str, Any]) -> None:
    try:
        db()[COL_TRANSACTIONS].insert_one(txn)
    except PyMongoError:
        pass


def list_transactions(limit: int = 20) -> list[dict[str, Any]]:
    try:
        cur = db()[COL_TRANSACTIONS].find().sort("ts", -1).limit(limit)
        return [{k: v for k, v in d.items() if k != "_id"} for d in cur]
    except PyMongoError:
        return []
