"""All wound inputs and capacity numbers are invented mathematical fixtures."""
from copy import deepcopy
import json

import pytest

from tools.research import p0_naval_carrier_late_tender_priority as research


def invented():
    return {
        "schema": research.SCHEMA, "record_kind": research.KIND,
        "carrier_unit_ids": ["balloon_carrier"],
        "healing_capacity_hp_levels": [140, 100, 40, 0, 80, 160],
        "wounded_waves": [
            {"unit_id": "ram_ship", "wave_label": "W1",
             "eligible_for_tender": True, "wounds_hp": 80},
            {"unit_id": "balloon_carrier", "wave_label": "W1",
             "eligible_for_tender": True, "wounds_hp": 60},
        ],
    }


def _by_capacity(result):
    return {x["hypothetical_capacity_hp"]: x
            for x in result["sensitivity_by_capacity"]}


def test_carrier_late_threshold_is_distinguishable_only_under_shortage():
    rec = invented()
    copy = deepcopy(rec)
    got = research.compare(rec)
    assert got["status"] == research.READY
    assert got["noncarrier_saturation_threshold_hp"] == 80
    assert got["discriminating_capacity_levels"] == [40, 80, 100]
    snapshots = _by_capacity(got)
    at_40 = snapshots[40]["hypothetical_allocation_by_policy"]
    assert at_40["noncarrier_before_carrier"]["hypothetical_carrier_healed_hp"] == 0
    assert at_40["proportional_all"]["hypothetical_carrier_healed_hp"] > 0
    assert at_40["carrier_before_noncarrier"]["hypothetical_carrier_healed_hp"] == 40
    at_100 = snapshots[100]["hypothetical_allocation_by_policy"]
    assert at_100["noncarrier_before_carrier"]["hypothetical_carrier_healed_hp"] == 20
    assert at_100["carrier_before_noncarrier"]["hypothetical_carrier_healed_hp"] == 60
    for level in [0, 140, 160]:
        assert not snapshots[level]["hypotheses_have_different_carrier_healing"]
    assert got["actual_gameforge_healing_order_verified"] is False
    assert got["owner_qualitative_observation_authenticated_by_screenshots"] is False
    assert got["independently_verified_game_observations"] == 0
    assert got["independent_holdouts"] == 0
    assert rec == copy


def test_budget_conserved_and_never_resurrects_or_heals_ineligible():
    rec = invented()
    rec["wounded_waves"].append({
        "unit_id": "naval_tender", "wave_label": "support",
        "eligible_for_tender": False, "wounds_hp": 300})
    output = research.compare(rec)
    for level in output["sensitivity_by_capacity"]:
        cap = level["hypothetical_capacity_hp"]
        for policy, scenario in level["hypothetical_allocation_by_policy"].items():
            assert policy in research.POLICIES
            assert (scenario["hypothetical_total_healed_hp"]
                    + scenario["unused_hypothetical_capacity_hp"] == cap)
            assert scenario["hypothetical_total_healed_hp"] == min(cap, 140)
            assert all(0 <= w["hypothetical_healed_hp"] for w in scenario["per_wave"])
            assert next(x for x in scenario["per_wave"]
                        if x["unit_id"] == "naval_tender")["hypothetical_healed_hp"] == 0


def test_wave_priority_tie_deterministic_after_row_reordering():
    r = invented()
    r["wounded_waves"][0]["wounds_hp"] = 81
    r["wounded_waves"].append({
        "unit_id": "ram_ship", "wave_label": "W2",
        "eligible_for_tender": True, "wounds_hp": 41})
    one = research.compare(r)
    r["wounded_waves"].reverse()
    two = research.compare(r)
    assert one["sensitivity_by_capacity"] == two["sensitivity_by_capacity"]


def test_missing_two_injured_groups_not_presented_as_discrimination():
    r = invented()
    r["wounded_waves"][1]["wounds_hp"] = 0
    assert research.compare(r)["status"] == research.INCONCLUSIVE
    r["wounded_waves"][1]["wounds_hp"] = 60
    r["wounded_waves"][0]["wounds_hp"] = 0
    assert research.compare(r)["status"] == research.INCONCLUSIVE


@pytest.mark.parametrize("field,bad", [
    ("healing_capacity_hp_levels", [True, 40]),
    ("healing_capacity_hp_levels", [-1]),
    ("healing_capacity_hp_levels", [50, 50]),
    ("healing_capacity_hp_levels", ["40"]),
    ("carrier_unit_ids", []),
    ("carrier_unit_ids", ["balloon_carrier", "balloon_carrier"]),
    ("record_kind", "claimed_official_evidence"),
    ("schema", "forged_source"),
])
def test_invalid_control_inputs_not_promoted_to_real_evidence(field, bad):
    r = invented()
    r[field] = bad
    result = research.compare(r)
    assert result["status"] == research.INVALID
    assert not result["sensitivity_by_capacity"]
    assert result["validation_errors"]


@pytest.mark.parametrize("wound", [True, -1, 1.25, "60", 1000000001])
def test_invalid_wound_amounts_fail_closed(wound):
    r = invented()
    r["wounded_waves"][1]["wounds_hp"] = wound
    assert research.compare(r)["status"] == research.INVALID


def test_duplicate_wave_not_double_counted():
    r = invented()
    r["wounded_waves"].append(deepcopy(r["wounded_waves"][0]))
    assert research.compare(r)["status"] == research.INVALID


def test_capacity_above_wounds_does_not_create_false_heal():
    r = invented()
    r["healing_capacity_hp_levels"] = [0, 200]
    got = research.compare(r)
    assert got["status"] == research.INCONCLUSIVE
    for policy in research.POLICIES:
        item = got["sensitivity_by_capacity"][-1]["hypothetical_allocation_by_policy"][policy]
        assert item["hypothetical_total_healed_hp"] == 140
        assert item["unused_hypothetical_capacity_hp"] == 60


def test_cli_outputs_synthetic_only_report(tmp_path, monkeypatch):
    a, b = tmp_path / "input.json", tmp_path / "output.json"
    a.write_text(json.dumps(invented()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py", "--input", str(a), "--output-json", str(b)])
    research.main()
    out = json.loads(b.read_text(encoding="utf-8"))
    assert out["status"] == research.READY
    assert out["actual_carrier_healing_amount_verified"] is False


def test_cli_invalid_exits_two_and_writes_diagnostics(tmp_path, monkeypatch):
    rec = invented()
    rec["carrier_unit_ids"] = []
    a, b = tmp_path / "bad.json", tmp_path / "bad-report.json"
    a.write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py", "--input", str(a), "--output-json", str(b)])
    with pytest.raises(SystemExit) as exc:
        research.main()
    assert exc.value.code == 2
    assert json.loads(b.read_text(encoding="utf-8"))["status"] == research.INVALID
