"""P0 synthetic real-engine multi-round healing/initiative invariants.

These are deliberately INVENTED controlled armies, never Gameforge reports.
The bounded exact-full-clear Doctor subset is testable; neither unknown
partial Doctor allocation nor Gameforge Accuracy/kill focus is inferred.
"""
from ikariam_battle import simulate
from ikariam_battle.engine import _apply_supported_doctor_healing
from ikariam_battle.models import ArmyUnit, Slot, Wave
from ikariam_battle.profiles import SupportProfile
from ikariam_battle.units import UnitRegistry


def _scenario(doctors):
    # Hoplites are synthetic sustaining fillers; small air/flank groups make
    # both a casualty and nonzero wounded survivors observable.
    defender_units = [
        {"unit_id": "hoplite", "quantity": 350},
        {"unit_id": "gyrocopter", "quantity": 3},
        {"unit_id": "swordsman", "quantity": 3},
    ]
    if doctors:
        defender_units.append({"unit_id": "doctor", "quantity": doctors})
    return {
        "policy": "experimental",
        "battlefield": "land-max",
        "max_rounds": 3,
        "attacker": {"units": [
            {"unit_id": "hoplite", "quantity": 350},
            {"unit_id": "gyrocopter", "quantity": 3},
            {"unit_id": "swordsman", "quantity": 3},
        ]},
        "defender": {"units": defender_units},
    }


def _slots(result, round_no, side, unit_id):
    return [
        slot for slot in result["rounds"][round_no][side]["slots"]
        if slot["unit_id"] == unit_id
    ]


def _events(result, round_no, kind, side=None):
    return [
        event for event in result["events"]
        if event["round"] == round_no and event["type"] == kind
        and (side is None or event["side"] == side)
    ]


def _slot_state(result, round_no, side, unit_id):
    return sorted(
        (s["damage_position"], s["units"], s["damage"], s["casualties"])
        for s in _slots(result, round_no, side, unit_id)
    )


def test_real_round_two_doctor_full_clear_repairs_humans_not_machine_gyro():
    baseline = simulate(_scenario(0))
    treated = simulate(_scenario(50))
    for result in (baseline, treated):
        assert result["rounds_completed"] >= 2, result["status"]
        assert len(result["rounds"]) >= 3
        assert sum(s["units"] for s in _slots(result, 1, "defender", "gyrocopter")) == 2
        assert sum(s["damage"] for s in _slots(result, 1, "defender", "gyrocopter")) == 340
        assert sum(s["damage"] for s in _slots(result, 1, "defender", "swordsman")) > 0
        assert _events(result, 2, "damage", "defender"), "Round 2 must actually fight"
        gyro_fire = [
            e for e in _events(result, 2, "damage", "defender")
            if e["details"].get("source_unit_id") == "gyrocopter"
        ]
        assert gyro_fire and sum(e["details"]["firing_units"] for e in gyro_fire) > 0

    # Doctor has no impact on the preceding first-round attack/death/HP ledger.
    for unit_id in ("gyrocopter", "swordsman", "hoplite"):
        assert _slot_state(baseline, 1, "defender", unit_id) == (
            _slot_state(treated, 1, "defender", unit_id)
        )
    assert not _events(baseline, 2, "healing", "defender")
    healing_events = _events(treated, 2, "healing", "defender")
    assert len(healing_events) == 1
    detail = healing_events[0]["details"]
    assert detail["support_unit_id"] == "doctor"
    assert detail["exact_subset"] == "capacity_covers_all_eligible_persistent_damage"
    assert detail["healing_rr_order"] == "order_invariant_for_full_clear"
    assert 0 < detail["eligible_damage_before"] <= detail["capacity"]
    assert detail["healing"] == detail["eligible_damage_before"]
    assert detail["healing"] == sum(detail["affected_units"].values())
    assert detail["affected_units"]["swordsman"] > 0
    assert "gyrocopter" not in detail["affected_units"]
    assert not _events(treated, 2, "healing_allocation_unresolved", "defender")

    # Dead units are not a healing target; later combat may kill more but
    # must not turn a dead unit back into a Round-2 survivor.
    for unit_id in ("gyrocopter", "swordsman"):
        alive_r1 = sum(s["units"] for s in _slots(treated, 1, "defender", unit_id))
        alive_r2 = sum(s["units"] for s in _slots(treated, 2, "defender", unit_id))
        assert alive_r1 < 3
        assert alive_r2 <= alive_r1


def test_partial_doctor_capacity_remains_unknown_without_phantom_repair():
    swords = Wave(
        ArmyUnit("swordsman", 80, "patient-wave"), 0,
        [
            Slot("left-flank", "flank", 1, 1, "swordsman",
                 "patient-wave", 40, 40, 3000),
            Slot("right-flank", "flank", 2, 2, "swordsman",
                 "patient-wave", 40, 40, 3000),
        ],
    )
    doctor = Wave(ArmyUnit("doctor", 1, "doctor-wave"), 0, [], 0, None, 1)
    before = [(s.units, s.damage) for s in swords.slots]
    events, applied = [], {}
    healed = _apply_supported_doctor_healing(
        [swords, doctor],
        UnitRegistry.load(include_barbarians=True),
        SupportProfile.load(), events, 2, "defender", applied,
    )
    assert healed == 0
    assert before == [(s.units, s.damage) for s in swords.slots]
    assert "EXP-HEAL-NONE-001" in applied
    assert not any(e.type == "healing" for e in events)
    warnings = [e for e in events if e.type == "healing_allocation_unresolved"]
    assert len(warnings) == 1
    details = warnings[0].details
    assert details["rule_id"] == "UNKNOWN-HEALING-ALLOCATION"
    assert details["capacity"] == 4000
    assert details["eligible_damage"] == 6000
    assert details["unresolved_damage"] == 6000
    assert details["action"] == "no_partial_healing_applied"
