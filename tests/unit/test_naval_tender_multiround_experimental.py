"""Actual multi-round engine regressions for provisional Navy HP and Tenders.

SYNTHETIC 35/42 First-line filler fleets are not the user's historical fleet.
Tender full-clear is executable; partial capacity remains explicitly UNKNOWN.
"""
from copy import deepcopy

import pytest

from ikariam_battle import simulate
from ikariam_battle.naval_focus import NAVAL_RAM_SHARE_RULE_ID


def _scenario(armor, tenders):
    units = [
        {"unit_id": "steam_ram", "quantity": 35},
        {"unit_id": "ram_ship", "quantity": 36,
         "attack_upgrade": 20, "armor_upgrade": armor},
    ]
    if tenders:
        units.append({"unit_id": "tender", "quantity": tenders})
    return {
        "policy": "experimental", "battlefield": "naval-max", "max_rounds": 3,
        "attacker": {"army_kind": "barbarian", "forge_level": 0, "units": [
            {"unit_id": "barbarian_wedge_paddler", "quantity": 42},
            {"unit_id": "barbarian_deckwrecker", "quantity": 36},
        ]},
        "defender": {"army_kind": "player", "forge_level": 5, "units": units},
    }


def _ram_slots(result, number):
    return [
        s for s in result["rounds"][number]["defender"]["slots"]
        if s["unit_id"] == "ram_ship"
    ]


def _round_events(result, number, event_type, side=None):
    return [
        e for e in result["events"]
        if e["round"] == number and e["type"] == event_type
        and (side is None or e["side"] == side)
    ]


@pytest.mark.parametrize("armor,remaining", [(14, 30), (19, 36)])
def test_real_multiround_tender_full_clear_keeps_deaths_and_restores_wounds(
    armor, remaining,
):
    no_heal = simulate(_scenario(armor, 0))
    full_heal = simulate(_scenario(armor, 50))
    for result in (no_heal, full_heal):
        assert result["rounds_completed"] >= 2, result.get("status")
        round_one = _ram_slots(result, 1)
        assert len(round_one) == 6
        assert sum(s["units"] for s in round_one) == remaining
        assert sum(s["casualties"] for s in round_one) == 36 - remaining
        assert sum(s["damage"] for s in round_one) > 0
        first_events = [
            e for e in _round_events(result, 1, "damage")
            if e["details"].get("source_unit_id") == "barbarian_deckwrecker"
            and e["details"].get("target_unit_id") == "ram_ship"
        ]
        assert len(first_events) == 6
        assert all(
            NAVAL_RAM_SHARE_RULE_ID in e["details"].get("assumption_ids", ())
            for e in first_events
        )
        assert _round_events(result, 2, "damage"), "Round 2 must actually fight"
        # Repair only operates on surviving hulls; it cannot restore dead Rams.
        assert sum(s["units"] for s in _ram_slots(result, 2)) <= remaining

    # Tender does not heal before the first battle round.
    assert [
        (s["damage_position"], s["units"], s["damage"])
        for s in _ram_slots(no_heal, 1)
    ] == [
        (s["damage_position"], s["units"], s["damage"])
        for s in _ram_slots(full_heal, 1)
    ]
    defender_heals = _round_events(full_heal, 2, "healing", "defender")
    assert len(defender_heals) == 1
    healing = defender_heals[0]["details"]
    assert healing["support_unit_id"] == "tender"
    assert healing["exact_subset"] == "capacity_covers_all_eligible_persistent_damage"
    assert healing["healing"] == healing["eligible_damage_before"] > 0
    assert healing["affected_units"]["ram_ship"] >= sum(
        s["damage"] for s in _ram_slots(full_heal, 1)
    )
    assert not _round_events(no_heal, 2, "healing", "defender")
    # Both settings execute a real second-round naval AM/damage phase.
    for result in (no_heal, full_heal):
        ram_fire = [
            e for e in _round_events(result, 2, "damage", "defender")
            if e["details"].get("source_unit_id") == "ram_ship"
        ]
        assert ram_fire and sum(e["details"]["firing_units"] for e in ram_fire) > 0


def test_partial_tender_capacity_is_visible_unknown_not_invented_repair():
    result = simulate(_scenario(14, 1))
    assert result["rounds_completed"] >= 2
    assert sum(s["units"] for s in _ram_slots(result, 1)) == 30
    blocked = _round_events(
        result, 2, "healing_allocation_unresolved", "defender"
    )
    assert blocked, "Do not hide an insufficient Tender repair capacity"
    assert all(
        e["details"]["capacity"] < e["details"]["eligible_damage"]
        and e["details"]["rule_id"] == "UNKNOWN-TENDER-HEALING-ALLOCATION"
        and e["details"]["action"] == "no_partial_healing_applied"
        for e in blocked
    )
    assert not _round_events(result, 2, "healing", "defender")
    assert "EXP-TENDER-HEAL-NONE-001" in {
        item["id"] for item in result["assumptions"]
    }
