import json

import pytest

from ikariam_battle.calibration import (
    MATCH,
    MISMATCH,
    NOT_ASSESSABLE,
    BattleReportFixture,
    damage_interval_from_report,
    evaluate_fixture,
    ranged_formation_observations,
    run_fixture,
    swordsman_full_flank_observation,
)
from ikariam_battle.models import ScenarioError


SCENARIO = {
    "policy": "experimental",
    "battlefield": "land-mini",
    "max_rounds": 1,
    "attacker": {"units": [{"unit_id": "hoplite", "quantity": 30}]},
    "defender": {"units": [{"unit_id": "hoplite", "quantity": 30}]},
}


def fixture(observations, round_number=1, scenario=None):
    return BattleReportFixture.from_dict({
        "fixture_id": "synthetic-controlled",
        "game_version": "17.5.0",
        "round_number": round_number,
        "scenario": scenario or SCENARIO,
        "observations": observations,
    })


def controlled_result(*, damage=7, units=1, casualties=2, status="completed"):
    slot = {
        "slot_id": "first-1",
        "line": "first",
        "physical_position": 2,
        "damage_position": 1,
        "unit_id": "hoplite",
        "wave_id": "wave-1",
        "units": units,
        "damage": damage,
    }
    events = [{
        "round": 1,
        "phase": "fire",
        "type": "damage",
        "side": "attacker",
        "details": {
            "target_side": "defender",
            "target_line": "first",
            "target_damage_position": 1,
            "casualties": casualties,
        },
    }]
    return {
        "status": status,
        "rounds_completed": 1,
        "rounds": [{"round": 0}, {"round": 1, "defender": {"slots": [slot]}, "attacker": {"slots": []}}],
        "events": events,
    }


def test_damage_percentage_round_up_maps_to_interval():
    assert damage_interval_from_report(1, 1120) == (1, 11)


def test_damage_percent_match_uses_integer_persistent_damage_interval():
    result = evaluate_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                        "damage_percent": 1}]), controlled_result())
    assessment = result.assessments[0]
    assert (assessment.status, assessment.expected_interval, assessment.simulated) == (MATCH, (1, 11), 7)
    json.dumps(result.as_dict())


def test_damage_percent_mismatch_reports_predicted_damage():
    result = evaluate_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                        "damage_percent": 1}]), controlled_result(damage=12))
    assessment = result.assessments[0]
    assert (assessment.status, assessment.expected_interval, assessment.simulated) == (MISMATCH, (1, 11), 12)


def test_barbarian_damage_percent_uses_combined_calibration_registry():
    barbarian_scenario = {
        "policy": "experimental",
        "battlefield": "land-mini",
        "max_rounds": 1,
        "attacker": {"army_kind": "player", "units": [{"unit_id": "hoplite", "quantity": 30}]},
        "defender": {"army_kind": "barbarian", "units": [
            {"unit_id": "barbarian_axe_swinger", "quantity": 30,
             "entry_batch_id": "barbarian-garrison"}
        ]},
    }
    observed = fixture(
        [{"side": "defender", "line": "first", "damage_position": 1, "damage_percent": 1}],
        scenario=barbarian_scenario,
    )
    result = controlled_result(damage=7, units=1)
    result["rounds"][1]["defender"]["slots"][0]["unit_id"] = "barbarian_axe_swinger"
    assessment = evaluate_fixture(observed, result).assessments[0]
    assert assessment.status == MATCH
    assert assessment.expected_interval == (1, 11)


def test_run_fixture_supports_barbarian_damage_percent_observation():
    barbarian_scenario = {
        "policy": "experimental",
        "battlefield": "land-mini",
        "max_rounds": 1,
        "attacker": {"army_kind": "player", "units": [{"unit_id": "hoplite", "quantity": 30}]},
        "defender": {"army_kind": "barbarian", "units": [
            {"unit_id": "barbarian_axe_swinger", "quantity": 30,
             "entry_batch_id": "barbarian-garrison"}
        ]},
    }
    result = run_fixture(fixture(
        [{"side": "defender", "line": "first", "damage_position": 1, "damage_percent": 0}],
        scenario=barbarian_scenario,
    ))
    assert result.reached_round == 1
    assert result.assessments[0].field == "damage_percent"
    assert result.assessments[0].status in {MATCH, MISMATCH}


@pytest.mark.parametrize(("reported", "expected"), [(2, MATCH), (3, MISMATCH)])
def test_casualties_are_aggregated_from_exact_target_slot_events(reported, expected):
    result = evaluate_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                        "casualties": reported}]), controlled_result())
    assessment = result.assessments[0]
    assert assessment.status == expected
    assert assessment.simulated == 2
    assert assessment.reason == "EXACT-TARGET-SLOT-DAMAGE-EVENTS"


def test_life_percent_is_accepted_but_explicitly_not_assessable():
    result = evaluate_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                        "life_percent": 99}]), controlled_result())
    assessment = result.assessments[0]
    assert assessment.status == NOT_ASSESSABLE
    assert assessment.reason == "UNKNOWN-BATTLE-REPORT-LIFE-PERCENT-SEMANTICS"


def test_missing_round_marks_each_requested_field_not_assessable():
    result = evaluate_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                        "casualties": 2, "damage_percent": 1}], round_number=2),
                              controlled_result())
    assert result.reached_round == 1
    assert [item.status for item in result.assessments] == [NOT_ASSESSABLE, NOT_ASSESSABLE]
    assert {item.reason for item in result.assessments} == {"SIMULATION-ROUND-NOT-REACHED"}


def test_unsupported_simulation_exposes_blocker_without_false_mismatch():
    scenario = {**SCENARIO, "battlefield": "land-small",
                "attacker": {"units": [{"unit_id": "swordsman", "quantity": 180}]},
                "defender": {"units": [{"unit_id": "hoplite", "quantity": 150}]}}
    result = run_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 1,
                                   "casualties": 0}], scenario=scenario))
    assert result.simulation_status == "inconclusive"
    assert "UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS" in result.blockers
    assert result.assessments[0].status == NOT_ASSESSABLE
    assert result.assessments[0].reason == "SIMULATION-ROUND-NOT-REACHED"


def test_multiple_observations_and_fields_remain_separate_and_deterministic():
    observed = [
        {"side": "defender", "line": "first", "damage_position": 1,
         "casualties": 2, "damage_percent": 1},
        {"side": "attacker", "line": "first", "damage_position": 2, "life_percent": 100},
    ]
    result = controlled_result()
    result["rounds"][1]["attacker"]["slots"] = [{
        "line": "first", "damage_position": 2, "unit_id": "hoplite", "units": 10, "damage": 0,
    }]
    first = evaluate_fixture(fixture(observed), result)
    second = evaluate_fixture(fixture(observed), result)
    assert first == second
    assert [(item.side, item.damage_position, item.field, item.status) for item in first.assessments] == [
        ("defender", 1, "casualties", MATCH),
        ("defender", 1, "damage_percent", MATCH),
        ("attacker", 2, "life_percent", NOT_ASSESSABLE),
    ]


def test_larger_battlefield_slot_is_addressed_by_runtime_line_and_damage_position():
    scenario = {**SCENARIO, "battlefield": "land-medium",
                "attacker": {"units": [{"unit_id": "hoplite", "quantity": 210}]},
                "defender": {"units": [{"unit_id": "hoplite", "quantity": 210}]}}
    result = run_fixture(fixture([{"side": "defender", "line": "first", "damage_position": 7,
                                   "casualties": 0}], scenario=scenario))
    assert result.reached_round == 1
    assert result.assessments[0].reason == "EXACT-TARGET-SLOT-DAMAGE-EVENTS"


@pytest.mark.parametrize("observation", [
    {"side": "other", "line": "first", "damage_position": 1, "casualties": 0},
    {"side": "defender", "line": "unknown", "damage_position": 1, "casualties": 0},
    {"side": "defender", "line": "first", "damage_position": 1},
])
def test_fixture_rejects_invalid_observations(observation):
    with pytest.raises(ScenarioError):
        fixture([observation])


def test_fixture_rejects_duplicate_field_for_same_slot_and_round():
    observation = {"side": "defender", "line": "first", "damage_position": 1, "casualties": 0}
    with pytest.raises(ScenarioError, match="duplicate observation"):
        fixture([observation, observation])


def test_user_observed_ranged_calibration_case_a_is_not_a_production_rule():
    data = ranged_formation_observations()
    case = data["cases"][0]
    assert data["evidence_class"] == "USER_PROVIDED_BATTLE_OBSERVATION"
    assert data["implementation_status"] == "CALIBRATION_ONLY_UNSUPPORTED_IN_PRODUCTION"
    assert "alive" not in case
    assert case["surviving_quantity"] is None
    assert case["surviving_quantity_status"] == "unknown_many_surviving_units_observed"
    assert (case["ammo_pool_shots"], case["observed_second_line_deployed"]) == (2, 2)
    assert case["observed_same_batch_additional_units"] is True
    assert case["observed_non_firing_remainder_in_front"] is True
    assert "front_weapon" in case["unknowns"]


def test_user_observed_ranged_calibration_case_b_keeps_remainder_off_field():
    case = ranged_formation_observations()["cases"][1]
    assert (case["alive"], case["ammo_pool_shots"], case["observed_second_line_slots_full"]) == (838, 282, 7)
    assert case["observed_non_firing_remainder_location"] == "reserve_or_off_field"
    assert case["observed_automatic_front_fallback"] is False

def test_user_observed_swordsman_full_flank_fixture_matches_calibrated_engine():
    observed = swordsman_full_flank_observation()
    result = run_fixture(observed)
    assert observed.evidence_class == "USER_PROVIDED_BATTLE_OBSERVATION"
    assert observed.fixture_id == "swordsman-full-flank-user-observation-2026-06-25"
    assert result.reached_round == 1
    assert result.blockers == ()
    assert result.assessments
    casualty_assessments = [
        item for item in result.assessments if item.field == "casualties"
    ]
    assert casualty_assessments
    assert all(item.status == MATCH for item in casualty_assessments)

    mismatches = [item for item in result.assessments if item.status == MISMATCH]
    assert not mismatches

