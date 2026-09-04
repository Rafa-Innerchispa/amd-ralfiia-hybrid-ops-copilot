# AMD Lab Program — Challenge 1 Builder Submission Draft

## Project title

**Hyperloom on Radeon AI PRO R9700 — Experimental RDNA4 Compatibility for Local AI Optimization**

## One-line pitch

We are adapting AMD Hyperloom's autonomous inference-optimization workflow to the Radeon AI PRO R9700 (`gfx1201`), a ROCm 10-capable 32 GB RDNA4 GPU that Hyperloom does not currently expose as an official runner.

## Problem

Hyperloom's current stable runner list targets AMD Instinct GPUs. The Radeon AI PRO R9700 is already a capable local-AI development GPU under ROCm, but it cannot currently be selected as a Hyperloom target. This leaves a gap between affordable local Radeon AI development and AMD's autonomous inference optimization stack.

## What we built

1. An experimental R9700/gfx1201 compatibility layer with explicit feature detection.
2. A capability matrix that separates architecture-neutral functionality from Instinct/CDNA-specific paths.
3. A reproducible local vLLM benchmark harness for baseline and candidate runs.
4. A benchmark comparator that generates auditable throughput/latency deltas and refuses unsupported claims.
5. A proposed minimal upstream port path based on Hyperloom's central GPU identity table and runner mapping.
6. A Challenge 1 evidence dashboard/documentation layer tied to real commits, tests, and runtime probes.

## AMD technology used

- AMD Radeon AI PRO R9700, RDNA4, 32 GB VRAM, `gfx1201`
- ROCm 10
- PyTorch ROCm build
- vLLM ROCm build
- Qwen3-Coder local inference
- Hyperloom 1.0 architecture and runner contracts
- AMD Instinct MI325X retained as the officially supported reference path for comparison, without requiring cloud spend for the local Challenge 1 work

## Why this is technically interesting

The project is not a wrapper that renames the R9700 as an MI300X. Hyperloom uses a central GPU dispatch identity table, GPU-type resolution, runner selection, benchmark scripts, profiling, and architecture-specific optimization paths. We preserve that separation.

For R9700 we propose:

- `r9700 -> gfx1201, 64 CU`
- a dedicated `r9700` runner label
- dedicated/custom vLLM benchmark script
- reuse of architecture-neutral orchestration and serving-parameter search
- explicit disabling/revalidation of CDNA-specific kernels and profiling assumptions

## Current status

### Proven

- R9700 detected as `gfx1201`
- ROCm 10 + vLLM local runtime is operational
- compatibility adapter implemented
- benchmark and comparison harness implemented
- automated tests passing
- code published in a public GitHub branch and draft PR

### Not yet claimed

Full upstream Hyperloom execution on R9700 is **not yet proven**. The next validation is to run a patched `r9700` preflight/baseline on the actual AMD node and capture the first hard incompatibility, or the successful optimization loop if it runs.

## Success criteria

Minimum success:

- Hyperloom accepts/detects R9700 through an experimental port.
- A valid local baseline is produced on R9700.
- Architecture-neutral candidate settings can be benchmarked and compared reproducibly.

Stretch success:

- Hyperloom completes an explore/rebenchmark loop on R9700.
- We produce a measurable throughput improvement while preserving correctness.
- The port is clean enough to propose upstream to AMD-AGI/Hyperloom.

## Repository evidence

Repository: `Rafa-Innerchispa/amd-ralfiia-hybrid-ops-copilot`

Branch: `local-agent/hyperloom-r9700-port`

PR: `#2`

Issue: `#1`

Detailed evidence map: `docs/EVIDENCE_INDEX.md`

## What we learned

The main limitation is not the R9700's 32 GB VRAM. ROCm 10 recognizes the GPU and local inference runs successfully. The current limitation is Hyperloom's runner/tooling support boundary: accepted GPU identities, benchmark runner scripts, profiling assumptions, and architecture-specific kernels are presently centered on Instinct families. That makes the problem a concrete software-porting challenge rather than a hardware-capacity impossibility.
