# AMD Lab Program — Challenge 1 Builder Submission Draft

## Project title

**Hyperloom on Radeon AI PRO R9700 — Experimental RDNA4 Compatibility for Local AI Optimization**

## One-line pitch

We extended AMD Hyperloom's architecture-neutral benchmark path to recognize and run on the Radeon AI PRO R9700 (`gfx1201`), a ROCm 10-capable RDNA4 GPU that Hyperloom does not currently expose as an official runner.

## Problem

Hyperloom's upstream GPU identity/runner support is centered on AMD Instinct families. Radeon AI PRO R9700 already runs serious local AI workloads with ROCm 10 and vLLM, but cannot currently be selected as a Hyperloom GPU type. The gap is software support, not simply VRAM capacity.

## What we built

1. Experimental `r9700 -> gfx1201 / 64 CU` Hyperloom identity support.
2. R9700 product-name and `gfx1201` autodetection.
3. A capability matrix separating architecture-neutral functionality from Instinct/CDNA-specific paths.
4. A live integration using Hyperloom's own `bypass` benchmark backend with InferenceX.
5. Reproducible baseline/candidate measurements against the existing ROCm 10 vLLM server on the physical R9700.
6. Auditable evidence and comparison tooling that explicitly prevents overclaiming Instinct kernel portability.

## AMD technology used

- AMD Radeon AI PRO R9700, RDNA4, `gfx1201`, 64 CU
- ROCm 10 runtime container
- PyTorch `2.12.0+rocm10.0.0`
- vLLM `0.27.1.dev5` ROCm build
- Qwen3-Coder 30B local inference
- AMD Hyperloom upstream commit `9ae79d6a8c9fec7ed041735e70fb19ef39850813`
- Hyperloom `bypass` benchmark backend
- InferenceX benchmark workload

## Why this is technically interesting

We did not pretend the R9700 is an MI300X. Hyperloom's GPU identity, architecture mapping, benchmark execution and architecture-specific optimization layers remain separate.

The experimental port adds:

```text
r9700 -> gfx1201, 64 CU
gfx1201 -> r9700
```

The first live path deliberately uses Hyperloom's architecture-neutral `bypass` backend. Instinct-specific Magpie scripts, TraceLens assumptions and `gfx942/gfx950` kernels remain gated until they are reimplemented or independently validated for RDNA4.

## Live results on the physical R9700

### Patched Hyperloom preflight

**PASS**

- `rocm-smi` product detection: Radeon AI PRO R9700
- Hyperloom autodetection: `r9700`
- dispatch identity: `gfx1201`, 64 CU
- `bypass` backend eligibility: PASS

### Baseline

Fixed workload: ISL=32, OSL=32, concurrency=1.

- Hyperloom report success: **true**
- completed: **10/10** requests
- output throughput: **21.7953 tok/s**
- total token throughput: **43.5905 tok/s**
- mean TTFT: **68.47 ms**
- mean E2E: **1467.81 ms**

### Candidate

Same GPU/model/server/workload shape, concurrency=2.

- Hyperloom report success: **true**
- completed: **20/20** requests
- output throughput: **36.5927 tok/s**
- total token throughput: **73.1854 tok/s**
- mean TTFT: **121.06 ms**
- mean E2E: **1746.44 ms**

### Result

Aggregate output throughput increased **67.89%** when moving from concurrency 1 to 2.

This is intentionally reported as **throughput/workload tuning**, not as a universal 67.89% GPU speedup. Latency increased with concurrency. The useful result is that the patched Hyperloom path can now execute, measure and compare real candidate configurations on an R9700.

## Current status

### Proven

- upstream-style R9700 identity patch
- R9700/gfx1201 live autodetection
- focused upstream tests PASS
- Hyperloom `bypass` backend running on physical R9700
- real InferenceX workload execution
- successful Hyperloom baseline report
- successful Hyperloom candidate report
- reproducible A/B comparison

### Still experimental / not claimed

- official AMD support
- Magpie-specific R9700 runner
- TraceLens profiling on RDNA4
- RDNA4 kernel optimization
- portability of MI300X/MI325X compiled kernels
- full autonomous Think → Decide → Implement Hyperloom optimization session

## Success criteria

The minimum Challenge 1 criteria are now met:

- Hyperloom accepts/detects R9700 through the experimental port: **PASS**
- valid live baseline on R9700: **PASS**
- architecture-neutral candidate benchmark/compare: **PASS**
- measurable throughput change with honest interpretation: **PASS**

The next stretch phase is full autonomous optimization and deeper RDNA4 profiler/kernel support.

## Repository evidence

Primary repository: `Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot`

Branch: `local-agent/hyperloom-r9700-port`

PR: `#2`

Issue: `#1`

Experimental upstream-style repo: `Rafa-Innerchispa/hyperloom-r9700-experimental`

Raw live evidence: `docs/evidence/hyperloom_r9700_live_ab_20260904.json`

Evidence map: `docs/EVIDENCE_INDEX.md`

## What we learned

The R9700's 32 GB-class memory is not the reason Hyperloom excluded it. The practical boundary is the supported GPU identity/runner/profiling/kernel stack. Hyperloom already contains an architecture-neutral benchmark seam (`bypass`) that makes a staged RDNA4 port viable: first identity + benchmark orchestration, then profiling, then architecture-specific optimization.
