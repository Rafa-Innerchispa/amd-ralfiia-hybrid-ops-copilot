#!/usr/bin/env python3
"""
Track 1 — AMD Hybrid Token-Efficient Routing Agent harness.
Modified to run fully offline (0 tokens) using a local Qwen-0.5B model on CPU.
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

import httpx
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from shared.fireworks_models import normalize_model_id, pick_target_model

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
).rstrip("/")
INPUT_PATH = os.environ.get("HARNESS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("HARNESS_OUTPUT_PATH", "/output/results.json")

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = None
model = None


def load_local_model() -> bool:
    global tokenizer, model
    try:
        print("Loading local Qwen model on CPU...", file=sys.stderr)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            device_map="cpu"
        )
        print("Model loaded successfully!", file=sys.stderr)
        return True
    except Exception as exc:
        print(f"Error loading local model: {exc}", file=sys.stderr)
        return False


def run_local_qwen(prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful, precise NLP assistant. Output only the final exact answer. Do not write explanations, introductions, or markdown formatting unless asked."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to("cpu")
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=48,
        do_sample=True,
        temperature=0.1
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()


def pick_fireworks_model() -> str:
    return pick_target_model(role="complex")


async def run_fireworks(client: httpx.AsyncClient, prompt: str) -> tuple[str, str]:
    model_id = pick_fireworks_model()
    if not FIREWORKS_API_KEY:
        return "FIREWORKS_API_KEY not set", "fireworks_missing_key"
    if not model_id:
        return "No Fireworks model configured (set ALLOWED_MODELS)", "fireworks_missing_model"

    print(
        f"[RalfIIA Control Plane] Directing production request to model target: {model_id}",
        file=sys.stderr,
    )

    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": normalize_model_id(model_id),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        resp = await client.post(
            f"{FIREWORKS_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
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

    answer = None
    engine = "local_qwen"

    if model is not None and tokenizer is not None:
        try:
            answer = run_local_qwen(prompt)
        except Exception as exc:
            print(f"Local Qwen inference failed: {exc}", file=sys.stderr)
            answer = None

    if answer is None:
        answer, engine = await run_fireworks(client, prompt)

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

    # Preload the model once for all tasks
    load_local_model()

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
