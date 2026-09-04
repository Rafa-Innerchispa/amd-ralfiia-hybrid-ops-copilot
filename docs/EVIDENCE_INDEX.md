# Challenge 1 Evidence Index — Hyperloom on Radeon AI PRO R9700

This file is the canonical evidence map for AMD Lab Program Challenge 1 (Builder path).
It distinguishes **verified facts**, **implemented code**, **measured evidence**, and **pending validation** so reviewers do not have to infer what is real.

## 1. Challenge claim

**Goal:** extend/adapt Hyperloom's inference-optimization workflow to an AMD Radeon AI PRO R9700 (`gfx1201`) that is not an officially supported Hyperloom runner in the current upstream release.

The project does **not** claim official AMD Hyperloom support for R9700. It explores the minimal compatibility layer required to make architecture-neutral Hyperloom concepts usable on RDNA4 while explicitly blocking Instinct/CDNA-specific artifacts.

## 2. Verified hardware/runtime evidence

Status: **VERIFIED**

- GPU: AMD Radeon AI PRO R9700
- ROCm target: `gfx1201`
- VRAM reported by `rocm-smi`: 34,208,743,424 bytes (32 GiB class)
- Compute Units: 64 (AMD public specification)
- Local runtime container: `rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0`
- PyTorch: `2.12.0+rocm10.0.0`
- HIP runtime reported by torch: `7.15.26333`
- vLLM: `0.27.1.dev5+gf46a9dfe2.d20260827.rocm100`
- Model: `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`

Evidence source: InnerOS local runtime probe on AMD node `.5`, 2026-09-04.

## 3. Upstream Hyperloom support boundary

Status: **VERIFIED UPSTREAM LIMITATION**

Current Hyperloom accepts these GPU types:

- `mi300x`
- `mi308x`
- `mi325x`
- `mi355x`

Upstream derives CLI choices from `AMD_GPU_DISPATCH_IDENTITIES`. The current table contains only Instinct identities (`gfx942` / `gfx950`). R9700 is therefore rejected before a true `r9700` runner can be selected.

Relevant upstream files:

- `src/hyperloom/common/gpu_identity.py`
- `src/hyperloom/inference_optimizer/gpu_types.py`
- `src/hyperloom/inference_optimizer/cli/parser.py`

## 4. Implemented Challenge 1 code

Status: **IMPLEMENTED + TESTED**

### Compatibility layer

`backend/app/integrations/hyperloom_r9700.py`

- detects R9700 / `gfx1201`
- exposes capability matrix: `works`, `adapted`, `blocked`, `upstream_required`
- preserves supported Instinct reference path (`mi325x`)
- blocks reuse of `gfx942/gfx950` compiled kernels as if they were portable
- parses Hyperloom session evidence conservatively

### Reproducible benchmark harness

`scripts/hyperloom_r9700_benchmark.py`

- OpenAI-compatible local endpoint benchmark
- deterministic prompts (`temperature=0`)
- latency, token counts and effective completion throughput
- raw JSON output suitable for audit
- `baseline` and `candidate` modes

### Baseline/candidate comparator

`scripts/compare_hyperloom_benchmarks.py`

- rejects model/GPU mismatches
- computes throughput gain and latency improvement
- never claims a gain when baseline is missing/zero
- explicit gate for a 10% throughput target

## 5. Automated test evidence

Status: **PASS**

Test suites:

- `tests/test_hyperloom_r9700.py`
- `tests/test_hyperloom_r9700_benchmark.py`
- `tests/test_compare_hyperloom_benchmarks.py`

The latest passing count must be refreshed after every commit. A PASS claim is valid only when the branch test command and Git SHA are recorded in the PR.

## 6. Git evidence

Status: **PUBLIC / REVIEWABLE**

Repository:

`Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot`

Challenge branch:

`local-agent/hyperloom-r9700-port`

Key commits so far:

- `1145605` — experimental Hyperloom R9700 compatibility layer
- `6711fd1` — reproducible R9700 inference benchmark harness
- `0eb3645` — Challenge 1 evidence and completion criteria

Pull Request:

- PR #2 — Challenge 1: experimental Hyperloom compatibility for Radeon AI PRO R9700

Tracking issue:

- Issue #1 — Hyperloom runner for Radeon AI PRO R9700 (`gfx1201`)

## 7. Evidence still required before claiming full success

Status: **PENDING**

1. Run `baseline` against the live local R9700 vLLM endpoint.
2. Apply one architecture-neutral candidate optimization.
3. Run `candidate` using identical workload/model constraints.
4. Generate comparison JSON.
5. Attempt patched Hyperloom preflight with `r9700` identity/runner.
6. Record the exact first upstream subsystem that fails, if any.
7. If Hyperloom reaches baseline/explore/rebenchmark, save its session artifacts.

Until those steps exist, the correct statement is:

> The R9700 compatibility layer and benchmark workflow are implemented and tested, but full Hyperloom execution on the R9700 has not yet been proven.

## 8. Evidence directory convention

Live evidence should be stored without secrets under:

```text
docs/evidence/
  environment.json
  baseline.json
  candidate.json
  comparison.json
  hyperloom_preflight.txt
  hyperloom_session_summary.json
```

Missing evidence files are intentional until the corresponding real run occurs. Never commit fabricated metrics to fill a slot.
