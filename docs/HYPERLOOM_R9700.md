# Hyperloom on Radeon AI PRO R9700 (gfx1201) — Experimental Challenge 1 Track

## Scope

This repository does **not** claim official Hyperloom support for Radeon AI PRO R9700.
Current Hyperloom validation targets AMD Instinct runner families. This Challenge 1 track
explores which parts of the Hyperloom optimization workflow can be adapted safely to
R9700/gfx1201 and which parts require upstream support.

## Local target

- GPU: AMD Radeon AI PRO R9700
- Architecture: gfx1201 / RDNA4
- Local runtime: ROCm 10 canary
- Serving: vLLM local-first
- Reference supported Hyperloom runner: AMD Instinct MI325X
- Cloud credits: none assumed; no cloud spend is required for the local experiment

## What we are adapting

Architecture-neutral pieces:

- baseline workload definition
- request concurrency and batching experiments
- vLLM/SGLang server-level tuning
- latency, TTFT and throughput measurement methodology
- optimization action ordering
- Hyperloom session evidence consumption

## What stays blocked

- pretending `--gpu-type r9700` is an official Hyperloom runner
- reusing MI30x Magpie runner scripts as if they were RDNA4 scripts
- reusing gfx942/gfx950 compiled kernel artifacts on gfx1201
- claiming MI325X performance gains apply to R9700 without local re-benchmarking

## Capability statuses

- `works`: already architecture-neutral and usable locally
- `adapted`: can be wrapped safely for the R9700 experiment
- `blocked`: must not run on gfx1201 in its current Instinct-specific form
- `upstream_required`: needs native Hyperloom support or an upstream-compatible runner

## Challenge 1 result we want

A reproducible proof that answers:

1. Which Hyperloom workflow components run unchanged on R9700?
2. Which components can be adapted without falsifying official support?
3. Which components are hard-blocked by Instinct/CDNA assumptions?
4. What local serving improvements can be validated on R9700 itself?
5. What upstream changes would be required for first-class `gfx1201` support?

This is intentionally more useful than a compatibility hack that simply renames the GPU.
