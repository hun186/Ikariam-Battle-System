"""Live two-round simulator HP / casualty audit with a pre-volley state witness.

All generated fleets and armies are SYNTHETIC controls, not Gameforge battles.
The live engine executes R1 and R2 firing; a narrowly scoped test hook records
its actual after-RR/pre-volley Wave/Slot state with no combat-model changes.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
from unittest.mock import patch

from ikariam_battle import simulate
from ikariam_battle import engine
from ikariam_battle.profiles import BattleEndProfile
from ikariam_battle.units import UnitRegistry

PROVENANCE = "SYNTHETIC_LIVE_SIMULATE_R1_R2_PREFIRE_POSTFIRE_NOT_GAME_OBSERVATION"
DOMAINS = ("land_doctor", "naval_tender")
SUPPORT_COUNTS = (0, 50)


def scenario(domain: str, supporters: int) -> dict:
    if type(supporters) is not int or supporters not in SUPPORT_COUNTS:
        raise ValueError("only the controlled supporter counts 0 and 50 are supported")
    if domain == "land_doctor":
        # 7x50 land-max First capacity: 750 Hoplites keep 400 in Reserve.
        # Smaller 410 initial Hoplites exhausted Reserve in R1 during first Hosted
        # validation, so could not witness a *nonempty* R2 pre-volley Reserve.
        defender = [
            {"unit_id": "hoplite", "quantity": 750},
            {"unit_id": "gyrocopter", "quantity": 3},
            {"unit_id": "swordsman", "quantity": 3},
        ]
        if supporters:
            defender.append({"unit_id": "doctor", "quantity": supporters})
        return {
            "policy": "experimental", "battlefield": "land-max", "max_rounds": 2,
            "attacker": {"units": [
                {"unit_id": "hoplite", "quantity": 350},
                {"unit_id": "gyrocopter", "quantity": 3},
                {"unit_id": "swordsman", "quantity": 3},
            ]},
            "defender": {"units": defender},
        }
    if domain == "naval_tender":
        # 6x6 naval-max Ram Flank capacity: 48 Rams keep 12 in Reserve.
        defender = [
            {"unit_id": "steam_ram", "quantity": 35},
            {"unit_id": "ram_ship", "quantity": 48,
             "attack_upgrade": 20, "armor_upgrade": 14},
        ]
        if supporters:
            defender.append({"unit_id": "tender", "quantity": supporters})
        return {
            "policy": "experimental", "battlefield": "naval-max", "max_rounds": 2,
            "attacker": {"army_kind": "barbarian", "forge_level": 0, "units": [
                {"unit_id": "barbarian_wedge_paddler", "quantity": 42},
                {"unit_id": "barbarian_deckwrecker", "quantity": 36},
            ]},
            "defender": {"army_kind": "player", "forge_level": 5, "units": defender},
        }
    raise ValueError("unknown controlled live battle domain")


def _wave_key(row: dict) -> tuple[str, str]:
    return row["unit_id"], row["wave_id"]


def _wave_map(state: dict) -> dict[tuple[str, str], dict]:
    return {_wave_key(row): row for row in state["waves"]}


def _wave_wounds(state: dict, key: tuple[str, str]) -> int:
    wave = _wave_map(state)[key]
    return wave["reserve_damage"] + sum(
        x["damage"] for x in state["slots"] if _wave_key(x) == key
    )


def _validate_snapshot(state: dict, registry: UnitRegistry, label: str):
    totals = defaultdict(int)
    reserves = defaultdict(int)
    slot_units = defaultdict(int)
    by_key = defaultdict(list)
    for slot in state["slots"]:
        key = _wave_key(slot)
        by_key[key].append(slot)
        unit = registry.get(slot["unit_id"])
        if (type(slot["units"]) is not int or slot["units"] < 0
                or slot["damage"] < 0
                or (slot["units"] and slot["damage"] >= slot["units"] * unit.hit_points)
                or not (0 <= slot["hit_points_percent"] <= 100)):
            raise AssertionError(f"{label}: illegal living slot HP or count {key}")
        if slot["units"] and slot["hit_points_percent"] <= 0:
            raise AssertionError(f"{label}: zero-HP survivors in {key}")
        slot_units[key] += slot["units"]
    for wave in state["waves"]:
        key = _wave_key(wave)
        if key in totals:
            raise AssertionError(f"{label}: duplicated Wave ID {key}")
        hp = registry.get(wave["unit_id"]).hit_points
        if (wave["reserve"] < 0 or wave["reserve_damage"] < 0
                or wave["reserve_damage"] >= wave["reserve"] * hp
                and wave["reserve"] > 0):
            raise AssertionError(f"{label}: illegal Reserve HP {key}")
        if wave["reserve"] == 0 and wave["reserve_damage"] != 0:
            raise AssertionError(f"{label}: empty Reserve owns persistent wounds {key}")
        # Support lives outside combat slots and Reserve; it does not fire.
        deployed_support = (wave["alive"] if registry.get(wave["unit_id"]).role == "support"
                            else 0)
        if wave["alive"] != wave["reserve"] + slot_units[key] + deployed_support:
            raise AssertionError(f"{label}: living Wave population not conserved {key}")
        totals[key] = wave["alive"]
        reserves[wave["unit_id"]] += wave["reserve"]
    if sum(totals.values()) != state["total"]:
        raise AssertionError(f"{label}: snapshot total differs from individual waves")
    for unit_id, alive in state["remaining"].items():
        if sum(n for (uid, _), n in totals.items() if uid == unit_id) != alive:
            raise AssertionError(f"{label}: remaining aggregate mismatch for {unit_id}")
    for unit_id, reserve in state["reserve"].items():
        if reserves[unit_id] != reserve:
            raise AssertionError(f"{label}: Reserve aggregate mismatch for {unit_id}")


def _validate_transition(previous: dict, current: dict, losses: dict,
                         label: str) -> dict:
    p, c = _wave_map(previous), _wave_map(current)
    if p.keys() != c.keys():
        raise AssertionError(f"{label}: Wave identity changed without arrivals")
    per_unit = defaultdict(int)
    per_wave = {}
    for key, row in p.items():
        lost = row["alive"] - c[key]["alive"]
        if lost < 0:
            raise AssertionError(f"{label}: spontaneous resurrection {key}")
        per_unit[key[0]] += lost
        per_wave[f"{key[0]}|{key[1]}"] = lost
    if {k: v for k, v in per_unit.items() if v} != {
            k: v for k, v in losses.items() if v}:
        raise AssertionError(f"{label}: round casualties disagree with live Wave delta")
    return per_wave


def live_audit(domain: str, supporters: int) -> dict:
    cfg = scenario(domain, supporters)
    captured: dict[tuple[int, str], dict] = {}
    real_build = engine._build_damage_queues
    battle_end = BattleEndProfile.load()
    registry = UnitRegistry.load(include_barbarians=True)

    def trace_pre_volley(waves, registry_arg, events, number, side, applied):
        # Exactly the real side Wave objects after deployment/healing/RR, just
        # before the engine builds its first per-individual fire queues.
        key = (number, side)
        if key in captured:
            raise AssertionError(f"duplicate pre-volley state {key}")
        captured[key] = deepcopy(engine._snapshot(waves, registry_arg, battle_end))
        return real_build(waves, registry_arg, events, number, side, applied)

    # Scope and automatic restoration matter: this research hook is NOT a
    # replacement for the engine or a production global runtime modification.
    with patch.object(engine, "_build_damage_queues", trace_pre_volley):
        result = simulate(cfg)
    if result["rounds_completed"] != 2 or len(result["rounds"]) != 3:
        raise AssertionError("two actual combat rounds were not completed")
    if set(captured) != {(1, "attacker"), (1, "defender"),
                         (2, "attacker"), (2, "defender")}:
        raise AssertionError("missing real pre-volley state at either round")
    for number in (1, 2):
        if not any(e["type"] == "damage" and e["round"] == number
                   for e in result["events"]):
            raise AssertionError(f"no live R{number} damage volley")

    transition = {}
    for side in ("attacker", "defender"):
        initial = result["rounds"][0][side]
        r1 = result["rounds"][1][side]
        r2 = result["rounds"][2][side]
        pre1, pre2 = captured[(1, side)], captured[(2, side)]
        for label, state in (
            ("r0", initial), ("r1prefire", pre1), ("r1end", r1),
            ("r2prefire", pre2), ("r2end", r2),
        ):
            _validate_snapshot(state, registry, f"{side}/{label}")
        if _wave_map(initial) != _wave_map(pre1):
            raise AssertionError("R1 pre-volley changed original living population")
        if _wave_map(r1).keys() != _wave_map(pre2).keys():
            raise AssertionError("R2 pre-volley lost Wave identity")
        for key, row in _wave_map(r1).items():
            if _wave_map(pre2)[key]["alive"] != row["alive"]:
                raise AssertionError(f"R2 prefire resurrected an R1 death: {key}")
        losses_1 = _validate_transition(
            pre1, r1, result["rounds"][1]["casualties"][side], f"{side}/r1")
        losses_2 = _validate_transition(
            pre2, r2, result["rounds"][2]["casualties"][side], f"{side}/r2")
        overall = defaultdict(int)
        for round_no in (1, 2):
            for uid, loss in result["rounds"][round_no]["casualties"][side].items():
                overall[uid] += loss
        if dict(overall) != result["casualties"][side]:
            raise AssertionError(f"{side}: global cumulative casualties incorrect")
        transition[side] = {
            "round_1_deaths_per_wave": losses_1,
            "round_2_deaths_per_wave": losses_2,
            "initial": initial, "round1_prefire": pre1, "round1_end": r1,
            "round2_prefire": pre2, "round2_end": r2,
        }

    support_type = "doctor" if domain == "land_doctor" else "tender"
    patient_type = "hoplite" if domain == "land_doctor" else "ram_ship"
    patient_key = (patient_type, "wave-1")
    previous_damage = _wave_wounds(transition["defender"]["round1_end"], patient_key)
    prefire_damage = _wave_wounds(transition["defender"]["round2_prefire"], patient_key)
    if previous_damage <= 0:
        raise AssertionError("controlled Round1 failed to wound surviving patient")
    if supporters:
        heals = [
            e for e in result["events"]
            if e["round"] == 2 and e["type"] == "healing"
            and e["side"] == "defender"
        ]
        if len(heals) != 1 or heals[0]["details"].get("support_unit_id") != support_type:
            raise AssertionError("full-support Round2 repair missing")
        detail = heals[0]["details"]
        if (detail.get("exact_subset") != "capacity_covers_all_eligible_persistent_damage"
                or detail.get("eligible_damage_before", 0) <= 0
                or detail.get("healing", 0) != detail.get("eligible_damage_before")
                or detail.get("capacity", 0) < detail["healing"]):
            raise AssertionError("Round2 full-clear event not internally consistent")
        if prefire_damage != 0:
            raise AssertionError("eligible patient retains HP wounds after full heal")
    elif previous_damage != prefire_damage:
        raise AssertionError("no support but patient HP wounds changed across round-start")

    slot_pre = [
        s for s in transition["defender"]["round2_prefire"]["slots"]
        if s["unit_id"] == patient_type
    ]
    reserve_pre = next(
        w for w in transition["defender"]["round2_prefire"]["waves"]
        if _wave_key(w) == patient_key
    )
    if not slot_pre or reserve_pre["reserve"] <= 0:
        raise AssertionError("Round2 lacks the reserved patient wave under study")
    fired = [
        e for e in result["events"]
        if e["round"] == 2 and e["side"] == "defender"
        and e["type"] == "damage"
        and e["details"].get("source_unit_id") == patient_type
    ]
    if not fired or sum(e["details"].get("firing_units", 0) for e in fired) <= 0:
        raise AssertionError("the wounded/refilled source did not actually fire in R2")

    return {
        "case_id": f"{domain}_support_{supporters}_live_two_rounds",
        "evidence_class": PROVENANCE,
        "game_observation": False,
        "independent_holdout": False,
        "actual_round2_firing": True,
        "domain": domain, "supporters": supporters,
        "patient": patient_type,
        "rounds_completed": result["rounds_completed"],
        "round1_patient_wounds": previous_damage,
        "round2_prefire_patient_wounds": prefire_damage,
        "round2_prefire_patient_reserve": reserve_pre["reserve"],
        "round2_patient_firing_event_count": len(fired),
        "patient_round2_firing_units": sum(e["details"].get("firing_units", 0) for e in fired),
        "global_casualties": result["casualties"],
        "witness": transition,
        "round2_support_events": [
            e for e in result["events"]
            if e["round"] == 2 and e["side"] == "defender"
            and e["type"] in ("healing", "healing_allocation_unresolved", "redistribution", "slot_repacked")
        ],
        "limitations": [
            "All armies invented: synthetic simulator outputs, no independent Gameforge holdout",
            "Round2 pre-volley witness collected using a scoped research-only function patch",
            "No official Accuracy/overkill/partial-healing/HP target allocator inferred",
        ],
    }


def report() -> dict:
    cases = [
        live_audit(domain, support)
        for domain in DOMAINS for support in SUPPORT_COUNTS
    ]
    return {
        "schema": "p0_live_two_round_prefire_postfire_ledger_v1",
        "classification": "CONTROLLED_ENGINE_EXECUTION_NOT_GAME_PROVENANCE",
        "summary": {
            "controlled_cases": len(cases), "actual_round2_engine_shot_cases": len(cases),
            "new_game_observations": 0, "independent_holdouts": 0,
            "with_full_support": sum(bool(x["supporters"]) for x in cases),
        },
        "cases": cases,
    }


def csv_rows(data: dict):
    return [{
        "case_id": c["case_id"], "evidence_class": c["evidence_class"],
        "domain": c["domain"], "supporters": c["supporters"],
        "patient": c["patient"],
        "round1_patient_wounds": c["round1_patient_wounds"],
        "round2_prefire_patient_wounds": c["round2_prefire_patient_wounds"],
        "round2_prefire_patient_reserve": c["round2_prefire_patient_reserve"],
        "round2_patient_firing_event_count": c["round2_patient_firing_event_count"],
        "patient_round2_firing_units": c["patient_round2_firing_units"],
        "actual_round2_firing": True, "new_game_observation": False,
        "independent_holdout": False,
    } for c in data["cases"]]


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
    with args.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
