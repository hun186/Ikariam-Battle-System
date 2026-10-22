"""Evidence-gap matrix regressions: aggregate fit is not Gameforge proof."""
import json

import pytest
from ikariam_battle.accuracy import NAVAL_FAST_CARRIER_FOCUS_ID
from ikariam_battle.naval_focus import NAVAL_RAM_SHARE_RULE_ID
from tools.research import p0_naval_observed_vs_model as audit
from tools.research.p0_naval_observed_vs_model import (
    BAR_UNAVAILABLE,
    ASSUMPTION_REPORTED,
    RAM_CHAT_SOURCE,
    MATCH_IN_SAMPLE,
    MISMATCH_CONTROLLED,
    MODEL_SYNTHETIC,
    NO_INDEPENDENT_HOLDOUT,
    NOT_ASSESSABLE,
    ROUND_UNKNOWN,
    SLOT_UNAVAILABLE,
    assess_aggregate,
    build_report,
    csv_rows,
)


def test_six_actual_source_aggregates_match_bounded_in_sample_controls_only():
    report = build_report()
    assert report["classification"] == "RESEARCH_ONLY_NO_PRODUCTION_ALGORITHM_CHANGE"
    assert report["summary"] == {
        "total_cases": 6,
        "aggregate_in_sample_matches": 6,
        "aggregate_controlled_mismatches": 0,
        "independently_held_out_cases": 0,
        "per_slot_game_telemetry_assessable_cases": 0,
        "game_hp_bar_parity_assessable_cases": 0,
        "fitted_candidate_reported_cases": 6,
        "fitted_candidate_not_reported_cases": 0,
    }
    assert [
        (c["observed"]["casualties_total"], c["model"]["casualties_total"])
        for c in report["cases"]
    ] == [(2, 2), (2, 2), (1, 1), (6, 6), (0, 0), (0, 0)]
    for case in report["cases"]:
        assert case["assessment"]["aggregate"] == MATCH_IN_SAMPLE
        assert case["assessment"]["per_slot_deaths"] == SLOT_UNAVAILABLE
        assert case["assessment"]["hp_bar"] == BAR_UNAVAILABLE
        assert case["assessment"]["independent_holdout"] == NO_INDEPENDENT_HOLDOUT
        assert case["assessment"]["official_mechanic_validation"] == NOT_ASSESSABLE
        assert case["assessment"]["exact_original_fleet_reconstruction"] is False
        assert case["model"]["evidence_class"] == MODEL_SYNTHETIC
        assert case["model"]["invented_first_line_fillers"] is True
        assert case["model"]["production_combat_algorithm_changed"] is False
        assert case["model"]["physical_slots_model_only"]
        assert case["model"]["applied_assumption_ids"]
        assert case["model"]["fitted_candidate_rule_id"] in (
            case["model"]["applied_assumption_ids"]
        )
        assert case["model"]["fitted_candidate_rule_status"] == ASSUMPTION_REPORTED
        assert case["model"]["assumption_evidence_source"] in {
            "engine_result.assumptions",
            "engine_round1_target_damage_event.assumption_ids",
        }
        assert len(case["next_required_evidence"]) >= 3


def test_pvp_round_one_confirmed_but_original_slot_casualties_not_observed():
    cases = build_report()["cases"]
    for case in cases[:3]:
        assert case["observed"]["reported_round"] == 1
        assert case["assessment"]["round"] == "model_reached_reported_round"
        assert case["observed"]["physical_slot_source_status"] == "unreported_for_this_game_case"
        assert case["observed"]["reported_hp_bars_percent"] is None
        assert len(case["model"]["physical_slots_model_only"]) == 2
        assert case["model"]["fitted_candidate_rule_id"] == NAVAL_FAST_CARRIER_FOCUS_ID
        assert case["model"]["assumption_evidence_source"] == "engine_result.assumptions"
    assert [c["case_id"] for c in cases[:3]] == [
        "pvp_fast_att12_carrier_def8",
        "pvp_fast_att20_carrier_def16",
        "pvp_fast_att17_carrier_def18",
    ]


def test_ram_workbook_not_confused_with_direct_chat_hp_bars_or_rounds():
    cases = build_report()["cases"][3:]
    assert [c["case_id"] for c in cases] == [
        "ram_defense_14_attack_20_forge5",
        "ram_defense_15_attack_20_forge5",
        "ram_defense_19_attack_20_forge5",
    ]
    for case in cases:
        assert case["assessment"]["round"] == ROUND_UNKNOWN
        assert case["observed"]["reported_round"] is None
        assert len(case["model"]["physical_slots_model_only"]) == 6
        assert case["model"]["fitted_candidate_rule_id"] == NAVAL_RAM_SHARE_RULE_ID
        assert case["model"]["assumption_evidence_source"] == (
            "engine_round1_target_damage_event.assumption_ids"
        )
    assert cases[0]["observed"]["evidence_class"] == "USER_WORKBOOK_F4_F19_AGGREGATE_ONLY"
    assert cases[1]["observed"]["evidence_class"] == "USER_WORKBOOK_F4_F19_AGGREGATE_ONLY"
    chat = cases[2]["observed"]
    assert chat["evidence_class"] == RAM_CHAT_SOURCE
    assert chat["reported_hp_bars_percent"] == {
        "player_remaining": 63, "barbarian_remaining": 88,
    }
    assert cases[2]["assessment"]["hp_bar"] == BAR_UNAVAILABLE


def test_different_aggregate_is_mismatch_but_not_held_out_proof():
    assert assess_aggregate(1, 2) == MISMATCH_CONTROLLED
    assert assess_aggregate(1, 1) == MATCH_IN_SAMPLE
    assert assess_aggregate(None, 1) == NOT_ASSESSABLE
    assert assess_aggregate(1, None) == NOT_ASSESSABLE


def test_report_is_deterministic_and_flat_csv_never_marks_full_calibration():
    first, second = build_report(), build_report()
    assert first == second
    rows = csv_rows(first)
    assert len(rows) == 6
    assert [int(row["observed_total"]) for row in rows] == [2, 2, 1, 6, 0, 0]
    for row in rows:
        assert row["aggregate_status"] == MATCH_IN_SAMPLE
        assert row["physical_slot_status"] == SLOT_UNAVAILABLE
        assert row["hp_bar_status"] == BAR_UNAVAILABLE
        assert row["holdout_status"] == NO_INDEPENDENT_HOLDOUT
        assert row["invented_first_line_fillers"] is True
        assert row["fitted_candidate_rule_id"] in row["engine_applied_assumption_ids"].split(";")
        assert row["fitted_candidate_rule_status"] == ASSUMPTION_REPORTED
        assert row["engine_assumption_source"]


def test_change_to_chat_def19_workbook_source_fails_closed(tmp_path, monkeypatch):
    original = json.loads(audit.RAM_FIXTURE.read_text(encoding="utf-8"))
    altered = original["observed"]["direct_conversation_case"]
    altered["source"] = "USER_WORKBOOK_F4_F19_AGGREGATE_ONLY"
    fixture = tmp_path / "altered_ram_source.json"
    fixture.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(audit, "RAM_FIXTURE", fixture)
    with pytest.raises(ValueError, match="DEF19 chat source"):
        audit.build_report()


def test_change_to_chat_def19_missing_not_in_excel_note_fails_closed(tmp_path, monkeypatch):
    original = json.loads(audit.RAM_FIXTURE.read_text(encoding="utf-8"))
    original["observed"]["direct_conversation_case"]["note"] = "unverified Excel row"
    fixture = tmp_path / "altered_ram_note.json"
    fixture.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(audit, "RAM_FIXTURE", fixture)
    with pytest.raises(ValueError, match="DEF19 chat source"):
        audit.build_report()


def test_assumption_extraction_rejects_missing_source_trace():
    with pytest.raises(ValueError, match="PvP engine assumption ledger"):
        audit._pvp_engine_assumptions({"model_applied_assumptions": []})
    with pytest.raises(ValueError, match="Ram target damage events"):
        audit._ram_engine_assumptions({"round1_events": [
            {"type": "damage", "details": {
                "source_unit_id": "barbarian_deckwrecker",
                "target_unit_id": "ram_ship", "assumption_ids": [],
            }}
        ]})
