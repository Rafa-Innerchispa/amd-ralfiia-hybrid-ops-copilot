# Candidate upstream port — Hyperloom R9700 / gfx1201

This is a **candidate port plan**, not a claim that upstream Hyperloom already supports R9700.
It is based on the current public Hyperloom source structure.

## Minimal identity changes

Hyperloom's CLI choices derive from `AMD_GPU_DISPATCH_IDENTITIES`, so the first candidate change is:

```diff
--- a/src/hyperloom/common/gpu_identity.py
+++ b/src/hyperloom/common/gpu_identity.py
@@
 AMD_GPU_DISPATCH_IDENTITIES: dict[str, tuple[str, int]] = {
     "mi300x": ("gfx942", 304),
     "mi308x": ("gfx942", 304),
     "mi325x": ("gfx942", 304),
     "mi355x": ("gfx950", 256),
+    "r9700": ("gfx1201", 64),
 }
```

AMD publishes R9700 as RDNA4 / `gfx1201` / 64 Compute Units.

## Runner fallback mapping

For torch `gcnArchName` fallback detection, add:

```diff
--- a/src/hyperloom/inference_optimizer/gpu_types.py
+++ b/src/hyperloom/inference_optimizer/gpu_types.py
@@
 _GFX_TO_RUNNER: dict[str, str] = {
     "gfx942": "mi300x",
     "gfx950": "mi355x",
+    "gfx1201": "r9700",
 }
```

Because `_gpu_runner_type()` already returns the normalized GPU type when it is not an MI308X/MI325X alias, an `r9700` identity naturally resolves to `runner_type=r9700`.

## Why this alone is not enough

Hyperloom materializes benchmark scripts using the framework + runner type, for example:

```text
vllm_mi300x.sh
sglang_mi355x.sh
```

An R9700 port therefore needs a dedicated benchmark path such as:

```text
vllm_r9700.sh
sglang_r9700.sh
```

or an explicit custom benchmark-script override that produces the same result contract.

## Proposed R9700 first runner

Start with **vLLM only**, because vLLM is already verified on the local R9700/ROCm 10 node.

The initial runner should:

1. launch/attach to a gfx1201-compatible vLLM server;
2. preserve Hyperloom workload knobs (model, ISL, OSL, concurrency, TP, precision where applicable);
3. write results to the provided `RESULT_DIR`;
4. expose output-token throughput and request completion evidence in the format Hyperloom/Magpie expects;
5. avoid MI300X-specific environment variables and kernel assumptions;
6. fail explicitly when an unsupported profiling/kernel phase is requested.

## Feature gates for the first port

### Enable initially

- baseline serving benchmark
- vLLM server-parameter experiments
- concurrency/batching experiments
- evidence/session orchestration
- generic correctness/performance comparison

### Disable until separately proven on gfx1201

- gfx942/gfx950 compiled kernel reuse
- MI300X-specific AITER recipes
- Instinct-only profiler assumptions
- architecture-specific kernel search results copied from MI300X/MI355X
- quantization schemes documented as GPU-specific to other architectures

## Upstream tests to add

1. CLI accepts `--gpu-type r9700` once identity is registered.
2. `gfx_arch_for_gpu_type("r9700") == "gfx1201"`.
3. `amd_gpu_dispatch_identity("r9700") == ("gfx1201", 64)`.
4. gfx1201 torch fallback resolves to `r9700`.
5. runner type remains `r9700`, not `mi300x`.
6. benchmark materialization selects the R9700 script or explicit override.
7. CDNA-only feature gates remain off for `gfx1201`.

## Definition of a useful Challenge 1 result

A valuable result does **not** require every Hyperloom optimizer backend to work on day one. The port is useful when Hyperloom can:

1. identify the R9700 truthfully;
2. execute a reproducible baseline;
3. explore at least architecture-neutral serving candidates;
4. rebenchmark and produce auditable evidence;
5. stop cleanly at unsupported architecture-specific functionality instead of generating a false PASS.

If those stages work, the remaining gfx1201 enablement becomes a clear upstream roadmap rather than an all-or-nothing experiment.
