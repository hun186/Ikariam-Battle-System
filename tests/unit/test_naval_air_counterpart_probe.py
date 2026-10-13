"""Observed vs conditional air-unit damage, AM and survivor HP must remain separate."""
import json
from math import ceil

from ikariam_battle.profiles import TargetingProfile
from tools.research.naval_air_counterpart_probe import (
    FIXTURE, damage_and_round_observables, report,
)


def _cases():
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {x["case"]: x for x in evidence["observed"]}


def test_observed_battle_reports_preserve_source_and_outcome_shapes():
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert not evidence["source"]["original_battle_reports_attached"]
    assert not evidence["source"]["raw_game_individual_shot_trace_available"]
    values = _cases()
    assert len(values) == 4
    assert values["barbarian_fast_vs_player_carrier_def7"]["reported_player_total_deaths"] == 1
    assert values["barbarian_fast_vs_player_carrier_def8"]["reported_player_total_deaths"] == 0
    assert values["barbarian_fast_vs_player_carrier_def14"]["reported_occupied_slot_bars_percent"] == [65,70]
    reverse = values["player_fast_att14_vs_barbarian_carrier"]
    assert reverse["reported_barbarian_deaths_per_position"] == 1
    assert reverse["reported_survivor_slot_bars_percent"] == [53,65]
    assert reverse["count_is_assumed_from_previous_comparison"]


def test_two_15_ship_source_columns_yield_16_14_row_major_slot_shots():
    for c in _cases().values():
        expected = damage_and_round_observables(c)
        assert expected["model_target_am_hit_counts"] == [16, 14]
        assert sum(expected["model_target_am_hit_counts"]) == 30
        assert expected["target_unit_hp"] == 2800
        assert expected["model_two_source_columns"] == [15, 15]


def test_barbarian_speedboat_player_carrier_defense_7_8_have_same_12_hit_lethal_threshold():
    c = _cases()
    level7=damage_and_round_observables(c["barbarian_fast_vs_player_carrier_def7"])
    level8=damage_and_round_observables(c["barbarian_fast_vs_player_carrier_def8"])
    assert level7["net_damage"] == 250
    assert level8["net_damage"] == 240
    assert ceil(level7["target_unit_hp"]/level7["net_damage"]) == 12
    assert ceil(level8["target_unit_hp"]/level8["net_damage"]) == 12
    # Same 12-shot lethal threshold cannot itself explain 1->0 deaths.


def test_defense14_no_deaths_two_slot_health_bars_match_16_14_conserved_hits():
    c=damage_and_round_observables(_cases()["barbarian_fast_vs_player_carrier_def14"])
    assert c["net_damage"] == 180
    assert c["hypothetical_no_loss_bars_truncated"] == [65,70]
    assert [round(x, 3) for x in c["hypothetical_no_loss_survivor_bars"]] == [65.714,70.0]
    assert c["observed"]["reported_player_total_deaths"] == 0
    assert c["observed"]["reported_occupied_slot_bars_percent"] == [65,70]


def test_reverse_att14_one_loss_each_retained_hp_bars_match_16_14_hits():
    c=damage_and_round_observables(_cases()["player_fast_att14_vs_barbarian_carrier"])
    assert c["net_damage"] == 337
    assert c["hypothetical_all_damage_retained_bars_truncated"] == [53,65]
    assert c["observed"]["reported_barbarian_deaths_per_position"] == 1
    assert c["observed"]["reported_survivor_slot_bars_percent"] == [53,65]
    # The match is conditional; it does not prove real game uses overkill carry.


def test_naval_official_firing_order_speedboats_before_carriers():
    rules = TargetingProfile.load("official-help-naval-targeting")
    assert rules.firing_order.index("anti-balloon") < rules.firing_order.index("balloon")
    assert rules.priorities["anti-balloon"][0] == "balloon"
    # A carrier's priority against other ship classes is NOT earlier than anti-air
    # speedboat fire in the currently implemented per-formation chronology.


def test_full_simulator_control_is_a_different_evidence_class():
    r=report()
    assert len(r["cases"]) == 4
    assert all(x["conditional_arithmetic"]["evidence_class"].startswith("MODEL_") for x in r["cases"])
    assert all(x["current_engine_control"]["evidence_class"].startswith("CONTROLLED_") for x in r["cases"])
    assert all(x["case"]["source"] == "USER_CHAT" for x in r["cases"])
    assert all("source" not in y["current_engine_control"] for y in r["cases"])


def test_actual_engine_am_addresses_same_16_14_target_slots():
    cases = report()["cases"]
    expected_model_losses = [2, 2, 1, 2]
    for test, expected_deaths in zip(cases, expected_model_losses):
        control = test["current_engine_control"]
        assert control["rounds_completed"] == 1
        assert control["invented_first_line_filler_not_observed"] is True
        assert control["model_target_units_lost"] == expected_deaths
        target_slots = control["target_slots"]
        assert len(target_slots) == 2
        assert {s["line"] for s in target_slots} == {"balloon"}
        target_matrix = [
            e["details"].get("trace", {}).get("hits_by_damage_position", {})
            for e in control["attacking_matrix_events"]
            if e.get("side") == "attacker"
            and e["details"].get("unit_id") == test["case"]["attacker"]
        ]
        assert target_matrix, "Production attacking matrix should fire fast boats"
        assert any(
            sorted(v.values()) == [14, 16] for v in target_matrix
        ), target_matrix


def test_actual_current_model_vs_user_report_are_not_assumed_equal():
    cases = report()["cases"]
    assert [x["current_engine_control"]["model_target_units_lost"] for x in cases] == [
        2, 2, 1, 2
    ]
    # 7/8/14 defenses differ in REAL battle from model's 2/2/1 kills.
    assert [c["case"]["reported_player_total_deaths"] for c in cases[:3]] == [1,0,0]
    reverse = cases[3]
    assert reverse["case"]["reported_barbarian_deaths_per_position"] == 1
    assert [x["casualties"] for x in reverse["current_engine_control"]["target_slots"]] == [1,1]
    # In the reverse case, the engine discards lethal overkill: source 337
    # requires nine hits to sink a 2,800-HP carrier; 9*337-2800=233 lost.
    assert 9*337-2800 == 233
    assert [int(100*(s["units"]*2800-s["damage"])/(s["units"]*2800))
            for s in reverse["current_engine_control"]["target_slots"]] == [57,69]
    assert reverse["conditional_arithmetic"]["hypothetical_all_damage_retained_bars_truncated"] == [53,65]
