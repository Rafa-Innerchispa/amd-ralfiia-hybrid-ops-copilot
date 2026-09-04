#!/usr/bin/env python3
"""Reproducible OpenAI-compatible benchmark for the Hyperloom-on-R9700 experiment.

Runs against a local vLLM/SGLang endpoint. It does not change server settings and
never assumes Hyperloom officially supports Radeon AI PRO R9700.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_PROMPTS = [
    "Return exactly this JSON object and nothing else: {\"status\":\"ok\",\"value\":1}",
    "In one sentence, explain why deterministic benchmarks matter for GPU inference optimization.",
    "Write a Python function named add(a, b) that returns a+b. No prose.",
]


@dataclass
class Sample:
    prompt_index: int
    latency_ms: float
    output_tokens: int
    prompt_tokens: int
    total_tokens: int
    tokens_per_second: float
    finish_reason: str


def _post_json(url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * p))
    return ordered[index]


def run(args: argparse.Namespace) -> Dict[str, Any]:
    samples: List[Sample] = []
    endpoint = args.base_url.rstrip("/") + "/v1/chat/completions"
    prompts = DEFAULT_PROMPTS * args.repeat

    started = datetime.now(timezone.utc).isoformat()
    for index, prompt in enumerate(prompts):
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": args.max_tokens,
            "stream": False,
        }
        t0 = time.perf_counter()
        response = _post_json(endpoint, payload, args.timeout)
        elapsed = time.perf_counter() - t0
        usage = response.get("usage") or {}
        completion = int(usage.get("completion_tokens") or 0)
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        total = int(usage.get("total_tokens") or completion + prompt_tokens)
        choice = (response.get("choices") or [{}])[0]
        samples.append(
            Sample(
                prompt_index=index,
                latency_ms=elapsed * 1000,
                output_tokens=completion,
                prompt_tokens=prompt_tokens,
                total_tokens=total,
                tokens_per_second=(completion / elapsed) if elapsed > 0 and completion else 0.0,
                finish_reason=str(choice.get("finish_reason") or ""),
            )
        )

    latencies = [s.latency_ms for s in samples]
    throughputs = [s.tokens_per_second for s in samples if s.tokens_per_second > 0]
    output_tokens = sum(s.output_tokens for s in samples)
    wall_seconds = sum(s.latency_ms for s in samples) / 1000
    result = {
        "schema_version": "inneros.hyperloom_r9700_benchmark.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started,
        "mode": args.mode,
        "target": {
            "base_url": args.base_url,
            "model": args.model,
            "gpu_claim": "AMD Radeon AI PRO R9700",
            "gfx_claim": "gfx1201",
            "official_hyperloom_support": False,
        },
        "config": {
            "repeat": args.repeat,
            "requests": len(samples),
            "temperature": 0,
            "max_tokens": args.max_tokens,
        },
        "summary": {
            "requests": len(samples),
            "output_tokens": output_tokens,
            "mean_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
            "p50_latency_ms": _percentile(latencies, 0.50),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "mean_completion_tokens_per_second": statistics.fmean(throughputs) if throughputs else 0.0,
            "sequential_effective_output_tokens_per_second": (output_tokens / wall_seconds) if wall_seconds > 0 else 0.0,
        },
        "samples": [asdict(sample) for sample in samples],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=("baseline", "candidate"), default="baseline")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")

    try:
        result = run(args)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "detail": str(exc)}))
        return 2

    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
