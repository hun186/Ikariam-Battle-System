"""Read-only Round2 same-Wave reserve refill, healing and RR state audit.

All patient deaths and wounds are SYNTHETIC. This executes the real engine's
round-start pipeline, but does not reproduce Gameforge shots or combat rounds.
No official partial-healing allocation or Healing-vs-RR order is asserted.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ikariam_battle.engine import _prepare_round_start, _snapshot
from ikariam_battle.models import ArmyUnit, Slot, Wave
from ikariam_battle.profiles import BattleEndProfile, SupportProfile
from ikariam_battle.units import UnitRegistry

PROVENANCE = "SYNTHETIC_SEEDED_ROUND2_SAME_WAVE_RESERVE_RR_NOT_GAME_OBSERVED"
NO_HEAL = "no_support_repack_then_rr"
UNKNOWN = "insufficient_support_no_partial_heal_assumption_then_rr"
FULL = "full_clear_before_rr_order_invariant"
CASES = ((0, 5000), (1, 5000), (1, 5001), (2, 5000), (1, 4000))


def _make_case(domain: str, support_count: int, injury: int):
    if type(support_count) is not int or support_count < 0:
        raise ValueError("support_count must be a nonnegative integer")
    if type(injury) is not int or injury < 0 or injury > 5001:
        raise ValueError("injury must be a nonnegative supported controlled sample <= 5001")
    if domain == "land_doctor":
        unit_id, support_id, line = "hoplite", "doctor", "first"
        cap, first, second, reserve, hp = 30, 30, 10, 80, 1120
    elif domain == "naval_tender":
        unit_id, support_id, line = "ram_ship", "tender", "flank"
        cap, first, second, reserve, hp = 6, 6, 2, 16, 3080
    else:
        raise ValueError("unrecognized domain")
    wave_id = f"{domain}-survivors"
    # One *existing* death. All 5000/5001 remaining damage belongs to living
    # patients. Reserve is already wounded; filling an existing slot may not
    # erase those injuries or invent newly healthy ships/humans.
    patient = Wave(
        ArmyUnit(unit_id, first + second + reserve + 1, wave_id),
        reserve,
        [
            Slot(f"{line}-1", line, 1, 1, unit_id, wave_id, first, cap, 600 if injury else 0),
            Slot(f"{line}-2", line, 2, 2, unit_id, wave_id, second, cap, 200 if injury else 0),
        ],
        injury - 800 if injury else 0,
    )
    if (patient.reserve_damage < 0
            or patient.reserve_damage >= patient.reserve * hp
            or any(s.damage >= s.units * hp for s in patient.slots)):
        raise ValueError("seeded survivor HP is not positive")
    waves = [patient]
    if support_count:
        waves.append(Wave(
            ArmyUnit(support_id, support_count, f"{domain}-support"),
            0, [], 0, None, support_count,
        ))
    return waves, patient, cap, hp


def _ledger(wave: Wave):
    return {
        "unit_id": wave.unit.unit_id,
        "wave_id": wave.unit.wave_id,
        "original_count": wave.unit.quantity,
        "alive": wave.alive,
        "historical_dead": wave.unit.quantity - wave.alive,
        "reserve": wave.reserve,
        "reserve_damage": wave.reserve_damage,
        "slots": [
            {"slot_id": s.slot_id, "position": s.damage_position,
             "units": s.units, "capacity": s.capacity, "damage": s.damage}
            for s in sorted(wave.slots, key=lambda s: s.damage_position)
        ],
        "total_wounds": wave.reserve_damage + sum(s.damage for s in wave.slots),
    }


def audit(domain: str, support_count: int, injury: int):
    waves, patient, cap, hp = _make_case(domain, support_count, injury)
    registry = UnitRegistry.load(include_barbarians=True)
    support = SupportProfile.load()
    before = _ledger(patient)
    assert before["historical_dead"] == 1
    assert before["total_wounds"] == injury
    events, applied = [], {}
    blocked = _prepare_round_start(
        waves, events, 2, "defender", applied,
        registry=registry, support=support,
    )
    if blocked:
        raise AssertionError("unexpected unsupported Round2 same-Wave boundary")
    after = _ledger(patient)
    if (after["alive"] != before["alive"]
            or after["historical_dead"] != before["historical_dead"]
            or after["original_count"] != before["original_count"]):
        raise AssertionError("prior casualty was resurrected or another unit lost")
    if after["reserve"] != before["reserve"] - (cap - before["slots"][1]["units"]):
        raise AssertionError("same-Wave reserve count not conserved by round-start repack")
    if [(s["position"], s["units"]) for s in after["slots"]] != [
            (1, cap), (2, cap)]:
        raise AssertionError("same-Wave physical slot refill was lost")
    if after["reserve"] + sum(s["units"] for s in after["slots"]) != before["alive"]:
        raise AssertionError("deployed plus reserve does not match original survivors")

    capacity = support_count * support.derived_capacity
    outcome = (
        NO_HEAL if support_count == 0
        else FULL if capacity >= injury
        else UNKNOWN
    )
    remaining_wounds = 0 if outcome == FULL else injury
    if after["total_wounds"] != remaining_wounds:
        raise AssertionError("persistent wounds were invented, lost, or incorrectly healed")

    heals = [e for e in events if e.type == "healing"]
    unknowns = [e for e in events if e.type == "healing_allocation_unresolved"]
    if outcome == FULL and injury > 0:
        if len(heals) != 1 or unknowns:
            raise AssertionError("expected exactly one order-invariant full repair")
        detail = heals[0].details
        if (detail.get("healing") != injury
                or detail.get("eligible_damage_before") != injury
                or detail.get("capacity") != capacity
                or detail.get("affected_units", {}).get(patient.unit.unit_id) != injury):
            raise AssertionError("healing event contradicts original damage")
    elif outcome == UNKNOWN:
        rule = (
            "UNKNOWN-HEALING-ALLOCATION" if domain == "land_doctor"
            else "UNKNOWN-TENDER-HEALING-ALLOCATION"
        )
        assumption = (
            "EXP-HEAL-NONE-001" if domain == "land_doctor"
            else "EXP-TENDER-HEAL-NONE-001"
        )
        if heals or len(unknowns) != 1:
            raise AssertionError("unknown partial allocation was represented as completed healing")
        d = unknowns[0].details
        if (d.get("rule_id") != rule
                or d.get("action") != "no_partial_healing_applied"
                or d.get("capacity") != capacity
                or d.get("eligible_damage") != injury
                or assumption not in applied):
            raise AssertionError("partial-heal unknown evidence not preserved")
    elif heals or unknowns:
        raise AssertionError("non-healing case emitted support healing")

    # Independent expected RR values: each slot holds 1/4 and Reserve
    # holds 1/2 of the same surviving Wave after refill. Existing Experimental
    # RR rounds the *combined deployed fraction* half-up, then assigns the
    # remaining indivisible HP by ascending physical damage priority. Thus
    # odd 5001 HP means 1251 to slot 1, 1250 to slot 2, 2500 to Reserve.
    # This is current engine behavior, NOT official Gameforge verification.
    if outcome == FULL:
        expected_slots = [0, 0]
    else:
        whole_per_slot = injury // 4
        deployed_target = (injury + 1) // 2
        priority_remainder = deployed_target - 2 * whole_per_slot
        if not 0 <= priority_remainder <= 2:
            raise AssertionError("invalid independent RR remainder derivation")
        expected_slots = [whole_per_slot + min(priority_remainder, 1),
                          whole_per_slot + max(0, priority_remainder - 1)]
    expected_reserve = remaining_wounds - sum(expected_slots)
    actual_deployed = [x["damage"] for x in after["slots"]]
    if (actual_deployed != expected_slots
            or after["reserve_damage"] != expected_reserve):
        raise AssertionError(
            f"Round2 RR survivor/Reserve HP mismatch: expected "
            f"{expected_slots}/{expected_reserve}, "
            f"actual {actual_deployed}/{after['reserve_damage']}"
        )
    rr_events = [
        e for e in events
        if e.type == "redistribution" and e.details.get("rule") == "RR"
    ]
    if remaining_wounds:
        if len(rr_events) != 1:
            raise AssertionError("RR not applied exactly once")
        d = rr_events[0].details
        if (d.get("total_wave_damage") != remaining_wounds
                or d.get("reserve_damage") != expected_reserve
                or d.get("damage_conserved") is not True
                or d.get("deployed_damage") != {
                    1: expected_slots[0], 2: expected_slots[1],
                }):
            raise AssertionError("RR event does not reflect actual conserved HP")
    elif rr_events:
        raise AssertionError("zero-damage full-clear case must not invent an RR event")

    state = _snapshot(waves, registry, BattleEndProfile.load())
    snap_wave = next(w for w in state["waves"] if w["wave_id"] == patient.unit.wave_id)
    snap_slots = [s for s in state["slots"] if s["wave_id"] == patient.unit.wave_id]
    if (snap_wave["reserve"] != after["reserve"]
            or snap_wave["reserve_damage"] != after["reserve_damage"]
            or len(snap_slots) != 2):
        raise AssertionError("public Round2 snapshot diverges from mutated Wave")
    for s, expected in zip(sorted(snap_slots, key=lambda s: s["damage_position"]),
                           after["slots"]):
        if (s["units"], s["damage"], s["damage_position"]) != (
                expected["units"], expected["damage"], expected["position"]):
            raise AssertionError("public Round2 snapshot slot state is stale")
        if not (0 < s["hit_points_percent"] <= 100):
            raise AssertionError("Round2 live slot has no remaining HP")
    if not (0 < snap_wave["reserve_hit_points_percent"] <= 100):
        raise AssertionError("Round2 reserve has no remaining HP")

    return {
        "case_id": f"{domain}_{support_count}_support_{injury}_wounds",
        "evidence_class": PROVENANCE,
        "original_game_observation": False,
        "independent_game_holdout": False,
        "fired_round2_shots": False,
        "domain": domain, "round": 2, "support_count": support_count,
        "healing_capacity": capacity, "initial_wounds": injury, "outcome": outcome,
        "before": before, "after": after,
        "round2_snapshot": {"wave": snap_wave, "slots": snap_slots},
        "events": [e.as_dict() for e in events],
        "applied_assumption_ids": sorted(applied),
        "unknown_game_mechanics": [
            "Actual Gameforge partial Doctor/Tender allocation",
            "Healing versus RR sequence when insufficient",
            "Source hits and live battle chronology in game",
        ],
    }


def report():
    cases = [
        audit(domain, count, injury)
        for domain in ("land_doctor", "naval_tender")
        for count, injury in CASES
    ]
    return {
        "schema_version": 1,
        "classification": "SYNTHETIC_REAL_ENGINE_ROUND_START_STATE_ONLY",
        "summary": {
            "controlled_cases": len(cases), "game_observations": 0,
            "independent_holdouts": 0,
            "full_clear": sum(x["outcome"] == FULL for x in cases),
            "partial_unknown": sum(x["outcome"] == UNKNOWN for x in cases),
            "no_support": sum(x["outcome"] == NO_HEAL for x in cases),
        },
        "cases": cases,
    }


def csv_rows(data):
    return [
        {
            "case_id": c["case_id"], "evidence_class": c["evidence_class"],
            "domain": c["domain"], "support_count": c["support_count"],
            "capacity": c["healing_capacity"], "before_wounds": c["initial_wounds"],
            "after_wounds": c["after"]["total_wounds"], "outcome": c["outcome"],
            "before_reserve": c["before"]["reserve"],
            "after_reserve": c["after"]["reserve"],
            "after_reserve_wounds": c["after"]["reserve_damage"],
            "after_slot_wounds": json.dumps(
                [s["damage"] for s in c["after"]["slots"]]
            ),
            "historical_deaths": c["after"]["historical_dead"],
            "independent_game_holdout": False,
        } for c in data["cases"]
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    data = report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = csv_rows(data)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
