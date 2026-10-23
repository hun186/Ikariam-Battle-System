"""P0 read-only round-boundary healing capacity and HP-state falsification matrix.

These seed invented persistent wounds directly into existing engine Wave/Slot
objects and invoke the real round-start pipeline. This does NOT reproduce
an actual Gameforge battle or determine unknown partial-healing allocation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from ikariam_battle.engine import _prepare_round_start, _snapshot
from ikariam_battle.models import ArmyUnit, Slot, Wave
from ikariam_battle.profiles import BattleEndProfile, SupportProfile
from ikariam_battle.units import UnitRegistry

PROVENANCE = "SYNTHETIC_SEEDED_ENGINE_ROUND2_BOUNDARY_NOT_GAME_OBSERVATION"
FULL = "current_engine_full_clear_order_invariant_subset"
PARTIAL_UNKNOWN = "current_engine_partial_unknown_no_heal_assumption"
NONE = "no_eligible_persistent_damage"
CASES = ((0, 1), (3999, 1), (4000, 1), (4001, 1), (4001, 2))


def _patient(unit_id: str, wave_id: str, line: str, units: int,
             capacity: int, injury: int, position: int) -> Wave:
    if type(injury) is not int or injury < 0:
        raise ValueError("seeded injury must be a nonnegative integer")
    return Wave(
        ArmyUnit(unit_id, units + 1, wave_id), 0,
        [Slot(f"{line}-{position}", line, position, position, unit_id,
              wave_id, units, capacity, injury)],
    )


def _seeded_waves(domain: str, injury: int, supporters: int) -> tuple[list[Wave], list[str]]:
    if type(injury) is not int or injury < 0:
        raise ValueError("seeded injury must be a nonnegative integer")
    if type(supporters) is not int or supporters <= 0:
        raise ValueError("supporters must be a positive integer")
    # Each eligible type has ONE prior casualty in its original 11/3 or 4/4
    # population, NO Reserve, and a living wound that can be repaired.
    # Eligible wounds are split over two DISTINCT combat state waves.
    a, b = min(2000, injury), max(0, injury - 2000)
    if domain == "land_doctor":
        if a > 10 * 360 or b > 2 * 1120:
            raise ValueError("seeded land wounds exceed surviving slot HP")
        waves = [
            _patient("swordsman", "swords-with-one-death", "flank", 10, 40, a, 1),
            _patient("hoplite", "hoplites-with-one-death", "first", 2, 30, b, 1),
            _patient("gyrocopter", "machines-with-one-death", "anti-balloon", 2, 2, 340, 1),
            Wave(ArmyUnit("doctor", supporters, "doctor-support"), 0, [], 0, None, supporters),
        ]
        return waves, ["swordsman", "hoplite"]
    if domain == "naval_tender":
        if a > 3 * 3080 or b > 3 * 2800:
            raise ValueError("seeded naval wounds exceed surviving slot HP")
        waves = [
            _patient("ram_ship", "rams-with-one-death", "flank", 3, 3, a, 1),
            _patient("balloon_carrier", "carriers-with-one-death", "balloon", 3, 3, b, 1),
            Wave(ArmyUnit("tender", supporters, "tender-support"), 0, [], 0, None, supporters),
        ]
        return waves, ["ram_ship", "balloon_carrier"]
    raise ValueError("unknown support domain")


def _wave_ledger(waves: list[Wave]) -> dict[str, dict[str, Any]]:
    rows = {}
    for wave in waves:
        if not wave.slots:
            continue
        if wave.unit.wave_id in rows:
            raise ValueError("duplicate wave identity in seeded controlled audit")
        rows[wave.unit.wave_id] = {
            "unit_id": wave.unit.unit_id,
            "historical_dead": wave.unit.quantity - wave.alive,
            "alive": wave.alive,
            "reserve": wave.reserve,
            "persistent_damage": wave.reserve_damage + sum(slot.damage for slot in wave.slots),
            "slots": [{
                "line": s.line, "damage_position": s.damage_position,
                "units": s.units, "damage": s.damage,
            } for s in wave.slots],
        }
    return rows


def probe(domain: str, injury: int, supporters: int) -> dict[str, Any]:
    registry = UnitRegistry.load(include_barbarians=True)
    support = SupportProfile.load()
    battle_end = BattleEndProfile.load()
    waves, eligible = _seeded_waves(domain, injury, supporters)
    before = _wave_ledger(waves)
    for key, v in before.items():
        if v["historical_dead"] != 1 or v["reserve"] != 0:
            raise ValueError(f"expected one historical death and no reserve in {key}")
    if sum(v["persistent_damage"] for v in before.values()
           if v["unit_id"] in eligible) != injury:
        raise ValueError("seeded eligible damage total did not reconcile")
    events, applied = [], {}
    blocked = _prepare_round_start(
        waves, events, 2, "defender", applied,
        registry=registry, support=support,
    )
    if blocked:
        raise ValueError("controlled full-clear round-start returned unsupported boundary")
    after = _wave_ledger(waves)
    if before.keys() != after.keys():
        raise ValueError("wave identities changed unexpectedly at controlled boundary")
    for key, prior in before.items():
        current = after[key]
        if (prior["alive"], prior["historical_dead"], prior["reserve"]) != (
                current["alive"], current["historical_dead"], current["reserve"]):
            raise ValueError(f"resurrection, loss or reserve refill at boundary: {key}")

    healing = [e for e in events if e.type == "healing"]
    unknown = [e for e in events if e.type == "healing_allocation_unresolved"]
    capacity = supporters * support.derived_capacity
    expected = NONE if injury == 0 else FULL if capacity >= injury else PARTIAL_UNKNOWN
    if expected == FULL:
        if len(healing) != 1 or unknown:
            raise ValueError("expected exactly one full-clear heal event")
        detail = healing[0].details
        if (detail.get("eligible_damage_before") != injury
                or detail.get("healing") != injury
                or detail.get("capacity") != capacity
                or detail.get("exact_subset") != "capacity_covers_all_eligible_persistent_damage"
                or detail.get("healing_rr_order") != "order_invariant_for_full_clear"
                or sum(detail.get("affected_units", {}).values()) != injury):
            raise ValueError("full-clear healing event cannot reconcile with HP ledger")
    elif expected == PARTIAL_UNKNOWN:
        rule = ("UNKNOWN-HEALING-ALLOCATION" if domain == "land_doctor"
                else "UNKNOWN-TENDER-HEALING-ALLOCATION")
        assumption = ("EXP-HEAL-NONE-001" if domain == "land_doctor"
                      else "EXP-TENDER-HEAL-NONE-001")
        if healing or len(unknown) != 1:
            raise ValueError("partial capacity must be unresolved, never healed")
        detail = unknown[0].details
        if (detail.get("rule_id") != rule
                or detail.get("action") != "no_partial_healing_applied"
                or detail.get("capacity") != capacity
                or detail.get("eligible_damage") != injury
                or detail.get("unresolved_damage") != injury
                or assumption not in applied):
            raise ValueError("partial allocation unknown ledger incomplete")
    elif healing or unknown:
        raise ValueError("no-eligible-damage case must not emit a heal event")

    for key, prior in before.items():
        current = after[key]
        expected_damage = (
            0 if prior["unit_id"] in eligible and expected == FULL
            else prior["persistent_damage"]
        )
        if current["persistent_damage"] != expected_damage:
            raise ValueError(f"real surviving HP changed unexpectedly at {key}")
    state = _snapshot(waves, registry, battle_end)
    snapshots = {x["wave_id"]: x for x in state["waves"]}
    for key in before:
        if snapshots[key]["alive"] != before[key]["alive"]:
            raise ValueError("round 2 snapshot did not preserve original surviving units")
    return {
        "case_id": f"{domain}_damage_{injury}_support_{supporters}",
        "evidence_class": PROVENANCE,
        "actual_game_battle_record": False,
        "game_healing_allocation_verified": False,
        "domain": domain,
        "round": 2,
        "supporters": supporters,
        "derived_capacity": capacity,
        "seeded_eligible_damage": injury,
        "execution": expected,
        "before": before,
        "after": after,
        "round2_snapshot": {
            "waves": [v for v in state["waves"] if v["wave_id"] in before],
            "slots": [v for v in state["slots"] if v["wave_id"] in before],
        },
        "events": [e.as_dict() for e in events],
        "applied_assumption_ids": sorted(applied),
        "limitations": [
            "Invented prior casualties and wounds, not Gameforge observations",
            "No attacks, ammo consumption, round-2 combat or reinforcement in seeded boundary",
            "Insufficient-capacity selection and healing-vs-RR order remain unknown",
        ],
    }


def build_report():
    cases = [probe(domain, injury, count)
             for domain in ("land_doctor", "naval_tender")
             for injury, count in CASES]
    return {
        "schema_version": 1,
        "report_id": "P0-DOCTOR-TENDER-HEALING-CAPACITY-BOUNDARY-20261023",
        "classification": "RESEARCH_ONLY_CURRENT_ENGINE_BOUNDED_SUBSET",
        "summary": {
            "synthetic_boundary_cases": len(cases),
            "game_observed_cases": 0,
            "independent_holdouts": 0,
            "full_clear": sum(x["execution"] == FULL for x in cases),
            "partial_allocation_unknown": sum(x["execution"] == PARTIAL_UNKNOWN for x in cases),
            "zero_eligible_damage": sum(x["execution"] == NONE for x in cases),
        },
        "cases": cases,
    }


def csv_rows(report):
    return [{
        "case_id": c["case_id"],
        "evidence_class": c["evidence_class"],
        "domain": c["domain"],
        "supporters": c["supporters"],
        "capacity": c["derived_capacity"],
        "seeded_eligible_damage": c["seeded_eligible_damage"],
        "execution": c["execution"],
        "before_hp_by_wave": json.dumps({k: v["persistent_damage"] for k,v in c["before"].items()}, sort_keys=True),
        "after_hp_by_wave": json.dumps({k: v["persistent_damage"] for k,v in c["after"].items()}, sort_keys=True),
        "original_deaths_protected": all(v["historical_dead"] == 1 for v in c["after"].values()),
        "independent_holdout": False,
    } for c in report["cases"]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-json", type=Path, required=True)
    p.add_argument("--output-csv", type=Path, required=True)
    args = p.parse_args()
    report = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = csv_rows(report)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
