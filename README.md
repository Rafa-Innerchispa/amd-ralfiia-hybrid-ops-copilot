# InnerOS Sovereign AI Fabric — Hyperloom on Radeon AI PRO R9700

AMD Lab Program Challenge 1 (Builder) project based on the existing `amd-ralfiia-hybrid-ops-copilot` platform.

## Challenge 1 focus

**Goal:** extend/adapt Hyperloom's inference-optimization workflow to the AMD Radeon AI PRO R9700 (`gfx1201`), a ROCm-capable local AI GPU that Hyperloom does not currently expose as an official runner.

This project does **not** claim official R9700 support. It separates:

- architecture-neutral optimization workflow components that work or can be reused locally,
- components that can be adapted safely,
- Instinct/CDNA-specific paths that must remain blocked until revalidated,
- changes that require an upstream Hyperloom port.

## Verified local AMD stack

- AMD Radeon AI PRO R9700, 32 GB VRAM
- RDNA4 / `gfx1201` / 64 Compute Units
- ROCm 10 runtime
- PyTorch ROCm build
- vLLM ROCm serving
- Qwen3-Coder local model
- MCP/A2A orchestration through InnerOS
- DigitalOcean AMD Instinct integration retained only as an optional supported-reference path; Challenge 1 assumes **no promotional AMD cloud credit**

## What is implemented

### Experimental compatibility adapter

`backend/app/integrations/hyperloom_r9700.py`

- R9700 / `gfx1201` detection
- `works / adapted / blocked / upstream_required` capability classification
- architecture-neutral preflight and benchmark planning
- explicit blocks for MI/CDNA-specific artifacts
- conservative Hyperloom session evidence parsing

### Reproducible benchmark + comparison

- `scripts/hyperloom_r9700_benchmark.py`
- `scripts/compare_hyperloom_benchmarks.py`

These produce raw JSON for baseline/candidate measurements and calculate performance deltas without inventing missing metrics.

Run focused tests:

```bash
python3 -m pytest \
  tests/test_hyperloom_r9700.py \
  tests/test_hyperloom_r9700_benchmark.py \
  tests/test_compare_hyperloom_benchmarks.py -q
```

Current branch evidence: **10 tests PASS**.

## Challenge evidence

- [`docs/EVIDENCE_INDEX.md`](docs/EVIDENCE_INDEX.md) — canonical verified/implemented/measured/pending map
- [`docs/BUILDER_SUBMISSION.md`](docs/BUILDER_SUBMISSION.md) — Builder submission draft
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — 2–3 minute demo flow
- [`docs/HYPERLOOM_R9700.md`](docs/HYPERLOOM_R9700.md) — compatibility design
- [`docs/upstream/HYPERLOOM_R9700_PATCH_PLAN.md`](docs/upstream/HYPERLOOM_R9700_PATCH_PLAN.md) — candidate upstream port
- `ui/public/hyperloom.html` — dedicated Challenge 1 evidence page

Public development tracking:

- GitHub Issue **#1** — R9700 Hyperloom runner experiment
- Draft PR **#2** — Challenge 1 implementation

## Current truthfulness boundary

The compatibility layer, test suite and benchmark tooling are implemented. **Full Hyperloom execution on the R9700 has not yet been proven.** A full-success claim requires a real patched-R9700 baseline and at least one rebenchmark/candidate cycle on the GPU.

Do not represent MI325X/MI300X kernel or throughput results as R9700 results without local revalidation.

## Original platform

This repository originated as the RalphiIA Hybrid Ops Copilot for AMD ACT II and includes multi-agent operations, A2A communication, hybrid runtime integrations, Smart Quoter and Watchdog agents. Challenge 1 deliberately reuses that real platform instead of creating an isolated disposable demo.
