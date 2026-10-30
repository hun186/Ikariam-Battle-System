"""Synthetic-only preparation tests; actual production simulator is executed."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from tools.research import p0_report_case_engine_slot_map_draft as draft


def _scenario(quantity=120, *, hall=None):
    value = {
        "battlefield": "land-mini", "policy": "experimental", "max_rounds": 2,
        "attacker": {"army_kind": "player", "forge_level": 0,
                     "units": [{"unit_id": "hoplite", "quantity": quantity}]},
        "defender": {"army_kind": "player", "forge_level": 0,
                     "units": [{"unit_id": "hoplite", "quantity": quantity}]},
    }
    if hall is not None:
        value["town_hall_level"] = hall
    return json.dumps(value, separators=(",", ":")).encode()


def _setup(monkeypatch, scenario):
    trace = draft.engine.engine_trace(scenario)  # real production engine
    final = next(s for s in trace["engine_slots"]
                 if s["engine_round"] == 2 and s["side"] == "attacker"
                 and s["unit_id"] == "hoplite")
    case = {
        "id": "synthetic-private-case", "battlefield": "land-mini",
        "rounds": [{"id": "r2", "number": 2, "phase": "round_end"}],
    }
    review = {
        "review_items": [{
            "earlier_capture_id": "r1", "target_capture_id": "r2",
            "target_round": 2, "round_number_gap": 1,
            "same_capture_phase": True,
            "side": final["side"], "line": final["line"],
            "physical_position": final["physical_position"],
            "reviewer_reported_status": "REVIEWER_REPORTS_IMAGES_READABLE",
        }],
    }
    monkeypatch.setattr(draft.binder, "_inspect_case", lambda value: {"id": case["id"]})
    monkeypatch.setattr(draft.manual, "assess_review", lambda *args: review)
    data = json.dumps(case).encode()
    return trace, final, case, review, data


def _run(scenario, case_bytes):
    return draft.prepare_draft(scenario, case_bytes, {}, Path("unused-synthetic-images"), b"{}")


def test_real_engine_candidates_never_autofill_verified_or_executable_slot_map(monkeypatch):
    scenario = _scenario()
    trace, slot, case, review, data = _setup(monkeypatch, scenario)
    result = _run(scenario, data)
    assert result["scenario_sha256"] == sha256(scenario).hexdigest()
    assert result["engine_output_sha256"] == trace["engine_output_sha256"]
    assert result["automatic_slot_bindings_created"] == 0
    assert result["can_be_used_as_verified_slot_map"] is False
    assert result["user_wave_and_physical_slot_assertion_required"] is True
    assert result["original_game_screenshots_authenticated"] is False
    assert result["independent_holdouts"] == 0
    assert "bindings" not in result
    assert result["schema"] != draft.engine.MAP_SCHEMA
    row = result["rows"][0]
    assert row["selected_engine_wave_id"] is None
    assert row["preparation_status"] == "CANDIDATE_ADDRESS_REQUIRES_HUMAN_WAVE_ASSERTION"
    assert any(c["engine_wave_id"] == slot["wave_id"] and
               c["engine_slot_id"] == slot["slot_id"]
               for c in row["engine_candidates_unverified"])


def test_actual_garrison_override_is_rejected_before_any_map(monkeypatch):
    scenario = _scenario(600, hall=1)
    trace, _, case, review, data = _setup(monkeypatch, scenario)
    assert trace["scenario_battlefield"] == "land-mini"
    assert trace["engine_effective_battlefield"] == "land-max"
    with pytest.raises(ValueError, match="battlefield"):
        _run(scenario, data)


def test_unreadable_phase_or_unknown_capture_no_positive_preparation(monkeypatch):
    scenario = _scenario()
    _, _, case, review, data = _setup(monkeypatch, scenario)
    review["review_items"][0]["reviewer_reported_status"] = "NOT_REVIEWED"
    assert _run(scenario, data)["rows"][0]["preparation_status"] == "NO_USER_REPORTED_READABLE_PAIR"
    case["rounds"][0]["phase"] = "round_start"
    assert _run(scenario, json.dumps(case).encode())["rows"][0]["preparation_status"] == "CAPTURE_PHASE_NOT_ROUND_END"
    review["review_items"][0]["target_capture_id"] = "forged-other"
    with pytest.raises(ValueError, match="canonical capture"):
        _run(scenario, data)


def test_missing_physical_address_never_promotes_to_model_wave(monkeypatch):
    scenario = _scenario()
    _, _, case, review, data = _setup(monkeypatch, scenario)
    review["review_items"][0].update(side=None, line=None, physical_position=None)
    row = _run(scenario, data)["rows"][0]
    assert row["preparation_status"] == "NO_TYPED_PHYSICAL_ADDRESS"
    assert row["engine_candidates_unverified"] == []
    assert row["selected_engine_wave_id"] is None


def test_stale_review_validation_is_not_silently_ignored(monkeypatch):
    scenario = _scenario()
    _, _, _, _, data = _setup(monkeypatch, scenario)
    def reject(*args):
        raise ValueError("stale screenshot bytes")
    monkeypatch.setattr(draft.manual, "assess_review", reject)
    with pytest.raises(ValueError, match="stale"):
        _run(scenario, data)
