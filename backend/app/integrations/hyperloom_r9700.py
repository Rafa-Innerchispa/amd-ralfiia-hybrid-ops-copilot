"""Experimental Hyperloom compatibility layer for Radeon AI PRO R9700 (gfx1201).

This module does NOT claim official Hyperloom support for Radeon AI PRO R9700.
It models what can be executed locally, what can be adapted safely, and what must
remain blocked because current Hyperloom validation targets AMD Instinct runners.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional


OFFICIAL_HYPERLOOM_GPU_TYPES = {"mi300x", "mi308x", "mi325x", "mi355x"}
EXPERIMENTAL_GPU_TYPE = "r9700"
EXPERIMENTAL_GFX = "gfx1201"
REFERENCE_GPU_TYPE = "mi325x"
SESSION_SCHEMA_PREFIX = "hyperloom.session_breakdown.v"


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class HyperloomR9700Plan:
    detected_gpu: str
    gfx_arch: str
    local_runner: str
    reference_runner: str
    official_support: bool
    capabilities: List[Capability]
    blocked_paths: List[str]
    portable_paths: List[str]
    preflight_commands: List[List[str]]
    benchmark_commands: List[List[str]]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = [c.to_dict() for c in self.capabilities]
        return payload


def normalize_gpu_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def is_r9700(name: str, gfx_arch: str) -> bool:
    normalized = normalize_gpu_name(name)
    gfx = (gfx_arch or "").strip().lower()
    return "radeon ai pro r9700" in normalized or gfx == EXPERIMENTAL_GFX


def classify_capabilities() -> List[Capability]:
    return [
        Capability(
            "rocm-runtime",
            "works",
            "R9700/gfx1201 is handled by the local ROCm runtime and can run local inference workloads.",
        ),
        Capability(
            "vllm-baseline",
            "works",
            "Architecture-neutral serving and benchmark loops can run against an existing local vLLM endpoint.",
        ),
        Capability(
            "sglang-baseline",
            "adapted",
            "Can be benchmarked when a gfx1201-compatible SGLang build is present; do not assume availability.",
        ),
        Capability(
            "hyperloom-orchestration-loop",
            "adapted",
            "Think/decide/benchmark/result handling can be mirrored without pretending the GPU is an Instinct runner.",
        ),
        Capability(
            "session-breakdown-v5-consumer",
            "works",
            "Reference Hyperloom session_breakdown v5 results can be parsed as external evidence while tolerating unknown fields.",
        ),
        Capability(
            "magpie-mi30x-runner-scripts",
            "blocked",
            "Current Hyperloom runner scripts target Instinct families and must not be reused as gfx1201 scripts.",
        ),
        Capability(
            "gfx942-gfx950-kernel-artifacts",
            "blocked",
            "Compiled kernels and ISA-specific optimizations for Instinct architectures are not portable to gfx1201.",
        ),
        Capability(
            "official-hyperloom-r9700-runner",
            "upstream_required",
            "Current Hyperloom accepted --gpu-type values do not include R9700/gfx1201.",
        ),
    ]


def build_experimental_plan(
    detected_gpu: str = "AMD Radeon AI PRO R9700",
    gfx_arch: str = EXPERIMENTAL_GFX,
    *,
    vllm_base_url: str = "http://127.0.0.1:8000",
    model: str = "QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ",
) -> HyperloomR9700Plan:
    if not is_r9700(detected_gpu, gfx_arch):
        raise ValueError(f"Unsupported experimental target: gpu={detected_gpu!r} gfx={gfx_arch!r}")

    return HyperloomR9700Plan(
        detected_gpu=detected_gpu,
        gfx_arch=gfx_arch,
        local_runner="experimental-r9700",
        reference_runner=REFERENCE_GPU_TYPE,
        official_support=False,
        capabilities=classify_capabilities(),
        blocked_paths=[
            "Hyperloom --gpu-type r9700 (not accepted upstream)",
            "Magpie vllm_mi30x/sglang_mi30x runner scripts as local Radeon runners",
            "gfx942/gfx950 compiled kernels or kernel patches",
            "claims that MI325X throughput gains apply to R9700 without rebenchmarking",
        ],
        portable_paths=[
            "baseline workload definition",
            "request/concurrency/batching experiments",
            "vLLM/SGLang server-level configuration experiments",
            "latency/throughput/TTFT measurement methodology",
            "optimization action ordering and evidence format",
            "session_breakdown v5 result consumption",
        ],
        preflight_commands=[
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"],
            ["rocminfo"],
            ["curl", "-fsS", f"{vllm_base_url.rstrip('/')}/v1/models"],
        ],
        benchmark_commands=[
            [
                "python3",
                "scripts/hyperloom_r9700_benchmark.py",
                "--base-url",
                vllm_base_url,
                "--model",
                model,
                "--mode",
                "baseline",
            ],
            [
                "python3",
                "scripts/hyperloom_r9700_benchmark.py",
                "--base-url",
                vllm_base_url,
                "--model",
                model,
                "--mode",
                "candidate",
            ],
        ],
    )


def parse_session_breakdown(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Parse Hyperloom session breakdown evidence conservatively.

    Hyperloom v5 is the expected current wire shape. Unknown fields are preserved
    rather than rejected, because minor additions are explicitly allowed by the
    upstream contract. Missing values are never fabricated.
    """
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.startswith(SESSION_SCHEMA_PREFIX):
        raise ValueError("Not a recognized Hyperloom session_breakdown payload")

    major_text = schema_version[len(SESSION_SCHEMA_PREFIX):].split(".", 1)[0]
    try:
        major = int(major_text)
    except ValueError as exc:
        raise ValueError(f"Invalid Hyperloom schema version: {schema_version}") from exc

    optimizations = payload.get("optimizations")
    if optimizations is None:
        optimizations = []
    if not isinstance(optimizations, list):
        raise ValueError("optimizations must be a list or null")

    return {
        "schema_version": schema_version,
        "schema_major": major,
        "supported_reader": major >= 5,
        "exporter_version": payload.get("exporter_version"),
        "optimizations": optimizations,
        "raw": dict(payload),
    }


def capability_matrix(capabilities: Optional[Iterable[Capability]] = None) -> Dict[str, str]:
    items = list(capabilities or classify_capabilities())
    return {item.name: item.status for item in items}
