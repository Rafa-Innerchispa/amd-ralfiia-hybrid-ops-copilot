import importlib.util
import sys
from argparse import Namespace
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hyperloom_r9700_benchmark.py"
spec = importlib.util.spec_from_file_location("hyperloom_r9700_benchmark", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_percentile_edges():
    assert module._percentile([], 0.5) == 0.0
    assert module._percentile([10.0], 0.95) == 10.0
    assert module._percentile([10.0, 20.0, 30.0], 0.5) == 20.0


def test_run_builds_reproducible_summary(monkeypatch):
    responses = [
        {
            "choices": [{"finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        for _ in module.DEFAULT_PROMPTS
    ]

    def fake_post_json(url, payload, timeout):
        assert url.endswith("/v1/chat/completions")
        assert payload["temperature"] == 0
        return responses.pop(0)

    times = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr(module, "_post_json", fake_post_json)
    monkeypatch.setattr(module.time, "perf_counter", lambda: next(times))

    args = Namespace(
        base_url="http://127.0.0.1:8000",
        model="demo-model",
        mode="baseline",
        repeat=1,
        max_tokens=96,
        timeout=120.0,
    )
    result = module.run(args)
    assert result["schema_version"] == "inneros.hyperloom_r9700_benchmark.v1"
    assert result["target"]["official_hyperloom_support"] is False
    assert result["summary"]["requests"] == 3
    assert result["summary"]["output_tokens"] == 60
    assert result["summary"]["mean_latency_ms"] == 1000.0
    assert result["summary"]["mean_completion_tokens_per_second"] == 20.0
