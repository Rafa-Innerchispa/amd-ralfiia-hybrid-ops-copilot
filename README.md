# InnerOS Sovereign AI Fabric — Hyperloom on Radeon AI PRO R9700

Experimental AMD Lab Program Challenge 1 project based on the existing `amd-ralfiia-hybrid-ops-copilot` platform.

## Challenge 1 focus

**Goal:** explore and implement a truthful experimental compatibility layer between Hyperloom and the AMD Radeon AI PRO R9700 (`gfx1201`).

Current Hyperloom validation targets AMD Instinct runner families. This project does **not** claim official R9700 support. Instead, it separates:

- architecture-neutral optimization workflow components that already work locally,
- components that can be adapted safely,
- Instinct/CDNA-specific paths that must remain blocked,
- changes that would require upstream Hyperloom support.

See [`docs/HYPERLOOM_R9700.md`](docs/HYPERLOOM_R9700.md).

## Verified local AMD stack

- AMD Radeon AI PRO R9700, 32 GB VRAM
- `gfx1201` / RDNA4
- ROCm 10 canary runtime
- vLLM local serving
- Qwen3-Coder local model
- MCP/A2A orchestration through InnerOS
- DigitalOcean AMD Instinct integration retained as an optional reference path, with no promotional credits assumed and no cloud spend required for Challenge 1

## Experimental compatibility adapter

`backend/app/integrations/hyperloom_r9700.py` provides:

- R9700 / `gfx1201` detection
- capability classification: `works`, `adapted`, `blocked`, `upstream_required`
- architecture-neutral preflight and benchmark plans
- explicit blocks for MI30x-specific runner scripts and `gfx942/gfx950` kernel artifacts
- conservative Hyperloom `session_breakdown` evidence parsing
- separation between `experimental-r9700` local runner and `mi325x` reference runner

Run the focused tests:

```bash
python3 -m pytest tests/test_hyperloom_r9700.py -q
```

## Original platform

The repository originated as the RalphiIA Hybrid Ops Copilot for AMD ACT II and already includes multi-agent operations, A2A communication, hybrid runtime integrations, Smart Quoter and Watchdog agents.

## Important truthfulness boundary

This repository must never represent the experimental R9700 adapter as official Hyperloom support unless AMD adds `gfx1201` upstream. Performance results from MI325X or other Instinct GPUs must be re-benchmarked locally before they are claimed for R9700.
