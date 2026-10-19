"""Three user-reported player-vs-player anti-air/carrier cases are held-out tests.

All casualties represent empirical user reports. A bounded 74% Round1
Experimental carrier-focus candidate now also matches the ATT17/DEF18 total
in a synthetic controlled fleet; this is IN-SAMPLE, not held-out validation.
"""
import json
from math import ceil

import pytest

from ikariam_battle.battlefield import NAVAL_BATTLEFIELDS
from tools.research.naval_pvp_fast_carrier_probe import FIXTURE, control_case, report


def test_user_pvp_holdout_fixture_preserves_3_cases_and_uncertainties():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert [x["reported_carrier_total_deaths"] for x in raw["observed"]] == [2,2,1]
    assert [(x["attacker_attack_upgrade"],x["defender_armor_upgrade"])
            for x in raw["observed"]] == [(12,8),(20,16),(17,18)]
    assert len(raw["observed"]) == 3
    assert all(x["attacker_count"] == 30 and x["defender_count"] == 6
               for x in raw["observed"])
    assert all(x["death_slots_unknown"] and x["observed_round_number"] == 1
               and x["round_one_confirmed_by_user"] for x in raw["observed"])
    assert raw["source"]["round_confirmation_source"].startswith("USER_FOLLOWUP_CHAT")
    assert raw["model_controls"]["actual_game_observed_round"] == 1
    assert raw["model_controls"]["round_one_confirmed_by_user"]
    assert raw["source"]["forge_confirmation_source"].startswith("USER_FOLLOWUP_CHAT")
    assert all(
        x["attacker_forge_level"] == x["defender_forge_level"] == 5
        and x["both_forge5_confirmed_by_user"]
        for x in raw["observed"]
    )
    assert raw["model_controls"]["actual_game_forge_configuration"] == {
        "attacker_forge": 5, "defender_forge": 5, "confirmed_by_user": True
    }
    assert [x["evidence_class"] for x in raw["model_controls"]["conditional_forge_configs"]] == [
        "USER_CONFIRMED_FORGE_SCOPE", "COUNTERFACTUAL_SENSITIVITY_NOT_OBSERVED"
    ]
    assert raw["model_controls"]["invented_both_sides_front_fillers_not_observed"]
    assert raw["model_controls"]["slots_derived_from_official_help_not_explicitly_reconfirmed_for_these_three_battles"]


@pytest.mark.parametrize(
    ("attack","defense","expected_damage","expected_kill_hits"),
    [(12,8,314,9),(20,16,326,9),(17,18,271,11)],
)
def test_same_forge5_profile_damage_is_computed_not_hardcoded(
    attack,defense,expected_damage,expected_kill_hits
):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    case = next(x for x in raw["observed"]
                if x["attacker_attack_upgrade"] == attack)
    model=control_case(case,attacker_forge=5,defender_forge=5)
    assert case["defender_armor_upgrade"] == defense
    assert model["damage_trace_from_production"]["final_damage"] == expected_damage
    assert model["net_hit"] == expected_damage
    assert model["accuracy"] == 90
    assert model["minimum_hits_to_kill_fresh_ship"] == expected_kill_hits
    assert model["target_ship_hp"] == 2800
    assert model["model_am_hit_slots"] == [16,14]
    assert [s["line"] for s in model["model_carrier_slots"]] == ["balloon","balloon"]


def test_three_current_engine_bounded_candidate_matches_in_sample_totals_only():
    r=report()
    assert len(r["comparisons"]) == 6
    both=[m for m in r["comparisons"]
          if m["forge_config"]=={"attacker":5,"defender":5}]
    attacker_only=[m for m in r["comparisons"]
                   if m["forge_config"]=={"attacker":5,"defender":0}]
    assert [m["reported_total_deaths"] for m in both] == [2,2,1]
    assert all(m["observed_game_round"] == 1 and m["model_rounds_completed"] == 1
               and m["model_round_matches_confirmed_game_round"] for m in both)
    assert all(m["matches_user_confirmed_forge_scope"] for m in both)
    assert all(
        m["forge_scope_evidence_class"] ==
        "USER_CONFIRMED_GAME_FORGE_SCOPE_WITH_SYNTHETIC_ENGINE"
        for m in both
    )
    assert all(not m["matches_user_confirmed_forge_scope"] for m in attacker_only)
    assert all(
        m["forge_scope_evidence_class"] ==
        "COUNTERFACTUAL_FORGE_SENSITIVITY_NOT_USER_OBSERVED"
        for m in attacker_only
    )
    assert [m["model_total_carrier_deaths"] for m in both] == [2,2,1]
    assert [m["model_total_carrier_deaths"] for m in attacker_only] == [2,2,2]
    assert [m["net_hit"] for m in both] == [314,326,271]
    assert [m["net_hit"] for m in attacker_only] == [334,346,291]
    assert all(m["model_rounds_completed"]==1 for m in r["comparisons"])
    assert [[s["casualties"] for s in m["model_carrier_slots"]]
            for m in both] == [[1,1],[1,1],[1,0]]
    assert all([s["casualties"] for s in m["model_carrier_slots"]] == [1,1]
               for m in attacker_only)
    assert all(m["synthetic_frontline_warning"].startswith("Invented")
               for m in r["comparisons"])


def test_pvp_runs_real_model_am_and_no_game_hit_logs():
    first=report()["comparisons"][0]
    assert first["model_am_events"]
    assert any(sorted((e.get("details") or {}).get("trace",{}).get(
        "hits_by_damage_position",{}).values()) == [14,16]
        for e in first["model_am_events"])
    assert first["model_source_damage_events"]
    assert sum(e["details"].get("firing_units",0)
               for e in first["model_source_damage_events"]) == 30
    assert all("accuracy_decisions" in e["details"]
               for e in first["model_source_damage_events"])
    assert NAVAL_BATTLEFIELDS["naval-max"].lines["anti-balloon"].slot_space == 15
    assert NAVAL_BATTLEFIELDS["naval-max"].lines["balloon"].slot_space == 15


def test_realized_focus_fraction_remains_hypothesis_not_official_accuracy():
    hp=2800
    # Assuming 16/14 full successful hits, fixed SAME realized share across
    # the three PVP attack grades, two deaths at 314/326, and the ONE death at
    # 271 occurring in 16-hit slot, the possible overlap is below.
    min_fraction=max(hp/(14*314),hp/(14*326),hp/(16*271))
    max_fraction=hp/(14*271)
    assert 0.645 < min_fraction < 0.647
    assert 0.737 < max_fraction < 0.739
    # A simple test ratio of 70% fits all three casualty totals conditionally.
    f=0.70
    predicted=[
        sum(int(shots*d*f>=hp) for shots in (16,14))
        for d in (314,326,271)
    ]
    assert predicted==[2,2,1]
    # This is not a legal discrete shot selector. It must NEVER be treated
    # as confirmed Accuracy=90 meaning f=0.70.


def test_pvp_artifact_preserves_user_evidence_source_and_all_forge_caveats():
    """Uploaded JSON must be self-auditing, not only predictions."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = report()
    assert result["source"] == fixture["source"]
    assert result["raw_observations"] == fixture["observed"]
    assert result["model_controls"] == fixture["model_controls"]
    assert not result["source"]["original_battle_reports_attached"]
    assert result["source"]["forge_confirmation_source"].startswith("USER_FOLLOWUP_CHAT")
    assert "round" in result["source"]["comment"].lower()
    assert all(x["observed_round_number"] == 1 and x["round_one_confirmed_by_user"]
               for x in result["raw_observations"])
    assert result["source"]["round_confirmation_source"] == fixture["source"]["round_confirmation_source"]
    assert any(
        c["forge_scope_evidence_class"] == "COUNTERFACTUAL_FORGE_SENSITIVITY_NOT_USER_OBSERVED"
        for c in result["comparisons"]
    )


def test_future_agent_is_routed_to_all_three_naval_evidence_fixtures():
    root = FIXTURE.parents[3]
    agent = (root / "AGENTS.md").read_text(encoding="utf-8")
    handoff = (root / "docs/calibration/naval-inverse-engineering-handoff.md").read_text(encoding="utf-8")
    for stem in (
        "naval_ram_deckwrecker_20261013.json",
        "naval_air_counterparts_20261013.json",
        "naval_pvp_fast_boat_carrier_20261013.json",
    ):
        assert stem in agent
        assert stem in handoff
    assert "three" in handoff.lower() or "三份" in handoff


def test_game_confirmed_round_one_does_not_imply_slot_or_fleet_identity():
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert all(case["observed_round_number"] == 1 for case in evidence["observed"])
    assert all(case["death_slots_unknown"] for case in evidence["observed"])
    assert evidence["model_controls"]["invented_both_sides_front_fillers_not_observed"]
    assert evidence["source"]["original_battle_reports_attached"] is False
