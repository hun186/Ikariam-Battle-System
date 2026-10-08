"""Pinned user-observed Ikariam rounds: evidence tests and expected rule gaps.

The JSON fixtures contain user-observed casualties and the exact corrected input
scenario. Tests marked xfail are *not approved behavior*; they represent known
incomplete mechanics and must become passing tests before that feature ships.
"""
import json
from pathlib import Path

import pytest

from ikariam_battle import simulate


CASES = Path(__file__).resolve().parents[1] / "fixtures" / "reverse_engineering"


def _case(name):
    return json.loads((CASES / (name + "_round1.json")).read_text(encoding="utf-8"))


def _simulate(name, rounds=1):
    case = _case(name)
    scenario = dict(case["scenario"])
    scenario["max_rounds"] = rounds
    return simulate(scenario)


@pytest.mark.parametrize("name", ("reikjavikas", "crispi"))
def test_round1_reference_fixture_is_a_consistent_observation(name):
    case = _case(name)
    assert case["schema_version"] == 1
    assert case["scenario"]["wall_level"] == case["wall_level"]
    for side, units in case["observed"]["slot_losses"].items():
        for unit_id, losses in units.items():
            assert sum(losses) == case["observed"]["casualties"][side][unit_id]
            assert all(isinstance(loss, int) and loss >= 0 for loss in losses)
    assert case["scenario"]["attacker"]["forge_level"] == case["legacy_model"]["forge_level"]["attacker"]
    assert case["scenario"]["defender"]["forge_level"] == case["legacy_model"]["forge_level"]["defender"]


def test_crispi_wall_is_five_breached_not_three_and_forge_is_asymmetric():
    case = _case("crispi")
    assert case["observed"]["wall_alive_physical"] == [1, 0, 0, 0, 0, 0, 1]
    assert case["observed"]["wall_breached_physical_positions"] == [2, 3, 4, 5, 6]
    assert case["scenario"]["attacker"]["forge_level"] == 5
    assert case["scenario"]["defender"]["forge_level"] == 0
    assert case["observed"]["casualties"]["attacker"]["hoplite"] == 52
    assert case["legacy_model"]["casualties"]["attacker"]["hoplite"] == 94


def test_crispi_air_casualties_and_net_damage_match_with_attacker_only_forge():
    case = _case("crispi")
    result = _simulate("crispi")
    assert result["rounds"][1]["casualties"]["attacker"]["bombardier"] == 20
    assert result["rounds"][1]["casualties"]["defender"]["bombardier"] == 30
    assert result["rounds"][1]["casualties"]["attacker"].get("gyrocopter", 0) == 0
    assert result["rounds"][1]["casualties"]["defender"].get("gyrocopter", 0) == 0
    gyro = [
        event for event in result["events"]
        if event["round"] == 1
        and event["type"] == "damage_calculation"
        and event["details"].get("source_unit_id") == "gyrocopter"
        and event["details"].get("target_unit_id") == "bombardier"
    ]
    assert {(e["side"], e["details"]["forge_level"], e["details"]["final_damage"])
            for e in gyro} == {("attacker", 5, 432), ("defender", 0, 320)}


def test_reikjavikas_air_hits_defending_bombardiers_exactly():
    case = _case("reikjavikas")
    result = _simulate("reikjavikas")
    assert result["rounds"][1]["casualties"]["defender"]["bombardier"] == 30
    assert case["observed"]["slot_losses"]["defender"]["bombardier"] == [15, 15]
    assert case["scenario"]["attacker"]["forge_level"] == 5
    assert case["scenario"]["defender"]["forge_level"] == 5


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: seven intact Town Wall sections must occupy all defender First slots until next round")
def test_crispi_defender_first_is_entirely_wall_at_initial_deployment():
    result = _simulate("crispi")
    defender = result["rounds"][0]["defender"]
    assert not [slot for slot in defender["slots"]
                if slot["line"] == "first" and slot["units"] > 0]


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: Flank remains empty on BOTH sides while any active Town Wall section survives")
def test_crispi_round1_both_sides_flank_are_empty():
    result = _simulate("crispi")
    for side in ("attacker", "defender"):
        assert not [slot for slot in result["rounds"][0][side]["slots"]
                    if slot["line"] == "flank" and slot["units"] > 0]


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: a breach during round N permits defender First troops to enter only in round N+1")
def test_crispi_breached_wall_never_allows_defender_first_to_fire_in_round1():
    result = _simulate("crispi")
    defender_first_fire = [
        event for event in result["events"]
        if event["round"] == 1 and event["side"] == "defender"
        and event["type"] == "damage"
        and event["details"].get("source_unit_id") in {"hoplite", "steam_giant", "spartan"}
        and event["details"].get("firing_phase") == "first"
    ]
    assert defender_first_fire == []


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: partial wall breach changes First deployment only at the next round boundary")
def test_crispi_next_round_first_occupies_only_prior_round_breached_positions():
    result = _simulate("crispi", rounds=2)
    round1_breaches = {
        event["details"]["damage_position"]
        for event in result["events"]
        if event["round"] == 1 and event["type"] == "wall_section_breached"
    }
    assert len(round1_breaches) == 5
    assert len(result["rounds"]) >= 3
    original = [slot for slot in result["rounds"][0]["defender"]["slots"]
                if slot["line"] == "first" and slot["units"] > 0]
    following = [slot for slot in result["rounds"][2]["defender"]["slots"]
                 if slot["line"] == "first" and slot["units"] > 0]
    assert not original
    assert following
    assert all(slot["damage_position"] in round1_breaches for slot in following)


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: after complete wall breach in round N, flank waits until round N+1")
def test_complete_wall_breach_opens_flank_only_from_following_round():
    case = _case("crispi")
    scenario = dict(case["scenario"])
    scenario["wall_level"] = 1
    scenario["max_rounds"] = 2
    result = simulate(scenario)
    breaches = [event for event in result["events"]
                if event["round"] == 1 and event["type"] == "wall_section_breached"]
    assert len(breaches) == 7
    assert all(not [slot for slot in result["rounds"][idx][side]["slots"]
                    if slot["line"] == "flank" and slot["units"] > 0]
               for idx in (0, 1) for side in ("attacker", "defender"))
    assert len(result["rounds"]) >= 3
    assert any(slot["line"] == "flank" and slot["units"] > 0
               for side in ("attacker", "defender")
               for slot in result["rounds"][2][side]["slots"])


def test_open_field_suppressed_wall_allows_flank_from_initial_deployment():
    case = _case("crispi")
    scenario = dict(case["scenario"])
    scenario["wall_level"] = 1
    scenario["town_hall_level"] = 1
    # Garrison limit = 350; the defender's troops greatly exceed this.
    result = simulate(scenario)
    assert result["garrison_status"]["open_field"] is True
    assert any(slot["line"] == "flank" and slot["units"] > 0
               for slot in result["rounds"][0]["defender"]["slots"])


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: real REIKJAVIKAS defender anti-air kills 13 Gyrocopters per slot, current model kills 15")
def test_reikjavikas_gyrocopter_accurate_air_death_distribution():
    case = _case("reikjavikas")
    result = _simulate("reikjavikas")
    losses = sorted(
        (slot["physical_position"], slot["casualties"])
        for slot in result["rounds"][1]["attacker"]["slots"]
        if slot["unit_id"] == "gyrocopter" and slot["line"] == "anti-balloon"
    )
    assert [loss for _, loss in losses] == case["observed"]["air"]["attacker_gyrocopter"]


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: wall occupancy, wall offense and Carabineer redistribution differ from observed Crispi 52 kills")
def test_crispi_round1_total_hoplite_losses_match_observed_case():
    case = _case("crispi")
    result = _simulate("crispi")
    assert result["rounds"][1]["casualties"]["attacker"]["hoplite"] == case["observed"]["casualties"]["attacker"]["hoplite"]
