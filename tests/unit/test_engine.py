from ikariam_battle import simulate


SCENARIO = {
    "ruleset": "paper-2020", "battlefield": "small-land", "max_rounds": 2,
    "attacker": {"units": [{"unit_id": "sulphur_carabineer", "quantity": 42, "attack_upgrade": 3}]},
    "defender": {"units": [{"unit_id": "hoplite", "quantity": 90, "defense_upgrade": 3}]},
}


def test_strict_mode_exposes_open_kill_selection():
    result = simulate({**SCENARIO, "policy": "strict"})
    assert result["status"] == result["outcome"] == "inconclusive"
    assert result["rounds_completed"] == 0
    assert any(event["type"] == "unsupported_mechanic" for event in result["events"])
    assert not result["assumptions"]


def test_experimental_mode_is_reproducible_and_traced():
    scenario = {**SCENARIO, "policy": "experimental"}
    first, second = simulate(scenario), simulate(scenario)
    assert first == second
    assert first["assumptions"]
    assert any(event["type"] == "attacking_matrix" for event in first["events"])
    assert all(slot["units"] >= 0 for side in first["final_state"].values() for slot in side["slots"])


def test_damage_is_preserved_as_casualties_plus_persistent_damage():
    result = simulate({**SCENARIO, "policy": "experimental", "max_rounds": 1})
    damage_events = [event for event in result["events"] if event["type"] == "damage" and event["side"] == "attacker"]
    hp = 56
    assert all(e["details"]["damage"] + e["details"].get("prior_damage", 0) ==
               e["details"]["casualties"] * hp + e["details"]["persistent_damage"] for e in damage_events)
