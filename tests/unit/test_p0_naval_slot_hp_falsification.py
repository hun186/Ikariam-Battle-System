"""Regression and counterexample tests for the five historical naval air cases."""
from copy import deepcopy
import json
import pytest
from tools.research import p0_naval_slot_hp_falsification as audit


def source_cases():
    fixture = json.loads(audit.FIXTURE.read_text(encoding="utf-8"))
    return audit.historical_cases(fixture)


def test_source_provenance_is_historical_not_holdout():
    cases = source_cases()
    assert len(cases) == 5
    assert len({c["case"] for c, _ in cases}) == 5
    assert [p["round"] for _, p in cases] == [None, None, None, 1, 1]
    assert cases[-1][0]["case"] == "barbarian_fast_vs_player_carrier_def3_no_forge"
    assert cases[-1][1]["mapping_confirmed"] is False


def test_engine_controls_and_event_ledgers_are_real_synthetic_runs():
    report = audit.build_report()
    assert report["classification"] == "RESEARCH_ONLY_NO_ENGINE_CHANGE"
    assert report["summary"]["historically_analyzed_cases"] == 5
    assert report["summary"]["independent_holdout_cases"] == 0
    assert report["summary"]["controlled_aggregate_matches"] == 5
    assert report["summary"]["controlled_aggregate_mismatches"] == 0
    assert report["summary"]["cases_with_source_hp_bars"] == 2
    for row in report["cases"]:
        assert row["evaluation_split"] == audit.IN_SAMPLE
        assert row["independent_holdout"] is False
        assert row["model"]["invented_first_line_fillers"] is True
        assert row["model"]["full_round1_event_trace"]
        assert row["model"]["target_damage_events"]
        assert row["model"]["assumption_ledger"]
        assert len(row["model"]["per_slot"]) == 2
        assert all(s["ammo"] == "unknown" for s in row["model"]["per_slot"])
        assert row["diagnostics"]["official_game_mechanism_verified"] is False
        assert row["diagnostics"]["game_slot_hp_parity_verified"] is False
        assert row["observed"]["physical_slot_mapping"] == "unknown"


def test_reverse_att14_death_parity_masks_remaining_hp_bar_gap():
    rows = {x["case_id"]: x for x in audit.build_report()["cases"]}
    reverse = rows["player_fast_att14_vs_barbarian_carrier"]
    assert reverse["observed"]["total_deaths"] == 2
    assert reverse["observed"]["per_slot_deaths"] == [1, 1]
    assert reverse["observed"]["hp_bars_unmapped_percent"] == [53, 65]
    assert [x["casualties"] for x in reverse["model"]["per_slot"]] == [1, 1]
    assert [x["modeled_hp_bar_percent"] for x in reverse["model"]["per_slot"]] == [57, 69]
    assert reverse["diagnostics"]["slot_deaths_residual"] == [0, 0]
    assert reverse["diagnostics"]["hp_bar_residual_percent_points_sorted"] == [4, 4]
    alternative = reverse["diagnostics"]["full_retention_arithmetic_counterfactual"]
    assert alternative["status"] == audit.COUNTERFACTUAL
    assert alternative["not_engine_output"] is True
    assert alternative["bars_sorted"] == [53, 65]
    assert alternative["residual_percent_points_sorted"] == [0, 0]


def test_def14_original_bars_are_unmapped_and_not_verified_game_slot_parity():
    row = {x["case_id"]: x for x in audit.build_report()["cases"]}[
        "barbarian_fast_vs_player_carrier_def14"
    ]
    assert row["observed"]["hp_bars_unmapped_percent"] == [65, 70]
    assert row["observed"]["per_slot_deaths"] is None
    assert row["diagnostics"]["hp_bar_semantics"] == audit.UNVERIFIED
    assert row["diagnostics"]["slot_deaths_residual"] is None


@pytest.mark.parametrize("claimed", [
    {"evaluation_split": "holdout"},
    {"evaluation_split": "independent"},
    {"independent_holdout": True},
])
def test_in_sample_fixture_cannot_be_reclassified_as_independent(claimed):
    case, provenance = source_cases()[0]
    with pytest.raises(ValueError, match="cannot claim independent holdout"):
        audit.compare_case({**case, **claimed}, provenance)


def test_invalid_hp_bar_and_fixture_provenance_fail_closed():
    fixture = json.loads(audit.FIXTURE.read_text(encoding="utf-8"))
    fixture["additional_observations"][0]["confirmed_target_slot_counts"] = [2, 4]
    with pytest.raises(ValueError, match="DEF3 source/formation"):
        audit.historical_cases(fixture)
    fixture = json.loads(audit.FIXTURE.read_text(encoding="utf-8"))
    fixture["observed"][3]["reported_survivor_slot_bars_percent"] = [53, 110]
    case, provenance = audit.historical_cases(fixture)[3]
    with pytest.raises(ValueError, match="original HP bars"):
        audit.compare_case(case, provenance)
    fixture = json.loads(audit.FIXTURE.read_text(encoding="utf-8"))
    fixture["source"]["original_battle_reports_attached"] = True
    with pytest.raises(ValueError, match="re-audit"):
        audit.historical_cases(fixture)


def test_model_missing_one_slot_damage_event_fails_closed(monkeypatch):
    original = audit.run_current_full_engine_control
    def missing(case):
        result = deepcopy(original(case))
        targeted = [
            e for e in result["synthetic_round1_model_events"]
            if e.get("type") == "damage"
            and (e.get("details") or {}).get("source_unit_id") == case["attacker"]
            and (e.get("details") or {}).get("target_unit_id") == case["target"]
        ]
        pos = targeted[0]["details"]["target_damage_position"]
        result["synthetic_round1_model_events"] = [
            e for e in result["synthetic_round1_model_events"]
            if not (e.get("type") == "damage"
                and (e.get("details") or {}).get("source_unit_id") == case["attacker"]
                and (e.get("details") or {}).get("target_unit_id") == case["target"]
                and e["details"].get("target_damage_position") == pos)
        ]
        return result
    monkeypatch.setattr(audit, "run_current_full_engine_control", missing)
    with pytest.raises(ValueError, match="target slots incomplete"):
        audit.compare_case(*source_cases()[0])


def test_deterministic_report_and_csv_no_holdout_leakage():
    a, b = audit.build_report(), audit.build_report()
    assert a == b
    rows = audit.csv_rows(a)
    assert len(rows) == 5
    assert [row["original_total"] for row in rows] == [1, 0, 0, 2, 2]
    assert all(row["independent_holdout"] is False for row in rows)
    assert rows[3]["unmapped_sorted_hp_residuals"] == "[4,4]"
    assert audit.COUNTERFACTUAL in rows[3]["counterfactual"]
