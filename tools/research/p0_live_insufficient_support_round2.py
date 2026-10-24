"""Research-only actual R1/R2 firing with insufficient Doctor/Tender capacity.

All 0/1/50-support armies are invented synthetic controls. One supporter with
insufficient capacity does NOT imply Gameforge healed nobody; the Experimental
simulator intentionally leaves the unknown partial allocation unapplied. This
tool verifies that honest boundary through real Round2 attacks and HP ledgers.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
from unittest.mock import patch

from ikariam_battle import engine, simulate
from ikariam_battle.profiles import BattleEndProfile, SupportProfile
from ikariam_battle.units import UnitRegistry
from tools.research.p0_live_round2_prefire_postfire_ledger import (
    DOMAINS, _validate_snapshot, _validate_transition, _wave_map,
    _wave_wounds, scenario,
)

SUPPORT_COUNTS = (0, 1, 50)
PROVENANCE = "SYNTHETIC_REAL_SIMULATE_R1_R2_PARTIAL_HEAL_UNKNOWN_NOT_GAME_OBSERVATION"
NO_SUPPORT = "no_support"
INSUFFICIENT = "insufficient_capacity_game_allocation_unknown_model_applies_no_partial"
FULL = "full_clear_current_supported_subset"


def _setting(domain: str, supporters: int) -> tuple[dict, str, str]:
    if domain not in DOMAINS or type(supporters) is not int or supporters not in SUPPORT_COUNTS:
        raise ValueError("only designated synthetic Land/Naval 0/1/50 support configurations")
    cfg = scenario(domain, 0)
    support_unit = "doctor" if domain == "land_doctor" else "tender"
    patient = "hoplite" if domain == "land_doctor" else "ram_ship"
    if supporters:
        cfg["defender"]["units"].append({
            "unit_id": support_unit, "quantity": supporters,
        })
    return cfg, support_unit, patient


def _eligible(unit, domain: str) -> bool:
    return unit.role == "combat" and (
        (domain == "land_doctor" and unit.unit_class == "human")
        or (domain == "naval_tender" and unit.domain == "naval")
    )


def reconcile_round_boundary(previous: dict, prefire: dict, *,
                             domain: str, side: str, supporters: int,
                             capacity_per_supporter: int,
                             events: list[dict], registry: UnitRegistry) -> dict:
    """Independently compute eligible R1 wounds before trusting heal events."""
    if side not in ("attacker", "defender"):
        raise ValueError("invalid combat side")
    if type(supporters) is not int or supporters < 0:
        raise ValueError("support count not valid")
    before, after = _wave_map(previous), _wave_map(prefire)
    if before.keys() != after.keys():
        raise AssertionError("R1/R2 Wave identities changed at round boundary")
    for key in before:
        if before[key]["alive"] != after[key]["alive"]:
            raise AssertionError(f"round boundary illegally added/removed living units {key}")

    candidates = []
    for key in sorted(before):
        uid, wave_id = key
        unit = registry.get(uid)
        wounded = _wave_wounds(previous, key)
        if wounded < 0:
            raise AssertionError("negative pre-existing Wave wound")
        candidates.append({
            "unit_id": uid, "wave_id": wave_id,
            "eligible": _eligible(unit, domain),
            "wounds_r1_end": wounded,
            "wounds_r2_prefire": _wave_wounds(prefire, key),
            "alive_r1_end": before[key]["alive"],
            "alive_r2_prefire": after[key]["alive"],
        })
    eligible_before = sum(
        x["wounds_r1_end"] for x in candidates if x["eligible"]
    )
    capacity = supporters * capacity_per_supporter
    if side == "attacker" or not supporters:
        expected = NO_SUPPORT
    elif eligible_before > capacity:
        expected = INSUFFICIENT
    else:
        expected = FULL
    for row in candidates:
        anticipated = (
            0 if expected == FULL and row["eligible"]
            else row["wounds_r1_end"]
        )
        if row["wounds_r2_prefire"] != anticipated:
            raise AssertionError(
                f"{side} Round2 wound drift {row['unit_id']}/{row['wave_id']}: "
                f"expected {anticipated}, got {row['wounds_r2_prefire']}"
            )

    relevant = [e for e in events
                if e["round"] == 2 and e["side"] == side]
    healed = [e for e in relevant if e["type"] == "healing"]
    unresolved = [e for e in relevant
                  if e["type"] == "healing_allocation_unresolved"]
    if expected == INSUFFICIENT:
        rule = ("UNKNOWN-HEALING-ALLOCATION" if domain == "land_doctor"
                else "UNKNOWN-TENDER-HEALING-ALLOCATION")
        if healed or len(unresolved) != 1:
            raise AssertionError("unknown partial heal was turned into completed repair")
        detail = unresolved[0]["details"]
        if (detail.get("rule_id") != rule
                or detail.get("action") != "no_partial_healing_applied"
                or detail.get("eligible_damage") != eligible_before
                or detail.get("unresolved_damage") != eligible_before
                or detail.get("capacity") != capacity):
            raise AssertionError("insufficient healing warning mismatches actual wounds")
        assumptions = [e["details"].get("id") for e in relevant
                       if e["type"] == "assumption_applied"]
        expected_assumption = ("EXP-HEAL-NONE-001" if domain == "land_doctor"
                               else "EXP-TENDER-HEAL-NONE-001")
        if expected_assumption not in assumptions:
            raise AssertionError("named unverified no-partial-heal assumption missing")
    elif expected == FULL and eligible_before > 0:
        if unresolved or len(healed) != 1:
            raise AssertionError("full heal must be explicitly recorded")
        detail = healed[0]["details"]
        expected_waves = sorted(
            ({"unit_id": row["unit_id"], "wave_id": row["wave_id"],
              "healing": row["wounds_r1_end"]}
             for row in candidates if row["eligible"] and row["wounds_r1_end"]),
            key=lambda x: (x["unit_id"], x["wave_id"]),
        )
        if (detail.get("capacity") != capacity
                or detail.get("eligible_damage_before") != eligible_before
                or detail.get("healing") != eligible_before
                or detail.get("affected_waves") != expected_waves
                or detail.get("exact_subset") != "capacity_covers_all_eligible_persistent_damage"):
            raise AssertionError("full-clear event disagrees with independent Wave wounds")
    elif healed or unresolved:
        raise AssertionError("non-healing boundary emitted an invented healing event")
    return {
        "side": side, "outcome": expected, "capacity": capacity,
        "eligible_wounds_at_r1_end": eligible_before,
        "actual_applied_heal_hp": (
            eligible_before if expected == FULL else 0
        ),
        "game_partial_allocation_verified": False,
        "waves": candidates,
        "support_events": [deepcopy(e) for e in relevant if e["type"] in (
            "healing", "healing_allocation_unresolved", "redistribution",
            "assumption_applied",
        )],
    }


def live_case(domain: str, supporters: int) -> dict:
    cfg, support_unit, patient = _setting(domain, supporters)
    registry = UnitRegistry.load(include_barbarians=True)
    support = SupportProfile.load()
    battle_end = BattleEndProfile.load()
    captured = {}
    real = engine._build_damage_queues

    def before_fire(waves, registry_arg, events, number, side, applied):
        key = number, side
        if key in captured:
            raise AssertionError(f"duplicate pre-volley snapshot {key}")
        captured[key] = deepcopy(engine._snapshot(waves, registry_arg, battle_end))
        return real(waves, registry_arg, events, number, side, applied)

    with patch.object(engine, "_build_damage_queues", before_fire):
        actual = simulate(cfg)
    if (actual["rounds_completed"] != 2
            or set(captured) != {(1, "attacker"), (1, "defender"),
                                 (2, "attacker"), (2, "defender")}):
        raise AssertionError("synthetic two-round fighting did not execute fully")
    transitions = {}
    for side in ("attacker", "defender"):
        r0, r1, r2 = (actual["rounds"][n][side] for n in (0, 1, 2))
        p1, p2 = captured[(1, side)], captured[(2, side)]
        for label, state in (("r0", r0), ("r1_start", p1), ("r1_end", r1),
                             ("r2_start", p2), ("r2_end", r2)):
            _validate_snapshot(state, registry, f"{domain}/{supporters}/{side}/{label}")
        r1_deaths = _validate_transition(
            p1, r1, actual["rounds"][1]["casualties"][side], f"{side}/R1"
        )
        r2_deaths = _validate_transition(
            p2, r2, actual["rounds"][2]["casualties"][side], f"{side}/R2"
        )
        boundary = reconcile_round_boundary(
            r1, p2, domain=domain, side=side,
            supporters=supporters if side == "defender" else 0,
            capacity_per_supporter=support.derived_capacity,
            events=actual["events"], registry=registry,
        )
        transitions[side] = {
            "before_r1": p1, "after_r1": r1, "before_r2": p2,
            "after_r2": r2, "r1_deaths_per_wave": r1_deaths,
            "r2_deaths_per_wave": r2_deaths, "boundary": boundary,
        }
    source_shots = [e for e in actual["events"]
                    if e["round"] == 2 and e["side"] == "defender"
                    and e["type"] == "damage"
                    and e["details"].get("source_unit_id") == patient]
    if not source_shots or not sum(e["details"].get("firing_units", 0)
                                   for e in source_shots):
        raise AssertionError("wounded/refilled defender patient did not fire in actual R2")
    # R1 wounds determine who is eligible for R2 healing. Never accept a
    # surviving R2 trace as a substitute for missing R1 firing provenance.
    # Check each round independently rather than using an existential check
    # over both rounds, which can pass with R1 stripped entirely.
    for number in (1, 2):
        if not any(e["round"] == number and e["type"] == "damage"
                   for e in actual["events"]):
            raise AssertionError(f"missing actual R{number} damage events")
    defender = transitions["defender"]
    patient_key = patient, "wave-1"
    wound1 = _wave_wounds(defender["after_r1"], patient_key)
    wound2 = _wave_wounds(defender["before_r2"], patient_key)
    if wound1 <= 0:
        raise AssertionError("the controlled combat failed to leave any wounded patient")
    # Construct the expected unit-ID set exclusively from independently
    # validated R1/R2 per-round casualty ledgers. Iterating keys from the
    # *global* field would make a deleted global casualty entry invisible.
    all_deaths = {}
    for side in ("attacker", "defender"):
        total = defaultdict(int)
        for round_no in (1, 2):
            for unit_id, lost in actual["rounds"][round_no]["casualties"][side].items():
                if type(lost) is not int or lost < 0:
                    raise AssertionError("invalid round casualty count")
                total[unit_id] += lost
        expected = {uid: lost for uid, lost in total.items() if lost > 0}
        reported = actual["casualties"][side]
        if (not isinstance(reported, dict)
                or any(type(lost) is not int or lost < 0
                       for lost in reported.values())
                or {uid: lost for uid, lost in reported.items() if lost > 0}
                != expected):
            raise AssertionError(
                f"{side}: global casualty tally does not reconcile to independently "
                "validated R1 and R2 unit deaths"
            )
        all_deaths[side] = expected
    return {
        "case_id": f"{domain}_support_{supporters}_live_R1_R2",
        "provenance": PROVENANCE, "domain": domain,
        "supporters": supporters, "support_unit_id": support_unit,
        "support_capacity_hp": supporters * support.derived_capacity,
        "game_observations": 0, "independent_holdouts": 0,
        "rounds_completed": 2, "round2_real_patient_firing": True,
        "round2_patient_grouped_damage_events": deepcopy(source_shots),
        "round1_patient_wounds": wound1,
        "round2_prefire_patient_wounds": wound2,
        "round2_defender_casualties": actual["rounds"][2]["casualties"]["defender"],
        "global_casualties": actual["casualties"],
        "transitions": transitions,
        "warning": (
            "Insufficient support leaves wounds unchanged ONLY as an explicit "
            "Experimental no-partial-allocation fallback. This is NOT a verified "
            "Gameforge no-heal rule or proof of heal-versus-RR chronology."
        ),
    }


def report() -> dict:
    cases = [live_case(d, n) for d in DOMAINS for n in SUPPORT_COUNTS]
    grouped = {(c["domain"], c["supporters"]): c for c in cases}
    for domain in DOMAINS:
        zero, one, fifty = (grouped[(domain, n)] for n in SUPPORT_COUNTS)
        # Support is not a first-round weapon. R1 combat inputs differ only
        # by non-firing support, so observed synthetic combat victims & wounds
        # must be identical until the first support round boundary.
        for variant in (one, fifty):
            for side in ("attacker", "defender"):
                lhs = zero["transitions"][side]["after_r1"]
                rhs = variant["transitions"][side]["after_r1"]
                for key in _wave_map(lhs):
                    if key[0] in ("doctor", "tender"):
                        continue
                    if key not in _wave_map(rhs):
                        raise AssertionError("support count changed combat Wave IDs")
                    if (_wave_wounds(lhs, key) != _wave_wounds(rhs, key)
                            or _wave_map(lhs)[key]["alive"] != _wave_map(rhs)[key]["alive"]):
                        raise AssertionError("support altered pre-heal R1 combat results")
        # If one support unit is insufficient, the fallback should expose
        # identical actual R2 prefire combat wounds to no-support, not
        # surreptitiously partially heal a surviving fleet.
        if one["transitions"]["defender"]["boundary"]["outcome"] == INSUFFICIENT:
            z = zero["transitions"]["defender"]["boundary"]["waves"]
            o = one["transitions"]["defender"]["boundary"]["waves"]
            za = {(x["unit_id"], x["wave_id"]): x for x in z}
            for row in o:
                key = row["unit_id"], row["wave_id"]
                if key in za and row["wounds_r2_prefire"] != za[key]["wounds_r2_prefire"]:
                    raise AssertionError("unknown partial-capacity fallback changed R2 wounds")
    return {
        "schema": "p0_live_insufficient_support_real_R2_v1",
        "classification": PROVENANCE,
        "summary": {
            "synthetic_cases": len(cases),
            "with_R2_firing": len(cases),
            "insufficient_support_cases": sum(
                x["transitions"]["defender"]["boundary"]["outcome"] == INSUFFICIENT
                for x in cases
            ),
            "full_clear_cases": sum(
                x["transitions"]["defender"]["boundary"]["outcome"] == FULL
                for x in cases
            ),
            "new_game_observations": 0, "independent_game_holdouts": 0,
        },
        "cases": cases,
    }


def csv_rows(data: dict) -> list[dict]:
    rows = []
    for c in data["cases"]:
        boundary = c["transitions"]["defender"]["boundary"]
        rows.append({
            "case_id": c["case_id"], "provenance": PROVENANCE,
            "domain": c["domain"], "supporters": c["supporters"],
            "support_capacity_hp": c["support_capacity_hp"],
            "r1_eligible_wounds": boundary["eligible_wounds_at_r1_end"],
            "r2_healing_status": boundary["outcome"],
            "model_applied_healing_hp": boundary["actual_applied_heal_hp"],
            "game_partial_allocation_verified": False,
            "r1_patient_wounds": c["round1_patient_wounds"],
            "r2_prefire_patient_wounds": c["round2_prefire_patient_wounds"],
            "r2_patient_grouped_shots_json": json.dumps(
                c["round2_patient_grouped_damage_events"], sort_keys=True
            ),
            "per_wave_round_boundary_json": json.dumps(
                boundary["waves"], sort_keys=True
            ),
            "support_event_evidence_json": json.dumps(
                boundary["support_events"], sort_keys=True
            ),
            "new_game_observations": 0, "independent_game_holdouts": 0,
        })
    if len({x["case_id"] for x in rows}) != len(rows):
        raise AssertionError("duplicate scenario identity in exported evidence")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    args = parser.parse_args()
    data = report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = csv_rows(data)
    with args.output_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
