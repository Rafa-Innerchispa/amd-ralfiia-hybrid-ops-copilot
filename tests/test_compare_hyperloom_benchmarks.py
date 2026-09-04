import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_hyperloom_benchmarks.py"
spec = importlib.util.spec_from_file_location("compare_hyperloom_benchmarks", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


def _bench(tput: float, latency: float, model: str = "Qwen"):
    return {
        "schema_version": "inneros.hyperloom_r9700_benchmark.v1",
        "target": {
            "model": model,
            "gpu_claim": "AMD Radeon AI PRO R9700",
            "gfx_claim": "gfx1201",
            "official_hyperloom_support": False,
        },
        "summary": {
            "sequential_effective_output_tokens_per_second": tput,
            "mean_latency_ms": latency,
        },
    }


def test_compare_reports_real_deltas():
    result = module.compare(_bench(100, 1000), _bench(115, 900))
    assert round(result["delta"]["throughput_gain_percent"], 2) == 15.0
    assert round(result["delta"]["latency_improvement_percent"], 2) == 10.0
    assert result["claim_gate"]["ten_percent_target_met"] is True


def test_compare_rejects_model_mismatch():
    try:
        module.compare(_bench(100, 1000, "A"), _bench(110, 900, "B"))
    except ValueError as exc:
        assert "model mismatch" in str(exc)
    else:
        raise AssertionError("model mismatch should fail")


def test_zero_baseline_never_claims_improvement():
    result = module.compare(_bench(0, 0), _bench(100, 900))
    assert result["delta"]["throughput_gain_percent"] is None
    assert result["claim_gate"]["measured"] is False
    assert result["claim_gate"]["ten_percent_target_met"] is False
