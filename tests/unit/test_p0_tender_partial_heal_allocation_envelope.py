"""Conditional Tender allocation envelope: real R1 witness, hypothetical R2 HP only."""
from copy import deepcopy
import json

import pytest

from tools.research import p0_tender_partial_heal_allocation_envelope as study


def test_integer_full_budget_policy_priorities_and_largest_remainder():
    rows = [
        {"unit_id": "ram_ship", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 5000},
        {"unit_id": "steam_ram", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 2500},
        {"unit_id": "tender", "wave_id": "wave-1",
         "eligible": False, "wounds_r1_end": 500},
    ]
    result = study.allocations(rows, 4000)
    ram, steam, tender = (u, "wave-1") for u in ("ram_ship", "steam_ram", "tender")
    assert result[study.POLICIES[0]] == {ram: 0, steam: 0, tender: 0}
    assert result[study.POLICIES[1]] == {ram: 4000, steam: 0, tender: 0}
    assert result[study.POLICIES[2]] == {ram: 1500, steam: 2500, tender: 0}
    assert result[study.POLICIES[3]] == {ram: 2667, steam: 1333, tender: 0}
    assert all(sum(values.values()) == 4000 for name, values in result.items()
               if name != study.POLICIES[0])


@pytest.mark.parametrize("bad_capacity", [0, -1, True, 7500, 7501, 1.0])
def test_rejects_zero_forged_or_sufficient_capacity(bad_capacity):
    rows = [
        {"unit_id": "ram_ship", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 5000},
        {"unit_id": "steam_ram", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 2500},
    ]
    with pytest.raises(ValueError):
        study.allocations(rows, bad_capacity)


def test_rejects_duplicate_waves_and_invalid_wound_values():
    rows = [
        {"unit_id": "ram_ship", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 5000},
        {"unit_id": "ram_ship", "wave_id": "wave-1",
         "eligible": True, "wounds_r1_end": 2500},
    ]
    with pytest.raises(ValueError, match="duplicate"):
        study.allocations(rows, 4000)
    rows[1]["wave_id"] = "wave-2"
    rows[1]["wounds_r1_end"] = -1
    with pytest.raises(ValueError, match="wound"):
        study.allocations(rows, 4000)


def test_live_source_still_reports_unknown_not_game_zero_healing():
    c = study.source()
    assert c["case_id"] == "naval_tender_support_1_live_R1_R2"
    assert c["game_observations"] == c["independent_holdouts"] == 0
    assert c["round2_real_patient_firing"] is True
    rows, capacity = study.wounded_eligible_waves(c)
    assert capacity == 4000
    assert sum(x["wounds_r1_end"] for x in rows if x["eligible"]) > capacity
    assert all(x["wounds_r1_end"] == x["model_wounds_r2_prefire"]
               for x in rows)
    assert c["transitions"]["defender"]["boundary"]["outcome"] == (
        "insufficient_capacity_game_allocation_unknown_model_applies_no_partial"
    )


def test_actual_r2_baseline_rr_replayed_and_other_policies_hypothetical():
    report = study.build_report()
    assert report["classification"] == "COUNTERFACTUAL_NOT_NEW_GAME_EVIDENCE"
    assert report["summary"] == {
        "model_comparison_scenarios": 4,
        "conditional_full_budget_policies": 3,
        "new_game_observations": 0,
        "independent_holdouts": 0,
        "official_partial_healing_verified": False,
    }
    scenarios = report["scenarios"]
    assert [x["policy"] for x in scenarios] == list(study.POLICIES)
    assert scenarios[0]["hypothetical_hp_budget_used"] == 0
    assert scenarios[0]["provenance"] == study.LIVE_PROVENANCE
    assert all(x["actual_engine_partial_healing_executed"] is False
               and x["game_mechanic_verified"] is False for x in scenarios)
    assert all(x["provenance"] == study.PROVENANCE and
               x["hypothetical_hp_budget_used"] == report["source"]["capacity_hp"]
               for x in scenarios[1:])

    for variant in scenarios:
        keys = [(w["unit_id"], w["wave_id"]) for w in variant["waves"]]
        assert len(keys) == len(set(keys))
        for wave in variant["waves"]:
            after = wave["hypothetical_remaining_wounds"]
            assert after + wave["hypothetical_healed_hp"] == wave["original_wounds_r1"]
            assert after == sum(s["remaining_wounds"] for s in wave["slots"]) + wave["reserve_wounds"]
            assert wave["alive"] == wave["reserve"] + sum(s["units"] for s in wave["slots"])
            assert 0 <= wave["reserve_wounds"]
            assert wave["rr_method"] == (
                "current_experimental_reserve_redistribution_on_unchanged_R2_deployment"
            )
            for slot in wave["slots"]:
                assert 0 <= slot["percent_current_model_format"] <= 100
                if variant["policy"] == study.POLICIES[0]:
                    assert slot["remaining_wounds"] == slot["original_model_wounds"]
                    assert slot["percent_current_model_format"] == slot["original_model_hp_bar"]


def test_csv_keeps_wave_and_policy_provenance_distinct():
    report = study.build_report()
    rows = study.csv_rows(report)
    assert len(rows) > 4
    assert len({(x["policy"], x["unit_id"], x["wave_id"]) for x in rows}) == len(rows)
    assert {x["policy"] for x in rows} == set(study.POLICIES)
    assert all(x["case_id"] == report["source"]["case_id"]
               and x["supporter_count"] == 1
               and x["capacity_hp"] == 4000
               and not x["game_mechanic_verified"]
               and not x["actual_engine_partial_healing_executed"]
               and x["new_game_observations"] == x["independent_holdouts"] == 0
               for x in rows)
    assert all(isinstance(json.loads(x["slot_hp_json"]), list) for x in rows)


def test_altered_real_r2_wound_snapshot_is_not_accepted(monkeypatch):
    baseline = study.source()

    def tampered():
        c = deepcopy(baseline)
        slot = next(s for s in c["transitions"]["defender"]["before_r2"]["slots"]
                    if s["unit_id"] == "ram_ship")
        slot["damage"] += 1
        return c

    monkeypatch.setattr(study, "source", tampered)
    with pytest.raises(AssertionError, match="not conserved"):
        study.build_report()


def test_forged_supported_healing_event_not_source_of_truth(monkeypatch):
    baseline = study.source()

    def tampered():
        c = deepcopy(baseline)
        c["transitions"]["defender"]["boundary"]["outcome"] = (
            "full_clear_current_supported_subset"
        )
        return c

    monkeypatch.setattr(study, "source", tampered)
    with pytest.raises(AssertionError, match="not an unresolved partial"):
        study.build_report()


def test_duplicate_export_policy_wave_is_rejected():
    report = study.build_report()
    report["scenarios"][0]["waves"].append(
        deepcopy(report["scenarios"][0]["waves"][0])
    )
    with pytest.raises(AssertionError, match="ambiguous"):
        study.csv_rows(report)


def test_report_is_repeatable_without_randomized_combat_assumptions():
    assert study.build_report() == study.build_report()
