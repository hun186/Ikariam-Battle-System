"""Bounded Experimental naval hypotheses must not depend on Wave serialization.

All fleets are SYNTHETIC CONTROLLED arrangements, not real-game shot logs.
The carrier tuple tests are in-sample; no official Accuracy/overkill assertion.
"""
from copy import deepcopy

import pytest

from ikariam_battle import simulate
from ikariam_battle.accuracy import NAVAL_FAST_CARRIER_FOCUS_ID
from ikariam_battle.naval_focus import (
    NAVAL_DECK_OVERKILL_RULE_ID,
    NAVAL_RAM_SHARE_RULE_ID,
)


def _split_unit(scenario, side, unit_id, count):
    """Give two source Waves separate identities without changing total ships."""
    changed = deepcopy(scenario)
    rows = changed[side]["units"]
    original = next(x for x in rows if x["unit_id"] == unit_id)
    assert original["quantity"] == 2 * count
    rows.remove(original)
    for i in range(2):
        row = {**original, "quantity": count}
        row.update({
            "wave_id": f"experimental-split-{i}",
            "entry_batch_id": f"experimental-batch-{i}",
        })
        rows.append(row)
    return changed


def _target_slot_state(result, side, unit_id):
    return sorted(
        (slot["damage_position"], slot["units"], slot["damage"], slot["casualties"])
        for slot in result["rounds"][1][side]["slots"]
        if slot["unit_id"] == unit_id
    )


def _candidate_events(result, source_id, target_id, rule_id):
    return [
        e for e in result["events"]
        if e["round"] == 1 and e["type"] == "damage"
        and e["details"].get("source_unit_id") == source_id
        and e["details"].get("target_unit_id") == target_id
        and rule_id in e["details"].get("assumption_ids", ())
    ]


@pytest.mark.parametrize("attack,armor,expected", [
    (12, 8, 2), (20, 16, 2), (17, 18, 1),
])
def test_calibrated_pvp_carrier_same_for_one_or_two_source_waves(
    attack, armor, expected,
):
    scenario = {
        "policy": "experimental", "battlefield": "naval-max", "max_rounds": 1,
        "attacker": {"forge_level": 5, "units": [
            {"unit_id": "steam_ram", "quantity": 35},
            {"unit_id": "paddle_speedboat", "quantity": 30,
             "attack_upgrade": attack},
        ]},
        "defender": {"forge_level": 5, "units": [
            {"unit_id": "steam_ram", "quantity": 35},
            {"unit_id": "balloon_carrier", "quantity": 6,
             "armor_upgrade": armor},
        ]},
    }
    single = simulate(scenario)
    split = simulate(_split_unit(scenario, "attacker", "paddle_speedboat", 15))
    for result in (single, split):
        assert result["casualties"]["defender"].get("balloon_carrier", 0) == expected
        events = _candidate_events(
            result, "paddle_speedboat", "balloon_carrier",
            NAVAL_FAST_CARRIER_FOCUS_ID,
        )
        # Split source Waves generate separate per-wave event groups, while
        # the shared AM still addresses the same two physical target slots.
        assert len(events) == (4 if result is split else 2)
        assert sum(e["details"]["firing_units"] for e in events) == 30
        assert all(e["details"]["weapon_accuracy"] == 90 for e in events)
    assert _target_slot_state(single, "defender", "balloon_carrier") == (
        _target_slot_state(split, "defender", "balloon_carrier")
    )


def test_ram_pooled_casualties_and_hp_invariant_to_split_source():
    # Barbarian army rules forbid distinct entry batches; the legally
    # split-Wave regression is player Ram ships, not Barbarian Deckwreckers.
    source_id, target_id = "ram_ship", "barbarian_deckwrecker"
    rule, target_side, expected_deaths = (
        NAVAL_DECK_OVERKILL_RULE_ID, "attacker", 18
    )
    scenario = {
        "policy": "experimental", "battlefield": "naval-max", "max_rounds": 1,
        "attacker": {"army_kind": "barbarian", "forge_level": 0, "units": [
            {"unit_id": "barbarian_wedge_paddler", "quantity": 42},
            {"unit_id": "barbarian_deckwrecker", "quantity": 36},
        ]},
        "defender": {"army_kind": "player", "forge_level": 5, "units": [
            {"unit_id": "steam_ram", "quantity": 35},
            {"unit_id": "ram_ship", "quantity": 36,
             "attack_upgrade": 20, "armor_upgrade": 14},
        ]},
    }
    source_side = "attacker" if source_id == "barbarian_deckwrecker" else "defender"
    single = simulate(scenario)
    split = simulate(_split_unit(scenario, source_side, source_id, 18))
    for result in (single, split):
        assert result["rounds"][1]["casualties"][target_side].get(target_id, 0) == expected_deaths
        events = _candidate_events(result, source_id, target_id, rule)
        assert len(events) == 6
        assert sum(e["details"]["firing_units"] for e in events) == 36
        assert all(e["details"]["experimental_pooled_allocation_not_real_shot_trace"]
                   for e in events)
    assert _target_slot_state(single, target_side, target_id) == (
        _target_slot_state(split, target_side, target_id)
    )


def test_uncalibrated_forge_and_upgrade_do_not_activate_carrier_rule():
    for attacker_forge, defender_forge, attack, armor in (
        (0, 0, 17, 18), (5, 5, 13, 18),
    ):
        result = simulate({
            "policy": "experimental", "battlefield": "naval-max",
            "max_rounds": 1,
            "attacker": {"forge_level": attacker_forge, "units": [
                {"unit_id": "steam_ram", "quantity": 35},
                {"unit_id": "paddle_speedboat", "quantity": 30,
                 "attack_upgrade": attack},
            ]},
            "defender": {"forge_level": defender_forge, "units": [
                {"unit_id": "steam_ram", "quantity": 35},
                {"unit_id": "balloon_carrier", "quantity": 6,
                 "armor_upgrade": armor},
            ]},
        })
        assert not _candidate_events(
            result, "paddle_speedboat", "balloon_carrier",
            NAVAL_FAST_CARRIER_FOCUS_ID,
        )
        assert NAVAL_FAST_CARRIER_FOCUS_ID not in {
            x["id"] for x in result["assumptions"]
        }
