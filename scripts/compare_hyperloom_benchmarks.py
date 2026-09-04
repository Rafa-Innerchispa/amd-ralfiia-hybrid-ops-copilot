#!/usr/bin/env python3
"""Compare two Hyperloom-on-R9700 benchmark JSON files.

The script never invents an improvement. It requires comparable benchmark
schemas and emits deltas for latency and throughput so Challenge 1 evidence can
be audited from raw JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

SCHEMA = "inneros.hyperloom_r9700_benchmark.v1"


def _load(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA:
        raise ValueError(f"unsupported benchmark schema in {path}")
    return data


def _pct(new: float, old: float, *, lower_is_better: bool = False) -> float | None:
    if old == 0:
        return None
    raw = ((new - old) / old) * 100.0
    return -raw if lower_is_better else raw


def compare(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    b_target = baseline.get("target") or {}
    c_target = candidate.get("target") or {}
    if b_target.get("model") != c_target.get("model"):
        raise ValueError("model mismatch")
    if b_target.get("gfx_claim") != c_target.get("gfx_claim"):
        raise ValueError("GPU architecture mismatch")

    b = baseline.get("summary") or {}
    c = candidate.get("summary") or {}
    b_tput = float(b.get("sequential_effective_output_tokens_per_second") or 0)
    c_tput = float(c.get("sequential_effective_output_tokens_per_second") or 0)
    b_lat = float(b.get("mean_latency_ms") or 0)
    c_lat = float(c.get("mean_latency_ms") or 0)

    throughput_gain = _pct(c_tput, b_tput)
    latency_improvement = _pct(c_lat, b_lat, lower_is_better=True)
    return {
        "schema_version": "inneros.hyperloom_r9700_comparison.v1",
        "target": {
            "model": b_target.get("model"),
            "gpu": b_target.get("gpu_claim"),
            "gfx": b_target.get("gfx_claim"),
            "official_hyperloom_support": False,
        },
        "baseline": {
            "throughput_tps": b_tput,
            "mean_latency_ms": b_lat,
        },
        "candidate": {
            "throughput_tps": c_tput,
            "mean_latency_ms": c_lat,
        },
        "delta": {
            "throughput_gain_percent": throughput_gain,
            "latency_improvement_percent": latency_improvement,
        },
        "claim_gate": {
            "measured": b_tput > 0 and c_tput > 0,
            "improved": bool(throughput_gain is not None and throughput_gain > 0),
            "ten_percent_target_met": bool(throughput_gain is not None and throughput_gain >= 10.0),
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("baseline")
    p.add_argument("candidate")
    p.add_argument("--output", default="")
    args = p.parse_args()
    try:
        result = compare(_load(args.baseline), _load(args.candidate))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "detail": str(exc)}))
        return 2
    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
