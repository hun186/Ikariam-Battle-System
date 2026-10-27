"""Synthetic-only sensitivity probe for a possible carrier-late Tender priority.

No official Ikariam healing order or real source shots are known. This only
compares three hypothetical bounded allocations at identical wounded inputs.
Do NOT use the produced healed-HP numbers as Gameforge observations.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

SCHEMA = "p0_naval_carrier_late_tender_priority_v1"
KIND = "hypothetical_wound_input_not_game_observation"
PROVENANCE = "OWNER_QUALITATIVE_CARRIER_LATE_HYPOTHESIS_SYNTHETIC_MATH"
POLICIES = (
    "noncarrier_before_carrier",
    "proportional_all",
    "carrier_before_noncarrier",
)
READY = "HYPOTHETICAL_PRIORITY_SENSITIVITY_ONLY"
INCONCLUSIVE = "HYPOTHETICAL_NOT_DISCRIMINATING"
INVALID = "INVALID_HYPOTHETICAL_WOUND_INPUT"


def _identifier(value) -> bool:
    return (isinstance(value, str) and value == value.strip()
            and bool(value) and len(value) <= 120)


def validate(record) -> list[str]:
    if not isinstance(record, dict) or set(record) != {
            "schema", "record_kind", "carrier_unit_ids",
            "healing_capacity_hp_levels", "wounded_waves"}:
        return ["requires exactly schema, record_kind, carrier_unit_ids, healing_capacity_hp_levels, wounded_waves"]
    errors = []
    if record["schema"] != SCHEMA or record["record_kind"] != KIND:
        errors.append("wrong schema or hypothetical-only record classification")
    carriers = record["carrier_unit_ids"]
    if (not isinstance(carriers, list) or not 1 <= len(carriers) <= 8
            or any(not _identifier(v) for v in carriers)
            or len(carriers) != len(set(carriers))):
        errors.append("carrier_unit_ids must contain unique nonblank unit IDs")
        carriers = []
    levels = record["healing_capacity_hp_levels"]
    if (not isinstance(levels, list) or not 1 <= len(levels) <= 20
            or any(type(n) is not int or not 0 <= n <= 1_000_000_000 for n in levels)
            or len(levels) != len(set(levels))):
        errors.append("capacity levels must be distinct bounded nonnegative integer HP")
    waves = record["wounded_waves"]
    if not isinstance(waves, list) or not 2 <= len(waves) <= 60:
        errors.append("wounded_waves must contain 2..60 rows")
        return errors
    seen, total = set(), 0
    for index, row in enumerate(waves):
        if (not isinstance(row, dict) or set(row) != {
                "unit_id", "wave_label", "eligible_for_tender", "wounds_hp"}):
            errors.append(f"wounded_waves[{index}]: malformed row")
            continue
        unit, wave = row["unit_id"], row["wave_label"]
        wound, eligible = row["wounds_hp"], row["eligible_for_tender"]
        if (not _identifier(unit) or not _identifier(wave)
                or type(eligible) is not bool
                or type(wound) is not int or not 0 <= wound <= 1_000_000_000):
            errors.append(f"wounded_waves[{index}]: invalid labels/eligible/wounds HP")
            continue
        if (unit, wave) in seen:
            errors.append(f"wounded_waves[{index}]: duplicate unit/Wave identity")
        seen.add((unit, wave))
        total += wound if eligible else 0
    if total > 1_000_000_000:
        errors.append("eligible wounds exceed safe aggregate capacity")
    return errors


def _largest_remainder(rows: list[dict], amount: int) -> dict[tuple[str, str], int]:
    """Deterministic proportional integer allocation within one group."""
    total = sum(row["wounds_hp"] for row in rows)
    budget = min(total, amount)
    if total == 0:
        return {(r["unit_id"], r["wave_label"]): 0 for r in rows}
    assignments = {}
    scores = []
    for row in rows:
        key = row["unit_id"], row["wave_label"]
        value = row["wounds_hp"] * budget
        base, residue = divmod(value, total)
        assignments[key] = base
        scores.append((-residue, key))
    leftover = budget - sum(assignments.values())
    for _, key in sorted(scores)[:leftover]:
        assignments[key] += 1
    if sum(assignments.values()) != budget:
        raise AssertionError("conditional healing allocation not conserved")
    return assignments


def _one_policy(waves: list[dict], carrier_units: set[str],
                capacity: int, policy: str) -> dict:
    eligible = [x for x in waves if x["eligible_for_tender"] and x["wounds_hp"]]
    carriers = [x for x in eligible if x["unit_id"] in carrier_units]
    others = [x for x in eligible if x["unit_id"] not in carrier_units]
    if policy == POLICIES[0]:
        groups = (others, carriers)
    elif policy == POLICIES[1]:
        groups = (eligible,)
    elif policy == POLICIES[2]:
        groups = (carriers, others)
    else:
        raise ValueError("unsupported hypothetical allocation")
    healed, remaining = {}, capacity
    for group in groups:
        assigned = _largest_remainder(group, remaining)
        if healed.keys() & assigned.keys():
            raise AssertionError("duplicate assigned wound-wave")
        healed.update(assigned)
        remaining -= sum(assigned.values())
    rows = []
    for wave in sorted(waves, key=lambda x: (x["unit_id"], x["wave_label"])):
        key = wave["unit_id"], wave["wave_label"]
        amount = healed.get(key, 0)
        if amount < 0 or amount > wave["wounds_hp"]:
            raise AssertionError("healing exceeds assumed wound input")
        rows.append({
            "unit_id": key[0],
            "wave_label": key[1],
            "hypothetical_healed_hp": amount,
            "hypothetical_remaining_wounds_hp": wave["wounds_hp"] - amount,
            "is_user_declared_carrier": key[0] in carrier_units,
        })
    spent = sum(x["hypothetical_healed_hp"] for x in rows)
    if spent + remaining != capacity:
        raise AssertionError("hypothetical healing budget not conserved")
    return {
        "hypothetical_carrier_healed_hp": sum(x["hypothetical_healed_hp"] for x in rows
                                              if x["is_user_declared_carrier"]),
        "hypothetical_noncarrier_healed_hp": sum(x["hypothetical_healed_hp"] for x in rows
                                                 if not x["is_user_declared_carrier"]),
        "hypothetical_total_healed_hp": spent,
        "unused_hypothetical_capacity_hp": remaining,
        "per_wave": rows,
    }


def compare(record) -> dict:
    """Never fetch combat logs or authenticate visual bars; math only."""
    out = {
        "schema": SCHEMA, "status": INVALID,
        "source_evidence_class": PROVENANCE,
        "owner_qualitative_observation_authenticated_by_screenshots": False,
        "actual_gameforge_healing_order_verified": False,
        "actual_carrier_healing_amount_verified": False,
        "official_tender_heal_rr_order_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "policies": list(POLICIES),
        "hypothetical_carrier_wounds_hp": 0,
        "hypothetical_noncarrier_wounds_hp": 0,
        "noncarrier_saturation_threshold_hp": None,
        "sensitivity_by_capacity": [],
        "discriminating_capacity_levels": [],
        "validation_errors": [],
        "notes": [
            "Three integer policies are hypothetical, not actual Gameforge priority rules.",
            "A carrier bar slowly declining over rounds can also reflect new attack damage, reserve replacement or UI rounding.",
            "A higher Tender count is not a direct measurement of allocated HP without equal wound inputs.",
            "Carriers receive zero under the carrier-last policy until the other eligible hypothetical wounds saturate.",
            "Healing chronology vs Reserve redistribution remains unverified.",
        ],
    }
    errors = validate(record)
    if errors:
        out["validation_errors"] = errors
        return out
    waves = deepcopy(record["wounded_waves"])
    carrier_ids = set(record["carrier_unit_ids"])
    carrier_wounds = sum(w["wounds_hp"] for w in waves
                         if w["eligible_for_tender"] and w["unit_id"] in carrier_ids)
    other_wounds = sum(w["wounds_hp"] for w in waves
                       if w["eligible_for_tender"] and w["unit_id"] not in carrier_ids)
    out["hypothetical_carrier_wounds_hp"] = carrier_wounds
    out["hypothetical_noncarrier_wounds_hp"] = other_wounds
    out["noncarrier_saturation_threshold_hp"] = other_wounds
    for capacity in sorted(record["healing_capacity_hp_levels"]):
        comparisons = {p: _one_policy(waves, carrier_ids, capacity, p)
                       for p in POLICIES}
        carrier_amounts = {
            p: comparisons[p]["hypothetical_carrier_healed_hp"] for p in POLICIES}
        distinguishes = len(set(carrier_amounts.values())) > 1
        out["sensitivity_by_capacity"].append({
            "hypothetical_capacity_hp": capacity,
            "hypotheses_have_different_carrier_healing": distinguishes,
            "hypothetical_allocation_by_policy": comparisons,
        })
        if distinguishes:
            out["discriminating_capacity_levels"].append(capacity)
    out["status"] = (READY if carrier_wounds > 0 and other_wounds > 0
                     and out["discriminating_capacity_levels"] else INCONCLUSIVE)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()
    result = compare(json.loads(args.input.read_text(encoding="utf-8")))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output_json)}))
    if result["status"] == INVALID:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
