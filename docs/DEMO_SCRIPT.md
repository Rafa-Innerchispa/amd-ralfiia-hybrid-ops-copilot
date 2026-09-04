# Challenge 1 Demo Script — Hyperloom on R9700

Target length: 2–3 minutes.

## Scene 1 — The gap (20s)

Show the AMD Radeon AI PRO R9700 and the live `rocm-smi` / runtime evidence.

Narration points:

- This is a Radeon AI PRO R9700 with 32 GB VRAM and RDNA4 `gfx1201`.
- ROCm 10 and vLLM already run local AI workloads on it.
- Hyperloom currently exposes official runners for Instinct families, not R9700.

## Scene 2 — Upstream limitation (25s)

Show the Hyperloom GPU identity/runner evidence and our capability matrix.

Narration points:

- Hyperloom's CLI derives accepted GPU types from its central AMD identity table.
- R9700 is not in that table today.
- We do not pretend the R9700 is an MI300X. We add a separate experimental runner and block non-portable CDNA artifacts.

## Scene 3 — Our port (35s)

Open `backend/app/integrations/hyperloom_r9700.py` and `docs/HYPERLOOM_R9700.md`.

Show:

- R9700/gfx1201 detection
- WORKS / ADAPTED / BLOCKED / UPSTREAM_REQUIRED matrix
- reference runner remains MI325X
- architecture-specific kernels explicitly blocked

## Scene 4 — Reproducible optimization evidence (35s)

Show:

```bash
python3 scripts/hyperloom_r9700_benchmark.py \
  --base-url http://127.0.0.1:8000 \
  --model QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ \
  --mode baseline --output docs/evidence/baseline.json
```

Then run the candidate with the exact same workload and compare:

```bash
python3 scripts/compare_hyperloom_benchmarks.py \
  docs/evidence/baseline.json \
  docs/evidence/candidate.json \
  --output docs/evidence/comparison.json
```

Narration points:

- Every performance claim comes from raw JSON.
- The comparator refuses model/GPU mismatches and never fabricates a percentage when no baseline exists.

## Scene 5 — Hyperloom experimental preflight (30s)

Once the live port validation is available, show either:

### Successful path

- R9700 accepted/detected
- baseline starts
- Hyperloom explore/rebenchmark loop
- session evidence

### Honest blocker path

Show the exact first incompatible subsystem and explain whether it is:

- runner script
- profiler
- kernel backend
- platform-specific recipe
- another upstream dependency

The blocker itself is valid engineering evidence if the port reaches it reproducibly.

## Scene 6 — Why it matters (20s)

Closing points:

- The R9700 is substantially more accessible than an Instinct server GPU for many local AI developers.
- Extending Hyperloom toward Radeon AI PRO would connect AMD's autonomous optimization stack with local workstation AI.
- The Challenge 1 deliverable is a real compatibility experiment with a clean upstream path, not a simulated demo.

## Final screen

Show:

- GitHub repository
- PR #2
- Issue #1
- test count
- `docs/EVIDENCE_INDEX.md`
- measured baseline/candidate delta if available

Do not show cloud-credit claims: this project assumes **no AMD promotional cloud credit**.
