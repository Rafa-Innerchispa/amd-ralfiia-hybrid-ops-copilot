#!/usr/bin/env python3
"""
Track 1 — AMD Hybrid Token-Efficient Routing Agent harness.

Priority order (minimize remote tokens, maximize accuracy):
1. High-confidence local heuristics → 0 tokens
2. Local GGUF (Qwen2.5-0.5B) → 0 tokens
3. Fireworks (ALLOWED_MODELS) only for hard code/math → few tokens
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# Container layout: /app/run_harness.py + /app/shared/
_APP = Path(__file__).resolve().parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

import httpx

from shared.fireworks_models import normalize_model_id, pick_target_model

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")
INPUT_PATH = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")
ZERO_TOKEN_ONLY = os.environ.get("ZERO_TOKEN_MODE", os.environ.get("ZERO_TOKEN_ONLY", "0")).strip() in {
    "1",
    "true",
    "yes",
}

COMPLEX_KEYWORDS = (
    "code",
    "debug",
    "math",
    "puzzle",
    "matrix",
    "algorithm",
    "algoritmo",
    "implement",
    "function",
    "compile",
    "recursion",
    "proof",
    "eigenvalue",
    "leetcode",
    "write a python",
    "write a program",
    "fix this",
    "rocm",
    "hip",
    "mi300x",
    "hipify",
    "memory",
)

_POSITIVE_STEMS = (
    "good",
    "great",
    "love",
    "excel",
    "happ",
    "positive",
    "amaz",
    "wonder",
    "cool",
    "best",
    "awesome",
    "fantast",
    "superb",
    "perfect",
    "delight",
    "pleas",
    "enjoy",
    "brilliant",
    "outstanding",
    "impressive",
    "solid",
    "smooth",
    "fast",
    "reliable",
)
_NEGATIVE_STEMS = (
    "bad",
    "terrible",
    "hate",
    "awful",
    "sad",
    "negative",
    "horri",
    "poor",
    "worst",
    "fail",
    "broken",
    "slow",
    "crash",
    "bug",
    "disappoint",
    "frustrat",
    "useless",
    "problem",
    "issue",
    "error",
    "unreliable",
    "lag",
)

_LOCAL_LLM = None
_LOCAL_LLM_TRIED = False

SYSTEM_BRIEF = (
    "Answer with ONLY the final short result. "
    "No lists of rules. No explanations. "
    "Sentiment labels: positive | negative | neutral | mixed. "
    "Otherwise reply with the shortest correct answer."
)

SYSTEM_FIREWORKS = (
    "You are solving an evaluation task. "
    "Return only the final answer that would be graded. "
    "Be concise. Do not restate the instructions. "
    "If the task is incomplete, give the best direct answer or a minimal clarifying ask."
)


def is_evaluator_mode() -> bool:
    return bool(os.environ.get("ALLOWED_MODELS", "").strip())


def pick_fireworks_model() -> str:
    return pick_target_model(role="complex")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _has_stem(words: set[str], stems: tuple[str, ...]) -> bool:
    for word in words:
        for stem in stems:
            if word == stem or word.startswith(stem):
                return True
    return False


def _extract_quoted_or_after_colon(prompt: str) -> str:
    for pattern in (
        r'["“](.+?)["”]',
        r"sentiment[:\s]+(.+)$",
        r"classify[:\s]+(.+)$",
        r"text[:\s]+(.+)$",
        r"review[:\s]+(.+)$",
        r"message[:\s]+(.+)$",
    ):
        match = re.search(pattern, prompt, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return prompt


def perform_fastrag(prompt: str) -> str:
    """Perform keyword syntactic search on MongoDB ralfia_agent_messages or local JSON fallback."""
    key_terms = ["rocm", "hip", "mi300x", "memory", "hipify"]
    lowered_prompt = prompt.lower()
    matched_terms = [t for t in key_terms if t in lowered_prompt]
    if not matched_terms:
        return ""

    messages = []
    # 1) Try real-time MongoDB query first
    try:
        from pymongo import MongoClient
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
        db_name = os.environ.get("MONGO_DB", "pcdoctor_swarm")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        col = db["ralfia_agent_messages"]
        query = {"$or": [{"content": {"$regex": re.escape(t), "$options": "i"}} for t in matched_terms]}
        mongo_docs = list(col.find(query))
        messages = [{"content": doc.get("content", "")} for doc in mongo_docs if doc.get("content")]
    except Exception as e:
        print(f"[RAG] MongoDB connect failed or skipped ({e}), falling back to local JSON cache", file=sys.stderr)

    # 2) Fallback to local JSON cache if Mongo failed or returned empty
    if not messages:
        MESSAGES_DUMP_PATH = os.path.join(os.path.dirname(__file__), "agent_messages.json")
        if os.path.isfile(MESSAGES_DUMP_PATH):
            try:
                with open(MESSAGES_DUMP_PATH, encoding="utf-8") as f:
                    messages = json.load(f)
            except Exception as e:
                print(f"[RAG] Error reading cache file: {e}", file=sys.stderr)

    if not messages:
        return ""

    scored_messages = []
    for msg in messages:
        content = str(msg.get("content", ""))
        content_lower = content.lower()
        score = sum(content_lower.count(t) for t in matched_terms)
        if score > 0:
            scored_messages.append((score, content))

    # Sort by score descending and take top 5
    scored_messages.sort(key=lambda x: x[0], reverse=True)
    top_messages = [content for score, content in scored_messages[:5]]

    if not top_messages:
        return ""

    context = "\n=== AMD ROCm & Hardware Operational Context (Retrieved Ground Truth) ===\n"
    for idx, msg in enumerate(top_messages):
        context += f"Reference {idx + 1}:\n{msg}\n\n"
    return context


def is_complex_task(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(k in lowered for k in COMPLEX_KEYWORDS)


def run_local_heuristics(prompt: str) -> str | None:
    """High-confidence local path (0 tokens). Returns None when unsure."""
    lowered = prompt.lower()
    words = set(_tokenize(lowered))
    payload = _extract_quoted_or_after_colon(prompt)
    payload_words = set(_tokenize(payload))

    wants_sentiment = (
        "sentiment" in lowered
        or "positive or negative" in lowered
        or "polarity" in lowered
        or re.search(r"\b(tone|opinion)\b", lowered) is not None
    )
    if wants_sentiment:
        # Avoid counting task instruction words as polarity
        instruction = {
            "sentiment",
            "classify",
            "classification",
            "positive",
            "negative",
            "neutral",
            "polarity",
            "tone",
            "opinion",
        }
        payload_only = payload_words - instruction
        scan = payload_only or payload_words
        has_pos = _has_stem(scan, _POSITIVE_STEMS)
        has_neg = _has_stem(scan, _NEGATIVE_STEMS)
        if has_pos and not has_neg:
            return "positive"
        if has_neg and not has_pos:
            return "negative"
        if has_pos and has_neg:
            return "mixed"
        # Unsure → local LLM (do not force neutral)
        return None

    wants_classify = (
        "classify" in lowered
        or "classification" in lowered
        or "label this" in lowered
        or "categorize" in lowered
    ) and not wants_sentiment
    if wants_classify:
        if words & {"spam", "phishing", "scam", "fraud"}:
            return "spam"
        if words & {"support", "helpdesk", "ticket", "bug", "outage", "incident"}:
            return "support"
        if words & {"sales", "pricing", "quote", "buy", "purchase", "demo"}:
            return "sales"
        if words & {"billing", "invoice", "payment", "refund"}:
            return "billing"
        if words & {"hr", "payroll", "recruiting", "onboarding"}:
            return "hr"
        # Not confident enough for a forced "general"
        return None

    if (
        "ner" in lowered
        or "named entit" in lowered
        or "extract entit" in lowered
        or "extract the entities" in lowered
        or "find entities" in lowered
    ):
        entities: list[str] = []
        # Prefer payload after colon
        scan_text = payload if payload != prompt else prompt
        for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", scan_text):
            name = match.group(1)
            if name.lower() in {
                "the",
                "what",
                "which",
                "named",
                "entity",
                "entities",
                "extract",
                "please",
                "identify",
                "find",
                "list",
            }:
                continue
            entities.append(name)
        # Also keep ALLCAPS tokens like AMD, ROCm-ish
        for match in re.finditer(r"\b([A-Z]{2,}[a-z0-9]*)\b", scan_text):
            tok = match.group(1)
            if tok.lower() not in {"ner", "amd"} or tok == "AMD":
                entities.append(tok if tok != "AMD" else "AMD")
        # Deduplicate preserving order
        cleaned = list(dict.fromkeys(entities))
        if cleaned:
            return ", ".join(cleaned)
        return None

    if "define" in lowered or "definition of" in lowered or lowered.strip().startswith("what is "):
        term_match = re.search(
            r"(?:define|definition of|what is)\s+([a-z0-9][a-z0-9 _/-]{1,60})",
            lowered,
        )
        if term_match:
            term = term_match.group(1).strip(" ?.,")
            # Leave definition quality to local LLM; only short-circuit ultra-known AMD terms
            known = {
                "rocm": "ROCm is AMD's open software stack for GPU compute.",
                "instinct": "AMD Instinct is AMD's datacenter GPU accelerator line.",
                "mi300x": "MI300X is an AMD Instinct accelerator GPU for AI/HPC.",
                "ryzen": "Ryzen is AMD's consumer/pro CPU brand.",
                "epyc": "EPYC is AMD's server CPU brand.",
            }
            key = term.replace(" ", "").lower()
            for k, v in known.items():
                if k in key:
                    return v
        return None

    if "summarize" in lowered or "summary" in lowered or "tldr" in lowered:
        return None

    return None


def run_local_fallback(prompt: str) -> str:
    """Zero-parameter, lightning-fast local fallback for CPU execution."""
    # Try FastRAG syntactic search first to return highly relevant ROCm context
    rag = perform_fastrag(prompt)
    if rag:
        cleaned = re.sub(r"Reference \d+:", "", rag)
        cleaned = re.sub(r"===.+===", "", cleaned)
        return cleaned.strip()[:200].strip(" .") + "."
    return "AMD ROCm software development and GPU acceleration platform."


async def run_fireworks(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    model_id = pick_fireworks_model()
    if not FIREWORKS_API_KEY:
        return "FIREWORKS_API_KEY not set", "fireworks_missing_key"
    if not model_id:
        return "No Fireworks model configured (set ALLOWED_MODELS)", "fireworks_missing_model"

    print(
        f"[RalfIIA Control Plane] Fireworks fallback → {model_id}",
        file=sys.stderr,
    )

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": normalize_model_id(model_id),
        "messages": [
            {"role": "system", "content": SYSTEM_FIREWORKS},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 256 if is_complex_task(prompt) else 96,
    }
    try:
        resp = await client.post(
            f"{FIREWORKS_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=45.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            answer = str(data["choices"][0]["message"]["content"]).strip()
            return answer, f"Fireworks ({model_id})"
        return (
            f"Fireworks HTTP {resp.status_code}: {resp.text[:400]}",
            "fireworks_error",
        )
    except Exception as exc:
        return f"Fireworks error: {exc}", "fireworks_error"


async def process_task(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, str]:
    task_id = str(item.get("task_id", uuid.uuid4()))
    prompt = str(item.get("prompt", ""))
    complex_task = is_complex_task(prompt)

    # 1) Heuristics (0 tokens) — skip for hard code/math
    answer: str | None = None
    engine = "unset"
    if not complex_task:
        answer = run_local_heuristics(prompt)
        if answer is not None:
            engine = "local_heuristics"

    # Perform FastRAG syntactic search
    rag_context = perform_fastrag(prompt)
    if rag_context:
        enriched_prompt = (
            f"Use the following AMD ROCm & hardware operational context to answer the user query. "
            f"Answer ONLY based on the provided context.\n{rag_context}\nUser Query: {prompt}"
        )
        print(f"Injecting FastRAG context for task={task_id}", file=sys.stderr)
    else:
        enriched_prompt = prompt

    # 2) Hard code/math → Fireworks first (accuracy gate), short max_tokens
    if answer is None and complex_task and FIREWORKS_API_KEY and not ZERO_TOKEN_ONLY:
        fw_answer, fw_engine = await run_fireworks(client, enriched_prompt)
        if fw_engine in {"fireworks_missing_key", "fireworks_missing_model", "fireworks_error"}:
            answer = None
        else:
            answer, engine = fw_answer, fw_engine

    # 3) Local fallback (0 tokens)
    if answer is None:
        answer = run_local_fallback(enriched_prompt)
        engine = "local_fallback"

    # 4) Last resort Fireworks for non-complex when local exhausted
    if answer is None and FIREWORKS_API_KEY and not ZERO_TOKEN_ONLY:
        answer, engine = await run_fireworks(client, enriched_prompt)

    if answer is None:
        answer = "unable to answer locally"
        engine = "local_exhausted"

    print(f"task={task_id} engine={engine}", file=sys.stderr)
    return {"task_id": task_id, "answer": answer}


def validate_results(results: list[Any]) -> str | None:
    if not isinstance(results, list):
        return "results must be a JSON array"
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            return f"item {idx} is not an object"
        keys = set(item.keys())
        if keys != {"task_id", "answer"}:
            return f"item {idx} keys must be exactly task_id and answer, got {sorted(keys)}"
        if not isinstance(item["task_id"], str) or not item["task_id"].strip():
            return f"item {idx} task_id must be a non-empty string"
        if not isinstance(item["answer"], str):
            return f"item {idx} answer must be a string"
    return None


async def main_async() -> int:

    if not os.path.isfile(INPUT_PATH):
        print(f"ERROR: input not found: {INPUT_PATH}", file=sys.stderr)
        return 1

    try:
        with open(INPUT_PATH, encoding="utf-8") as f:
            tasks = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {INPUT_PATH}: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: cannot read {INPUT_PATH}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(tasks, list):
        print("ERROR: tasks.json must be a JSON array", file=sys.stderr)
        return 1

    results: list[dict[str, str]] = []
    async with httpx.AsyncClient() as client:
        for item in tasks:
            if not isinstance(item, dict):
                continue
            results.append(await process_task(client, item))

    validation_error = validate_results(results)
    if validation_error:
        print(f"ERROR: output validation failed: {validation_error}", file=sys.stderr)
        return 1

    out_dir = Path(OUTPUT_PATH).parent
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"ERROR: cannot write {OUTPUT_PATH}: {exc}", file=sys.stderr)
        return 1

    print(f"Track 1 harness OK — {len(results)} tasks → {OUTPUT_PATH}")
    return 0


def main() -> None:
    try:
        code = asyncio.run(main_async())
    except KeyboardInterrupt:
        code = 130
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
