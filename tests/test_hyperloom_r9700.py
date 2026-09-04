import pytest

from backend.app.integrations.hyperloom_r9700 import (
    build_experimental_plan,
    capability_matrix,
    is_r9700,
    parse_session_breakdown,
)


def test_detects_r9700_by_name_or_gfx():
    assert is_r9700("AMD Radeon AI PRO R9700", "gfx1201")
    assert is_r9700("Unknown AMD GPU", "gfx1201")
    assert not is_r9700("AMD Instinct MI325X", "gfx942")


def test_plan_is_truthful_and_blocks_instinct_specific_paths():
    plan = build_experimental_plan()
    assert plan.official_support is False
    assert plan.local_runner == "experimental-r9700"
    assert plan.reference_runner == "mi325x"
    matrix = capability_matrix(plan.capabilities)
    assert matrix["vllm-baseline"] == "works"
    assert matrix["hyperloom-orchestration-loop"] == "adapted"
    assert matrix["magpie-mi30x-runner-scripts"] == "blocked"
    assert matrix["official-hyperloom-r9700-runner"] == "upstream_required"
    assert any("gfx942/gfx950" in item for item in plan.blocked_paths)


def test_plan_rejects_non_r9700_target():
    with pytest.raises(ValueError):
        build_experimental_plan("AMD Instinct MI325X", "gfx942")


def test_session_breakdown_v5_preserves_unknown_fields():
    payload = {
        "schema_version": "hyperloom.session_breakdown.v5.0",
        "exporter_version": "1.0.0a2",
        "optimizations": [{"name": "batching", "gain_pct": 12.5}],
        "future_field": {"keep": True},
    }
    parsed = parse_session_breakdown(payload)
    assert parsed["schema_major"] == 5
    assert parsed["supported_reader"] is True
    assert parsed["raw"]["future_field"] == {"keep": True}


def test_session_breakdown_rejects_wrong_contract():
    with pytest.raises(ValueError):
        parse_session_breakdown({"schema_version": "other.v1"})
