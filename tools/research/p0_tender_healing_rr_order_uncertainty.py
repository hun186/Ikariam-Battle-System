"""P0 Tender healing/RR ordering and allocation-location uncertainty, *math only*.

Only the PR #83/84 simulator's *synthetic* R1/R2 Tender=1 source runs through
actual combat. These branches do NOT execute hypothetical Round2 attacks,
infer official Gameforge order, or mutate the production engine. Comparing
heal-before-RR with RR-then-slot/reserve-priority changes BOTH order and
localization; it cannot isolate the official chronology.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import json
from pathlib import Path

from ikariam_battle.units import UnitRegistry
from tools.research import p0_tender_partial_heal_allocation_envelope as prior

PROVENANCE = "SYNTHETIC_R1_MATH_COUNTERFACTUAL_HEAL_RR_ORDER_AND_LOCATION_UNVERIFIED"
ORDERS = (
    "hypothetical_wave_heal_before_experimental_rr",
    "hypothetical_experimental_rr_then_center_slot_first_heal",
    "hypothetical_experimental_rr_then_reserve_first_heal",
)
PRIORITIES = prior.POLICIES[1:]


def _nonnegative(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _baseline(state: dict, row: dict, registry: UnitRegistry) -> dict:
    """An independent exact no-partial-RR replay of actual model R2 prefire."""
    base = prior._rr_counterfactual(state, row, 0, registry)
    if (base["hypothetical_remaining_wounds"] != base["model_original_prefire_wounds"]
            or base["reserve_wounds"] != base["original_model_reserve_wounds"]
            or any(s["remaining_wounds"] != s["original_model_wounds"]
                   for s in base["slots"])):
        raise AssertionError("original live R2 prefire HP disagrees with RR baseline")
    return base


def _slot_bar(wounds: int, population: int, hp: int) -> float:
    if population <= 0 or hp <= 0 or not 0 <= wounds < population * hp:
        raise AssertionError("projected Slot has illegal wounded survivor HP")
    return round(100 * (population * hp - wounds) / (population * hp), 2)


def rr_then_local_heal(state: dict, row: dict, grant: int,
                       registry: UnitRegistry, *, reserve_first: bool) -> dict:
    """Apply per-Wave grant to already RR-distributed wounds, in fixed order.

    These center-slot-first vs Reserve-first integer priorities are invented
    *localization hypotheses*, not observed wounded individuals or the game UI.
    """
    if type(reserve_first) is not bool:
        raise ValueError("reserve_first flag must be bool")
    original = _baseline(state, row, registry)
    total = _nonnegative(row["wounds_r1_end"], "R1 persistent injuries")
    healed = _nonnegative(grant, "hypothetical healing")
    if healed > total or (not row["eligible"] and healed):
        raise ValueError("hypothetical healing exceeds eligible survivor wounds")
    result = deepcopy(original)
    uid = row["unit_id"]
    hp = registry.get(uid).hit_points
    if type(hp) is not int or hp <= 0:
        raise AssertionError("unit per-patient HP is missing")
    slots = result["slots"]
    if len({x["damage_position"] for x in slots}) != len(slots):
        raise AssertionError("RR-first target addresses are duplicated")
    available = result["reserve_wounds"] + sum(
        x["remaining_wounds"] for x in slots
    )
    if available != total:
        raise AssertionError("RR-first wound inputs do not match prior round")
    remaining = healed
    # Extra reserve entry is deliberately separate from combat Slots. A fixed
    # priority is only a comparison, not a known Gameforge per-target rule.
    locations = (
        [("reserve", None)] + [("slot", x) for x in slots] if reserve_first
        else [("slot", x) for x in slots] + [("reserve", None)]
    )
    grants = []
    for kind, slot in locations:
        amount = result["reserve_wounds"] if kind == "reserve" else slot["remaining_wounds"]
        applied = min(remaining, amount)
        if kind == "reserve":
            result["reserve_wounds"] -= applied
        else:
            slot["remaining_wounds"] -= applied
        remaining -= applied
        grants.append({
            "place": "Reserve" if kind == "reserve" else "Slot",
            "damage_position": None if kind == "reserve" else slot["damage_position"],
            "healing_hp": applied,
        })
    if remaining != 0 or sum(x["healing_hp"] for x in grants) != healed:
        raise AssertionError("RR-first healing allocation failed conservation")

    for slot in slots:
        if slot["units"] <= 0:
            if slot["remaining_wounds"]:
                raise AssertionError("empty Slot cannot carry injuries")
            slot["percent_current_model_format"] = 0
        else:
            slot["percent_current_model_format"] = _slot_bar(
                slot["remaining_wounds"], slot["units"], hp
            )
    reserve = result["reserve"]
    reserve_wounds = result["reserve_wounds"]
    if reserve_wounds < 0 or (
            reserve == 0 and reserve_wounds != 0
            or reserve > 0 and reserve_wounds >= reserve * hp):
        raise AssertionError("RR-first Reserve HP invalid")
    end = sum(x["remaining_wounds"] for x in slots) + reserve_wounds
    if end != total - healed:
        raise AssertionError("RR-first Slot+Reserve HP conservation failed")
    if original["alive"] != result["alive"] or original["reserve"] != result["reserve"]:
        raise AssertionError("healing changed living population or deployed population")
    result["hypothetical_healed_hp"] = healed
    result["hypothetical_remaining_wounds"] = end
    result["rr_method"] = (
        "first_experimental_RR_then_hypothetical_localized_healing"
    )
    result["localized_healing_evidence"] = grants
    result["same_deployment_assumed"] = True
    return result


def _delta(a: dict, b: dict) -> dict:
    if ((a["unit_id"], a["wave_id"]) != (b["unit_id"], b["wave_id"])):
        raise AssertionError("comparison loses Wave provenance")
    left = {s["damage_position"]: s for s in a["slots"]}
    right = {s["damage_position"]: s for s in b["slots"]}
    if left.keys() != right.keys():
        raise AssertionError("different physical Slot address sets")
    if any(left[pos]["units"] != right[pos]["units"] for pos in left):
        raise AssertionError("not same per-Slot living population")
    return {
        "slot_hp_wound_deltas": [
            {"damage_position": pos,
             "wounds_delta": right[pos]["remaining_wounds"] - left[pos]["remaining_wounds"]}
            for pos in sorted(left)
        ],
        "reserve_wounds_delta": b["reserve_wounds"] - a["reserve_wounds"],
    }


def build_report() -> dict:
    source = prior.source()
    rows, capacity = prior.wounded_eligible_waves(source)
    allocated = prior.allocations(rows, capacity)
    r2 = source["transitions"]["defender"]["before_r2"]
    registry = UnitRegistry.load(include_barbarians=True)
    combat_rows = [
        x for x in rows if x["alive"] and registry.get(x["unit_id"]).role == "combat"
    ]
    if not combat_rows:
        raise AssertionError("counterfactual analysis has no living combat Waves")
    if any(not x["eligible"] and allocated[name][
            (x["unit_id"], x["wave_id"])] for name in prior.POLICIES for x in rows):
        raise AssertionError("source wrongly heals ineligible support")
    bases = {
        (row["unit_id"], row["wave_id"]): _baseline(r2, row, registry)
        for row in combat_rows
    }
    cases = [{
        "case_id": "model_current_no_partial_healing_R2_prefire",
        "policy": prior.POLICIES[0], "ordering_hypothesis": "original_engine_fallback",
        "source_evidence": prior.LIVE_PROVENANCE,
        "game_mechanic_verified": False,
        "actual_changed_R2_combat_executed": False,
        "total_hypothetical_heal_hp": 0,
        "wave_hp": [deepcopy(bases[(x["unit_id"], x["wave_id"])])
                    for x in combat_rows],
        "sum_absolute_wound_differences_vs_heal_before_rr": 0,
    }]
    for policy in PRIORITIES:
        grant_by_wave = allocated[policy]
        for ordering in ORDERS:
            wave_hp = []
            difference = 0
            for row in combat_rows:
                key = row["unit_id"], row["wave_id"]
                healed = grant_by_wave[key]
                if ordering == ORDERS[0]:
                    projected = prior._rr_counterfactual(
                        r2, row, healed, registry
                    )
                else:
                    projected = rr_then_local_heal(
                        r2, row, healed, registry,
                        reserve_first=(ordering == ORDERS[2])
                    )
                if (projected["alive"] != bases[key]["alive"]
                        or projected["reserve"] != bases[key]["reserve"]
                        or sum(s["units"] for s in projected["slots"])
                        != sum(s["units"] for s in bases[key]["slots"])):
                    raise AssertionError("projected healing changed surviving fleet")
                if (projected["hypothetical_remaining_wounds"] + healed
                        != row["wounds_r1_end"]):
                    raise AssertionError("projected total HP accounting failed")
                if projected["hypothetical_remaining_wounds"] != (
                        sum(s["remaining_wounds"] for s in projected["slots"])
                        + projected["reserve_wounds"]):
                    raise AssertionError("projected Slot and Reserve wounds do not sum")
                wave_hp.append(projected)
                if ordering != ORDERS[0]:
                    ref = prior._rr_counterfactual(r2, row, healed, registry)
                    details = _delta(ref, projected)
                    difference += abs(details["reserve_wounds_delta"]) + sum(
                        abs(v["wounds_delta"]) for v in details["slot_hp_wound_deltas"]
                    )
            actual_total = sum(w["hypothetical_healed_hp"] for w in wave_hp)
            if actual_total != capacity:
                raise AssertionError("projected healing exceeded or omitted Tender capacity")
            cases.append({
                "case_id": f"{policy}__{ordering}",
                "policy": policy, "ordering_hypothesis": ordering,
                "source_evidence": PROVENANCE,
                "game_mechanic_verified": False,
                "actual_changed_R2_combat_executed": False,
                "total_hypothetical_heal_hp": actual_total,
                "wave_hp": wave_hp,
                "sum_absolute_wound_differences_vs_heal_before_rr": difference,
            })
    if len(cases) != 1 + len(PRIORITIES) * len(ORDERS):
        raise AssertionError("not all conditional order hypotheses compared")
    return {
        "schema": "p0_tender_healing_RR_localization_counterfactual_v1",
        "classification": PROVENANCE,
        "source": {
            "case_id": source["case_id"],
            "evidence_class": prior.LIVE_PROVENANCE,
            "source_run_rounds": 2,
            "game_observations": 0,
            "independent_holdouts": 0,
            "tender_count": 1,
            "model_reference_capacity_hp": capacity,
            "original_model_partial_healing_applied_hp": 0,
            "unknown_original_game_rule": prior.PENDING,
        },
        "summary": {
            "comparisons": len(cases),
            "hypothetical_comparisons": len(cases) - 1,
            "novel_game_observations": 0, "independent_holdouts": 0,
            "game_mechanic_verified": False,
        },
        "cases": cases,
        "limitations": [
            "Comparisons require hypothetical full 4000-HP model capacity use; real under-capacity Gameforge use is unknown.",
            "RR-then-slot-first or RR-then-Reserve-first also changes the healing recipient priority, so differences cannot identify chronology alone.",
            "All projections freeze real simulated R2 deployment and reuse experimental RR integer rounding; they are NOT alternate R2 battle executions.",
            "Only baseline source underwent actual synthetic R2 shots. No new Gameforge screenshots, observations or held-out data.",
        ],
    }


def csv_rows(report: dict) -> list[dict]:
    out = []
    for case in report["cases"]:
        for wave in case["wave_hp"]:
            out.append({
                "source_case_id": report["source"]["case_id"],
                "case_id": case["case_id"],
                "source_evidence": case["source_evidence"],
                "allocation_policy": case["policy"],
                "ordering_hypothesis": case["ordering_hypothesis"],
                "unit_id": wave["unit_id"], "wave_id": wave["wave_id"],
                "alive": wave["alive"], "reserve_units": wave["reserve"],
                "original_wave_wounds": wave["original_wounds_r1"],
                "hypothetical_healed_hp": wave["hypothetical_healed_hp"],
                "hypothetical_remaining_wounds": wave["hypothetical_remaining_wounds"],
                "hypothetical_reserve_wounds": wave["reserve_wounds"],
                "slots_json": json.dumps(wave["slots"], sort_keys=True),
                "localized_allocation_json": json.dumps(
                    wave.get("localized_healing_evidence", []), sort_keys=True
                ),
                "difference_vs_heal_before_rr": case[
                    "sum_absolute_wound_differences_vs_heal_before_rr"],
                "game_mechanic_verified": False,
                "alternate_R2_combat_executed": False,
                "new_game_observations": 0,
                "independent_holdouts": 0,
            })
    if len({(x["case_id"], x["unit_id"], x["wave_id"]) for x in out}) != len(out):
        raise AssertionError("CSV projection loses case-qualified Wave identity")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    data = build_report()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    rows = csv_rows(data)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(data["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
