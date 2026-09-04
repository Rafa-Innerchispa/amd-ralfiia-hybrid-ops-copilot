# AMD Lab Program — Challenge 1 Status

## Project
**Hyperloom on Radeon AI PRO R9700 (`gfx1201`)**

Builder-path experiment inside the existing InnerOS / RalfIIA AMD hybrid ops copilot.

## Goal
Determine how much of the Hyperloom optimization workflow can be safely adapted to a Radeon AI PRO R9700 without pretending that upstream Hyperloom officially supports `gfx1201`.

The experiment separates:

- **WORKS** — already supported by the local ROCm / inference stack.
- **ADAPTED** — architecture-neutral Hyperloom ideas that can be reproduced locally.
- **BLOCKED** — Instinct/CDNA-specific paths that must not be reused on RDNA4.
- **UPSTREAM_REQUIRED** — capabilities that need official Hyperloom changes before they can be called supported.

## Verified local hardware/runtime evidence

Observed on the AMD node on 2026-09-04:

- GPU: AMD Radeon AI PRO R9700
- VRAM: 34,208,743,424 bytes (~32 GiB)
- LLVM/GFX target: `gfx1201`
- Runtime container: `rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0`
- PyTorch: `2.12.0+rocm10.0.0`
- vLLM: `0.27.1.dev5+gf46a9dfe2.d20260827.rocm100`
- Active model: `QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ`
- vLLM bind: `127.0.0.1:8000`

This is a real local ROCm 10 inference runtime, not a simulated environment.

## Implemented in this branch

1. `backend/app/integrations/hyperloom_r9700.py`
   - R9700/gfx1201 detection
   - capability classification
   - portable-vs-blocked path model
   - conservative Hyperloom session breakdown parser

2. `scripts/hyperloom_r9700_benchmark.py`
   - reproducible OpenAI-compatible inference benchmark
   - deterministic temperature 0 prompt suite
   - latency and completion throughput metrics
   - baseline/candidate modes
   - JSON evidence output

3. Tests
   - capability contract tests
   - session evidence parsing tests
   - benchmark summary tests

## Current test evidence

- `7 passed`
- `git diff --check` PASS
- branch pushed to GitHub
- Draft PR #2 open

## Live benchmark plan

The benchmark must run on the AMD node because the production vLLM endpoint is intentionally bound to loopback (`127.0.0.1:8000`).

Planned command:

```bash
python3 scripts/hyperloom_r9700_benchmark.py \
  --base-url http://127.0.0.1:8000 \
  --model QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ \
  --mode baseline \
  --repeat 3 \
  --output evidence/r9700-baseline.json
```

Then repeat with one architecture-neutral candidate configuration and compare:

- mean latency
- p50 latency
- p95 latency
- completion tokens/s
- sequential effective output tokens/s
- correctness / finish behavior

## Current control-plane blockers

These are InnerOS orchestration/tooling blockers, not R9700 failures:

1. `local_model_benchmark` currently emits only a dry-run fixture even while real vLLM is healthy.
2. canonical `run_local_model` still routes to stale `127.0.0.1:18000` while the real AMD vLLM is on `:8000`.
3. `peer_python_runtime` does not allow safe execution of a repo-owned Python script, only status/venv/pip/compileall/pytest.
4. `peer_project_fs` write on the AMD repo returns helper code `126` despite correct project registry and allowed paths.
5. Dev Swarm task envelope still loses repo/binding metadata and produces `blocked_missing_task_binding`.

All five are tracked as control-plane repair work for Codex. They must not be misreported as Hyperloom/R9700 incompatibility.

## Success criteria for Challenge 1

Challenge 1 can be considered technically complete when:

1. The experimental R9700 compatibility layer is reproducible from the public repo.
2. A real baseline benchmark is captured on the local R9700/ROCm 10 runtime.
3. At least one architecture-neutral candidate optimization is benchmarked against the baseline, or the exact upstream/tool blocker is documented with evidence.
4. Instinct-only paths remain explicitly blocked rather than silently reused.
5. The public README/PR clearly states that this is experimental compatibility research, not official Hyperloom R9700 support.
6. LabLab Builder submission references the repo, tests, benchmark evidence, and findings.

## Cloud policy

No AMD promotional credit is assumed. The owner confirmed the account is existing and the $100 new-account promotion is unavailable. DigitalOcean MI325X remains an optional, owner-approved reference runner only; no cloud spend is required for the R9700 compatibility experiment itself.
