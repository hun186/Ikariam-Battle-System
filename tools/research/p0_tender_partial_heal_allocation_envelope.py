"""P0 read-only counterfactual Tender partial-heal allocation envelope.

Runs the existing REAL synthetic R1/R2 simulator through the merged PR #83
witness. Only its actual R1-end survivor wounds and actual R2 pre-volley
deployment feed *hypothetical* allocation policies. The current engine applies
zero partial repair as an explicit UNKNOWN fallback. We never patch healing,
claim Gameforge allocation/chronology, or execute hypothetical R2 combat.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import csv
import json
from pathlib import Path

from ikariam_battle.profiles import SupportProfile
from ikariam_battle.redistribution import SlotShare, reserve_redistribution
from ikariam_battle.units import UnitRegistry
from tools.research.p0_live_insufficient_support_round2 import (
    INSUFFICIENT, PROVENANCE as LIVE_PROVENANCE, live_case,
)
from tools.research.p0_live_round2_prefire_postfire_ledger import (
    _wave_key, _wave_map, _wave_wounds,
)

PROVENANCE = "COUNTERFACTUAL_WAVE_ALLOCATION_FROM_SYNTHETIC_R1_NOT_GAME_OBSERVATION"
POLICIES = (
    "current_model_no_partial_applied",
    "hypothetical_ram_ship_first",
    "hypothetical_steam_ram_first",
    "hypothetical_proportional_largest_remainder",
)
PENDING = "UNKNOWN-TENDER-HEALING-ALLOCATION"


def source() -> dict:
    """Only the already source-tagged, actual R1/R2 Tender=1 audit."""
    c = live_case("naval_tender", 1)
    track = c["transitions"]["defender"]
    boundary = track["boundary"]
    if (c["provenance"] != LIVE_PROVENANCE or c["game_observations"] != 0
            or c["independent_holdouts"] != 0
            or boundary["outcome"] != INSUFFICIENT
            or boundary["capacity"] != SupportProfile.load().derived_capacity
            or c["supporters"] != 1 or not c["round2_real_patient_firing"]):
        raise AssertionError("source evidence no longer describes the guarded Tender=1 R1/R2 case")
    unknown = [e for e in boundary["support_events"]
               if e["type"] == "healing_allocation_unresolved"]
    if (len(unknown) != 1
            or unknown[0]["details"].get("rule_id") != PENDING
            or unknown[0]["details"].get("action") != "no_partial_healing_applied"):
        raise AssertionError("the real simulator's under-capacity unknown has disappeared")
    return c


def _integer(v, name: str) -> int:
    if type(v) is not int or v < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return v


def wounded_eligible_waves(c: dict) -> tuple[list[dict], int]:
    """Derive independent wave injuries from snapshots, not event claims."""
    track = c["transitions"]["defender"]
    before, pre = track["after_r1"], track["before_r2"]
    if _wave_map(before).keys() != _wave_map(pre).keys():
        raise AssertionError("R1/R2 wave identities differ")
    registry = UnitRegistry.load(include_barbarians=True)
    boundary = track["boundary"]
    if boundary["outcome"] != INSUFFICIENT:
        raise AssertionError("source is not an unresolved partial Tender case")
    rows = []
    for entry in boundary["waves"]:
        key = _wave_key(entry)
        if key not in _wave_map(before) or key not in _wave_map(pre):
            raise AssertionError("unknown witness wave")
        actual_r1 = _wave_wounds(before, key)
        actual_r2 = _wave_wounds(pre, key)
        if (actual_r1 != _integer(entry["wounds_r1_end"], "R1 wound")
                or actual_r2 != _integer(entry["wounds_r2_prefire"], "R2 wound")
                or actual_r1 != actual_r2):
            raise AssertionError("real R1/R2 no-partial HP witness is not conserved")
        uid, wave_id = key
        unit = registry.get(uid)
        eligible = unit.role == "combat" and unit.domain == "naval"
        if eligible != entry["eligible"]:
            raise AssertionError("research healing eligibility diverges from registry")
        if _wave_map(before)[key]["alive"] != _wave_map(pre)[key]["alive"]:
            raise AssertionError("previous casualty resurrected across Round boundary")
        row = {
            "unit_id": uid, "wave_id": wave_id,
            "eligible": eligible,
            "wounds_r1_end": actual_r1,
            "model_wounds_r2_prefire": actual_r2,
            "alive": _wave_map(pre)[key]["alive"],
        }
        rows.append(row)
    eligible_wounds = sum(x["wounds_r1_end"] for x in rows if x["eligible"])
    if (eligible_wounds != boundary["eligible_wounds_at_r1_end"]
            or eligible_wounds <= boundary["capacity"]):
        raise AssertionError("eligible wound sum/capacity boundary did not reconcile")
    return rows, boundary["capacity"]


def allocations(rows: list[dict], capacity: int) -> dict[str, dict[tuple[str, str], int]]:
    """Entirely conditional wave-level allocation, all integer HP and bounded."""
    cap = _integer(capacity, "capacity")
    keys = [(x["unit_id"], x["wave_id"]) for x in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate wound-wave identity")
    wounds = {}
    for row, key in zip(rows, keys):
        n = _integer(row["wounds_r1_end"], "wound")
        wounds[key] = n if row["eligible"] else 0
    if not 0 < cap < sum(wounds.values()):
        raise ValueError("only insufficient positive-capacity witnesses are supported")

    baseline = {key: 0 for key in keys}

    def first(preferred: str) -> dict[tuple[str, str], int]:
        remain = cap
        result = baseline.copy()
        for key in sorted(keys, key=lambda k: (k[0] != preferred, k)):
            grant = min(remain, wounds[key])
            result[key] = grant
            remain -= grant
        if remain:
            raise AssertionError("priority allocator failed to exhaust its hypothetical budget")
        return result

    exact = {key: Fraction(cap * n, sum(wounds.values())) for key, n in wounds.items()}
    proportional = {key: int(v) for key, v in exact.items()}
    leftover = cap - sum(proportional.values())
    ranked = sorted(keys, key=lambda k: (-(exact[k] - int(exact[k])), k))
    for key in ranked:
        if not leftover:
            break
        if proportional[key] < wounds[key]:
            proportional[key] += 1
            leftover -= 1
    if leftover:
        raise AssertionError("proportional allocator lost integer capacity")
    options = dict(zip(POLICIES, [
        baseline, first("ram_ship"), first("steam_ram"), proportional,
    ]))
    for policy, grant in options.items():
        total = sum(grant.values())
        if total != (0 if policy == POLICIES[0] else cap):
            raise AssertionError("counterfactual healing budget not conserved")
        if any(not 0 <= grant[key] <= wounds[key] for key in keys):
            raise AssertionError("counterfactual repaired ineligible or unwounded wave")
    return options


def _rr_counterfactual(state: dict, row: dict, grant: int,
                        registry: UnitRegistry) -> dict:
    """Predict R2 HP *given* same deployment and existing Experimental RR.

    This is NOT live engine execution with a partial-heal hypothesis, and
    doesn't identify heal-before/after-RR or Gameforge individual allocation.
    """
    uid, wave_id = row["unit_id"], row["wave_id"]
    key = uid, wave_id
    wave = _wave_map(state)[key]
    hp = registry.get(uid).hit_points
    alive = wave["alive"]
    if type(hp) is not int or hp <= 0 or type(alive) is not int or alive <= 0:
        raise AssertionError("counterfactual requires living identified positive-HP wave")
    _integer(grant, "healing")
    remaining = _integer(row["wounds_r1_end"], "original wounds") - grant
    if remaining < 0 or remaining >= alive * hp:
        raise AssertionError("hypothetical surviving wave HP invalid")

    slots = sorted((s for s in state["slots"] if _wave_key(s) == key),
                   key=lambda s: s["damage_position"])
    positions = [s["damage_position"] for s in slots]
    if len(positions) != len(set(positions)):
        raise AssertionError("ambiguous damage-position RR destination")
    deployed = [
        SlotShare(s["damage_position"], s["units"])
        for s in slots if s["units"] > 0
    ]
    assigned, reserve = reserve_redistribution(remaining, alive, deployed)
    if wave["reserve"] + sum(s["units"] for s in slots) != alive:
        raise AssertionError("fake survivor deployed or Reserve population")
    if sum(assigned.values()) + reserve != remaining:
        raise AssertionError("hypothetical RR wounds not conserved")
    result_slots = []
    for slot in slots:
        current = assigned.get(slot["damage_position"], 0)
        if not 0 <= current < max(1, slot["units"] * hp):
            raise AssertionError("hypothetical Slot HP would be invalid")
        if slot["units"] == 0 and current:
            raise AssertionError("cannot injure empty Slot")
        cap = slot["units"] * hp
        result_slots.append({
            "slot_id": slot["slot_id"], "damage_position": slot["damage_position"],
            "units": slot["units"], "remaining_wounds": current,
            "percent_current_model_format": (
                round(100 * (cap - current) / cap, 2) if cap else 0
            ),
            "original_model_wounds": slot["damage"],
            "original_model_hp_bar": slot["hit_points_percent"],
        })
    if (reserve < 0 or
            (wave["reserve"] == 0 and reserve != 0) or
            (wave["reserve"] > 0 and reserve >= wave["reserve"] * hp)):
        raise AssertionError("invalid hypothetical reserve HP")
    return {
        "unit_id": uid, "wave_id": wave_id, "eligible": row["eligible"],
        "alive": alive, "original_wounds_r1": row["wounds_r1_end"],
        "hypothetical_healed_hp": grant,
        "hypothetical_remaining_wounds": remaining,
        "model_original_prefire_wounds": row["model_wounds_r2_prefire"],
        "slots": result_slots,
        "reserve": wave["reserve"], "reserve_wounds": reserve,
        "original_model_reserve_wounds": wave["reserve_damage"],
        "rr_method": "current_experimental_reserve_redistribution_on_unchanged_R2_deployment",
    }


def build_report() -> dict:
    case = source()
    rows, cap = wounded_eligible_waves(case)
    policies = allocations(rows, cap)
    state = case["transitions"]["defender"]["before_r2"]
    registry = UnitRegistry.load(include_barbarians=True)
    scenarios = []
    for name in POLICIES:
        by_wave = [_rr_counterfactual(state, row, policies[name][
            (row["unit_id"], row["wave_id"])], registry) for row in rows if row["alive"]]
        for row in by_wave:
            if name == POLICIES[0]:
                if (row["hypothetical_remaining_wounds"] !=
                        row["model_original_prefire_wounds"] or
                        row["reserve_wounds"] != row["original_model_reserve_wounds"] or
                        any(s["remaining_wounds"] != s["original_model_wounds"]
                            for s in row["slots"])):
                    raise AssertionError("replayed zero-partial RR disagrees with REAL simulator baseline")
        healed = sum(x["hypothetical_healed_hp"] for x in by_wave)
        scenarios.append({
            "policy": name,
            "provenance": (
                LIVE_PROVENANCE if name == POLICIES[0] else PROVENANCE
            ),
            "actual_engine_partial_healing_executed": False,
            "hypothetical_hp_budget_used": healed,
            "game_mechanic_verified": False,
            "waves": by_wave,
        })
    return {
        "schema": "p0_tender_partial_heal_allocation_rr_envelope_v1",
        "classification": "COUNTERFACTUAL_NOT_NEW_GAME_EVIDENCE",
        "source": {
            "case_id": case["case_id"], "provenance": case["provenance"],
            "evidence_class": LIVE_PROVENANCE, "side": "defender",
            "supporters": 1, "capacity_hp": cap,
            "r1_eligible_wounds": case["transitions"]["defender"]["boundary"]["eligible_wounds_at_r1_end"],
            "actual_model_unknown_rule": PENDING,
            "actual_model_partial_hp_applied": 0,
            "actual_R2_firing_witness": True,
        },
        "summary": {
            "model_comparison_scenarios": len(scenarios),
            "conditional_full_budget_policies": len(scenarios) - 1,
            "new_game_observations": 0,
            "independent_holdouts": 0,
            "official_partial_healing_verified": False,
        },
        "scenarios": scenarios,
        "limitations": [
            "The source run is real simulator execution on an INVENTED naval fleet, never actual Gameforge shots.",
            "Only zero-applied-partial ran through actual Round2 combat; all other R2 HP states are math projections without simulated R2 shots.",
            "Whole-wave heal allocation and applying current Experimental RR to same next-round deployment are unverified hypotheses, not Gameforge individual healing or chronology.",
            "The 4000 HP budget is model profile-derived capacity; actual Gameforge usage when insufficient is UNKNOWN.",
        ],
    }


def csv_rows(report: dict) -> list[dict]:
    out = []
    for scenario in report["scenarios"]:
        for wave in scenario["waves"]:
            out.append({
                "case_id": report["source"]["case_id"],
                "source_provenance": report["source"]["provenance"],
                "policy": scenario["policy"],
                "scenario_provenance": scenario["provenance"],
                "game_mechanic_verified": False,
                "actual_engine_partial_healing_executed": False,
                "supporter_count": report["source"]["supporters"],
                "capacity_hp": report["source"]["capacity_hp"],
                "unit_id": wave["unit_id"], "wave_id": wave["wave_id"],
                "alive": wave["alive"],
                "original_r1_wounds": wave["original_wounds_r1"],
                "hypothetical_healed_hp": wave["hypothetical_healed_hp"],
                "hypothetical_remaining_wounds": wave["hypothetical_remaining_wounds"],
                "reserve_wounds": wave["reserve_wounds"],
                "model_original_reserve_wounds": wave["original_model_reserve_wounds"],
                "rr_assumption": wave["rr_method"],
                "slot_hp_json": json.dumps(wave["slots"], sort_keys=True),
                "new_game_observations": 0, "independent_holdouts": 0,
            })
    if len({(x["policy"], x["unit_id"], x["wave_id"]) for x in out}) != len(out):
        raise AssertionError("ambiguous policy-specific wave evidence identity")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-json", required=True, type=Path)
    p.add_argument("--output-csv", required=True, type=Path)
    args = p.parse_args()
    report = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = csv_rows(report)
    with args.output_csv.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
