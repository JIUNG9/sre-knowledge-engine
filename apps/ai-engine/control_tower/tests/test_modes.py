"""Mode specs + configuration sanity tests."""

from __future__ import annotations

import pytest

from control_tower.config import ControlTowerConfig
from control_tower.modes import (
    DEEP,
    ECO,
    STANDARD,
    all_modes,
    get_mode_spec,
)


def test_eco_is_cheap_and_small():
    assert ECO.name == "eco"
    assert ECO.max_llm_calls == 1
    assert ECO.include_logs is False
    assert ECO.include_traces is False
    assert ECO.run_pattern_analyzer is False
    assert "haiku" in ECO.preferred_model.lower()


def test_standard_pulls_telemetry():
    assert STANDARD.name == "standard"
    assert STANDARD.max_llm_calls == 2
    assert STANDARD.include_logs is True
    assert STANDARD.include_metrics is True
    assert STANDARD.include_traces is False
    assert "sonnet" in STANDARD.preferred_model.lower()


def test_deep_runs_pattern_analyzer():
    assert DEEP.name == "deep"
    assert DEEP.max_llm_calls == 3
    assert DEEP.run_pattern_analyzer is True
    assert DEEP.include_traces is True
    assert "opus" in DEEP.preferred_model.lower()


def test_all_modes_returns_all_three():
    modes = all_modes()
    assert [m.name for m in modes] == ["eco", "standard", "deep"]


def test_get_mode_spec_valid():
    assert get_mode_spec("eco") is ECO
    assert get_mode_spec("STANDARD") is STANDARD
    assert get_mode_spec("Deep") is DEEP


def test_get_mode_spec_invalid():
    with pytest.raises(ValueError):
        get_mode_spec("ultra")


def test_mode_spec_to_dict_is_serializable():
    spec_dict = STANDARD.to_dict()
    assert spec_dict["name"] == "standard"
    assert isinstance(spec_dict["tools"], list)
    assert spec_dict["include_logs"] is True


def test_config_context_budgets_default():
    cfg = ControlTowerConfig()
    assert cfg.context_budget_for("eco") == 4_000
    assert cfg.context_budget_for("standard") == 16_000
    assert cfg.context_budget_for("deep") == 64_000


def test_config_call_ceilings_default():
    cfg = ControlTowerConfig()
    assert cfg.call_ceiling_for("eco") == 1
    assert cfg.call_ceiling_for("standard") == 2
    assert cfg.call_ceiling_for("deep") == 3


def test_config_custom_budget():
    cfg = ControlTowerConfig(eco_context_tokens=2048, deep_context_tokens=8192)
    assert cfg.context_budget_for("eco") == 2048
    assert cfg.context_budget_for("deep") == 8192


def test_config_rejects_too_small_eco_budget():
    with pytest.raises(Exception):
        ControlTowerConfig(eco_context_tokens=0)
