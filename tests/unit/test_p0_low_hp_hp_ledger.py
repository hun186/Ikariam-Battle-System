"""Land low-HP numeric HP ledgers, not only firing eligibility tests.

Synthetic scenarios do NOT represent owner-observed Gameforge casualty records.
No new official Accuracy or kill-concentration claims are made here.
"""
from ikariam_battle import simulate
from ikariam_battle.engine import _apply_supported_doctor_healing
from ikariam_battle.models import ArmyUnit, Slot, Wave
from ikariam_battle.profiles import SupportProfile
from ikariam_battle.units import UnitRegistry


def _fight(left, right):
    return simulate({
        "policy": "experimental",
        "battlefield": "land-max",
        "max_rounds": 1,
        "attacker": {"units": left},
        "defender": {"units": right},
    })


def _events_for_target(result, side, target):
    return [
        e["details"] for e in result["events"]
        if e["round"] == 1 and e["type"] == "damage"
        and e["details"].get("target_side") == side
        and e["details"].get("target_unit_id") == target
    ]


def _hp_balance(result, side, unit_id, hp):
    """Account for fresh-target nominal damage, dead HP and discarded excess."""
    incoming = _events_for_target(result, side, unit_id)
    assert incoming
    gross = sum(event["damage"] for event in incoming)
    excess = sum(event["overkill_discarded"] for event in incoming)
    deaths = result["rounds"][1]["casualties"][side].get(unit_id, 0)
    slots = [
        slot for slot in result["rounds"][1][side]["slots"]
        if slot["unit_id"] == unit_id
    ]
    wounds = sum(slot["damage"] for slot in slots)
    assert all(0 <= slot["damage"] < hp * slot["units"] for slot in slots if slot["units"])
    assert gross == deaths * hp + wounds + excess, {
        "side": side, "gross": gross, "dead_hp": deaths * hp,
        "survivor_wounds": wounds, "discarded_overkill": excess,
    }
    return deaths, wounds, gross, excess


def test_gyro_mirror_conserves_each_side_deaths_and_survivor_hp():
    squad = [
        {"unit_id": "hoplite", "quantity": 350},
        {"unit_id": "gyrocopter", "quantity": 3},
    ]
    result = _fight(squad, squad)
    a = _hp_balance(result, "attacker", "gyrocopter", 580)
    d = _hp_balance(result, "defender", "gyrocopter", 580)
    # Three shots cause one two-hit kill, leave a *real* wounded survivor,
    # and discard only the exact lethal excess. A 30v30 case had zero wounds.
    assert a == d == (1, 340, 1020, 100)
    for side in ("attacker", "defender"):
        slots = [s for s in result["rounds"][1][side]["slots"]
                 if s["unit_id"] == "gyrocopter"]
        assert sum(s["units"] for s in slots) == 2
        assert sum(s["damage"] for s in slots) == 340
    gyro_events = [
        e for e in result["events"]
        if e["type"] == "damage"
        and e["details"].get("source_unit_id") == "gyrocopter"
    ]
    assert {e["side"] for e in gyro_events} == {"attacker", "defender"}
    assert {e["details"]["firing_phase"] for e in gyro_events} == {"anti-balloon"}
    assert "EXP-ACCURACY-CONCENTRATION-001" in {
        item["id"] for item in result["assumptions"]
    }


def test_gyro_preemptive_balloon_kill_accounts_for_actual_hp_not_fake_fire():
    result = _fight(
        [{"unit_id": "hoplite", "quantity": 350},
         {"unit_id": "gyrocopter", "quantity": 30}],
        [{"unit_id": "hoplite", "quantity": 350},
         {"unit_id": "bombardier", "quantity": 1}],
    )
    death, wounds, gross, excess = _hp_balance(
        result, "defender", "bombardier", 800
    )
    assert death == 1
    assert wounds == 0
    assert gross == 800 + excess
    assert not any(
        e["type"] == "damage"
        and e["details"].get("source_unit_id") == "bombardier"
        for e in result["events"]
    )


def test_doctor_full_clear_heals_human_swordsman_but_not_machine_gyro():
    """Doctor subset never accidentally repairs gyro (or resurrects casualties)."""
    gyro = Wave(
        ArmyUnit("gyrocopter", 3, "gyro-wave"), 0,
        [Slot("gyro-slot", "anti-balloon", 1, 1, "gyrocopter",
              "gyro-wave", 2, 2, 300)],
    )
    sword = Wave(
        ArmyUnit("swordsman", 3, "sword-wave"), 0,
        [Slot("sword-slot", "flank", 1, 1, "swordsman",
              "sword-wave", 2, 2, 200)],
    )
    doctor = Wave(ArmyUnit("doctor", 2, "doctor-wave"), 0, [], 0, None, 2)
    # Each concrete Wave began with three units but has only two living
    # units and no reserve: there is one existing death to protect.
    assert gyro.unit.quantity == sword.unit.quantity == 3
    assert gyro.alive == sword.alive == 2
    assert gyro.reserve == sword.reserve == 0
    before_living = (gyro.alive, sword.alive)
    events, assumptions = [], {}
    healed = _apply_supported_doctor_healing(
        [gyro, sword, doctor],
        UnitRegistry.load(include_barbarians=True),
        SupportProfile.load(),
        events, 2, "attacker", assumptions,
    )
    assert healed == 200
    assert sword.slots[0].damage == 0
    assert gyro.slots[0].damage == 300
    assert gyro.slots[0].units == sword.slots[0].units == 2
    assert (gyro.alive, sword.alive) == before_living
    assert (gyro.unit.quantity - gyro.alive, sword.unit.quantity - sword.alive) == (1, 1)
    heals = [e for e in events if e.type == "healing"]
    assert len(heals) == 1
    assert heals[0].details["affected_units"] == {"swordsman": 200}
    assert heals[0].details["eligibility"] == "land_human_combat"
