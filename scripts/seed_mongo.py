"""Seed 10 mock historical transactions for dashboard demo."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

COL = "amd_hybrid_ops_transactions"


def seed_if_empty(mongo_uri: str | None = None, mongo_db: str = "pcdoctor_swarm") -> int:
    try:
        from app.settings import settings

        uri = mongo_uri or settings.mongo_uri
        db_name = mongo_db or settings.mongo_db
    except Exception:
        uri = mongo_uri or "mongodb://127.0.0.1:27017"
        db_name = mongo_db

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        col = client[db_name][COL]
        if col.count_documents({}) >= 10:
            return col.count_documents({})

        now = datetime.now(timezone.utc)
        samples = [
            ("smart_quoter_agent", "local", "qwen2.5:14b-instruct-q4_K_M", 0, 0, "intake_extraction"),
            ("smart_quoter_agent", "fireworks", "gemma-2-9b-it", 0, 842, "executive_polish"),
            ("watchdog_sre_agent", "local", "llama3.1:latest", 0, 0, "health_scan"),
            ("smart_quoter_agent", "local", "qwen2.5:14b-instruct-q4_K_M", 0, 0, "quote_draft"),
            ("watchdog_sre_agent", "local", "llama3.1:latest", 0, 0, "remediation_blueprint"),
            ("smart_quoter_agent", "fireworks", "gemma-2-9b-it", 0, 1204, "risk_audit"),
            ("root_gateway", "local", "routing-phi", 0, 0, "a2a_delegate"),
            ("smart_quoter_agent", "local", "qwen2.5:14b-instruct-q4_K_M", 0, 0, "line_items"),
            ("watchdog_sre_agent", "local", "llama3.1:latest", 0, 0, "container_watch"),
            ("smart_quoter_agent", "fireworks", "gemma-2-9b-it", 0, 956, "corporate_summary"),
        ]

        for i, (agent, runtime, model, tl, tr, action) in enumerate(samples):
            col.insert_one(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "agent": agent,
                    "runtime": runtime,
                    "model": model,
                    "tokens_local": tl,
                    "tokens_remote": tr,
                    "action": action,
                    "status": "completed",
                    "ts": (now - timedelta(hours=i * 3)).isoformat(),
                    "session_id": f"seed-session-{i + 1}",
                }
            )
        return col.count_documents({})
    except Exception:
        return 0
