# Challenge 1 Evidence Index — Hyperloom on Radeon AI PRO R9700

This file is the canonical evidence map for AMD Lab Program Challenge 1 (Builder path). It separates **verified facts**, **implemented code**, **measured evidence**, and the remaining upstream limitations.

## 1. Challenge claim

**Goal:** extend/adapt Hyperloom's inference-optimization workflow to an AMD Radeon AI PRO R9700 (`gfx1201`) that is not an officially supported Hyperloom runner in the current upstream release.

The project does **not** claim official AMD Hyperloom support for R9700. It demonstrates an experimental R9700 identity/autodetection port plus a live architecture-neutral Hyperloom `bypass` benchmark path on RDNA4.

## 2. Verified hardware/runtime evidence

Status: **VERIFIED**

- GPU: AMD Radeon AI PRO R9700
- ROCm target: `gfx1201`
- VRAM reported by `rocm-smi`: 34,208,743,424 bytes (32 GiB class)
- Compute Units: 64
- Local runtime container: `rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0`
- PyTorch: `2.12.0+rocm10.0.0`
- vLLM: `0.27.1.dev5+gf46a9dfe2.d20260827.rocm100`
- Model: `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`
- Existing local endpoint: `http://127.0.0.1:8000`

Evidence source: live InnerOS probes on AMD node `.5`, 2026-09-04.

## 3. Upstream Hyperloom support boundary

Status: **VERIFIED UPSTREAM LIMITATION**

Current upstream Hyperloom accepts Instinct identities (`mi300x`, `mi308x`, `mi325x`, `mi355x`) through `AMD_GPU_DISPATCH_IDENTITIES`. R9700 is absent upstream.

Experimental patch used for this challenge:

```python
"r9700": ("gfx1201", 64)
```

and:

```python
"gfx1201": "r9700"
```

Relevant upstream files:

- `src/hyperloom/common/gpu_identity.py`
- `src/hyperloom/inference_optimizer/gpu_types.py`

Exact upstream base tested: `9ae79d6a8c9fec7ed041735e70fb19ef39850813`.

## 4. Live Hyperloom execution on physical R9700

Status: **PASS — EXPERIMENTAL**

The patched Hyperloom code was executed on AMD node `.5`, not merely unit-tested.

### Live preflight

- `rocm-smi` detected `AMD Radeon AI PRO R9700`
- autodetected Hyperloom GPU type: `r9700`
- dispatch identity: `gfx1201`, 64 CU
- benchmark backend: `bypass`
- vLLM lifecycle eligibility: PASS
- process return code: 0

### Live baseline/candidate benchmark

Hyperloom's `bypass_runner` executed against the existing ROCm 10 vLLM endpoint. InferenceX generated the benchmark workload and Hyperloom wrote real `benchmark_report.json` artifacts.

Fixed workload for both runs:

- ISL: 32
- OSL: 32
- `RANDOM_RANGE_RATIO=1.0`
- accuracy eval disabled for the throughput experiment
- same GPU, model, server and endpoint

#### Baseline — concurrency 1

- success: **true**
- completed requests: **10/10**
- output throughput: **21.7953 tok/s**
- total token throughput: **43.5905 tok/s**
- mean TTFT: **68.47 ms**
- mean TPOT: **45.14 ms**
- mean E2E: **1467.81 ms**

#### Candidate — concurrency 2

- success: **true**
- completed requests: **20/20**
- output throughput: **36.5927 tok/s**
- total token throughput: **73.1854 tok/s**
- mean TTFT: **121.06 ms**
- mean TPOT: **52.43 ms**
- mean E2E: **1746.44 ms**

#### Comparison

- output throughput gain: **+67.89%**

Important interpretation: the candidate improves **aggregate throughput by increasing concurrency** while latency increases. This is a workload/concurrency tuning result. It is **not** a claim that the R9700 became universally 67.89% faster and it is not a kernel optimization.

Canonical raw evidence:

`docs/evidence/hyperloom_r9700_live_ab_20260904.json`

## 5. Implemented Challenge 1 code

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

### Baseline/candidate comparator

`scripts/compare_hyperloom_benchmarks.py`

## 6. Automated test evidence

Status: **PASS**

Challenge repo focused tests: **10/10 PASS** at the latest packaged run.

Upstream-style experimental patch focused tests: **11/11 PASS**.

Live patched preflight: **PASS**.

Live Hyperloom bypass baseline: **PASS**.

Live Hyperloom bypass candidate: **PASS**.

## 7. Git evidence

Status: **PUBLIC / REVIEWABLE**

Primary challenge repository:

`Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot`

Challenge branch:

`local-agent/hyperloom-r9700-port`

Pull Request:

- PR #2 — Challenge 1: experimental Hyperloom compatibility for Radeon AI PRO R9700

Tracking issue:

- Issue #1 — Hyperloom runner for Radeon AI PRO R9700 (`gfx1201`)

Experimental upstream-style repository:

`Rafa-Innerchispa/hyperloom-r9700-experimental`

Temporary live harness repositories are evidence tooling only and are not the submitted product.

## 8. What is proven now

The following statement is supported by live evidence:

> A patched Hyperloom build can recognize the Radeon AI PRO R9700 as `r9700/gfx1201`, use Hyperloom's architecture-neutral `bypass` benchmark path, execute real InferenceX workloads against a ROCm 10 vLLM server on the physical R9700, and produce successful Hyperloom benchmark reports for baseline and candidate configurations.

## 9. What is NOT yet claimed

- official AMD Hyperloom support for R9700
- Magpie R9700 runner support
- TraceLens profiling on R9700
- RDNA4 kernel optimization support
- portability of MI300X/MI325X `gfx942` kernels to `gfx1201`
- a full autonomous Hyperloom Think → Decide → Implement optimization session on R9700

Those are Phase 2 work, not hidden behind a fake PASS.
