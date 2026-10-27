"""Unverified, conditional R1/R2 HP-bar integer inverse bounds.

Secure local image binding is necessary, NOT Gameforge authenticity. Declared
unit HP, unchanged physical survivors and percentage denominator are assumptions.
No official Tender repair mechanism or rounding mode is inferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.research import p0_naval_local_stage_delta_bundle as stages
from tools.research.p0_naval_hp_bar_inverse_bounds import (
    ROUNDING_MODES, percent_window,
)

SCHEMA = "p0_naval_conditional_hp_intervals_v1"
ASSUMPTIONS_SCHEMA = "p0_naval_conditional_hp_assumptions_v1"
DENOMINATOR = "constant_living_unit_hp_times_same_living_units"
COMPLETE = "CONDITIONAL_HP_INTERVALS_UNVERIFIED"
PARTIAL = "CONDITIONAL_HP_INTERVALS_PARTIAL_UNVERIFIED"
GATED = "NOT_ASSESSABLE_LOCAL_STAGE_BYTES_UNBOUND"
INVALID = "INVALID_USER_HP_ASSUMPTIONS"
MAX_UNIT_HP = 1_000_000
MAX_CAPACITY = 1_000_000_000


def validate_assumptions(config):
    if not isinstance(config, dict) or set(config) != {
            "schema", "denominator_assumption", "unit_hp_by_unit_id"}:
        return ["assumptions: expected only schema, denominator_assumption, unit_hp_by_unit_id"]
    errors = []
    if config["schema"] != ASSUMPTIONS_SCHEMA:
        errors.append("assumptions.schema: unexpected schema")
    if config["denominator_assumption"] != DENOMINATOR:
        errors.append("assumptions.denominator_assumption: explicit hypothesis acknowledgement required")
    hp = config["unit_hp_by_unit_id"]
    if not isinstance(hp, dict) or len(hp) > 100:
        errors.append("assumptions.unit_hp_by_unit_id: expected at most 100 entries")
        return errors
    for unit, amount in hp.items():
        if (not isinstance(unit, str) or not unit.strip()
                or unit.strip() != unit or len(unit) > 120
                or type(amount) is not int or not 1 <= amount <= MAX_UNIT_HP):
            errors.append("assumptions.unit_hp_by_unit_id: invalid unit name or integer HP")
            break
    return errors


def analyze(record, manifest, evidence_root: Path, assumptions):
    out = {
        "schema": SCHEMA, "status": INVALID,
        "upstream_status": "NOT_EVALUATED",
        "manual_transcription_sha256": None,
        "local_image_bytes_sha256_by_stage": {},
        "rounding_modes_tested": list(ROUNDING_MODES),
        "denominator_assumption": DENOMINATOR,
        "user_supplied_hp_not_verified_against_gameforge": True,
        "conditional_slot_ranges": [], "not_assessable_slot_labels": [],
        "blockers": [],
        "original_game_screenshots_authenticated": False,
        "actual_physical_ship_continuity_verified": False,
        "official_hp_bar_rounding_verified": False,
        "official_tender_healing_verified": False,
        "official_heal_rr_order_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "notes": [
            "Hypothesis: displayed percent of living-units times each user's declared unit HP.",
            "Same physical hulls and absence of reserve substitution NOT verified.",
            "Positive conditional net HP change does NOT prove Tender repair.",
            "Local byte differences do not prove Gameforge screenshot provenance or timing.",
            "No screenshot bytes, local paths or whole input records in this output.",
        ],
    }
    errors = validate_assumptions(assumptions)
    if errors:
        out["blockers"].extend(errors)
        return out
    bundle = stages.compare_local_bundle(record, manifest, evidence_root)
    out["upstream_status"] = bundle["status"]
    out["manual_transcription_sha256"] = bundle["manual_transcription_sha256"]
    out["blockers"].extend(bundle["comparability_blockers"])
    if bundle["status"] not in (stages.READY, stages.PARTIAL):
        out["status"] = GATED
        out["blockers"].append("local R1/R2 byte gate did not admit stage differences")
        return out
    out["local_image_bytes_sha256_by_stage"] = dict(
        bundle["local_image_bytes_sha256_by_stage"])
    by_unit = assumptions["unit_hp_by_unit_id"]
    for pair in bundle["candidate_label_matches"]:
        label = {key: pair[key] for key in (
            "side", "unit_id", "wave_label", "physical_slot_label")}
        n1, n2 = pair["r1_units_alive"], pair["r2_units_alive"]
        hp = by_unit.get(pair["unit_id"])
        if n1 != n2:
            out["not_assessable_slot_labels"].append({
                **label, "reason": "different_living_unit_count_denominator_or_hull_identity_unknown"})
            continue
        if n1 <= 0:
            out["not_assessable_slot_labels"].append({
                **label, "reason": "zero_living_units_no_positive_hp_denominator"})
            continue
        if hp is None:
            out["not_assessable_slot_labels"].append({
                **label, "reason": "missing_user_supplied_unit_hp"})
            continue
        cap = n1 * hp
        if cap > MAX_CAPACITY:
            out["not_assessable_slot_labels"].append({
                **label, "reason": "derived_hp_capacity_exceeds_safety_bound"})
            continue
        modes = {}
        for mode in ROUNDING_MODES:
            try:
                r1_lo, r1_hi = percent_window(pair["r1_visible_percent"], cap, mode)
                r2_lo, r2_hi = percent_window(pair["r2_visible_percent"], cap, mode)
            except ValueError:
                modes[mode] = {"compatible_with_display_model": False}
                continue
            lo, hi = r1_lo - r2_hi, r1_hi - r2_lo
            modes[mode] = {
                "compatible_with_display_model": True,
                "r1_remaining_wounds_hp_interval": [r1_lo, r1_hi],
                "r2_remaining_wounds_hp_interval": [r2_lo, r2_hi],
                "conditional_net_hp_increase_interval": [lo, hi],
                "conditional_positive_increase_required": lo > 0,
                "conditional_decrease_required": hi < 0,
            }
        compatible = [item for item in modes.values()
                      if item["compatible_with_display_model"]]
        out["conditional_slot_ranges"].append({
            **label,
            "r1_visible_percent": pair["r1_visible_percent"],
            "r2_visible_percent": pair["r2_visible_percent"],
            "unchanged_user_reported_living_units": n1,
            "user_supplied_hp_per_unit": hp,
            "assumed_constant_living_hp_capacity": cap,
            "rounding_mode_intervals": modes,
            "all_three_rounding_modes_compatible": (
                len(compatible) == len(ROUNDING_MODES)),
            "positive_hp_increase_required_across_all_three_modes": (
                len(compatible) == len(ROUNDING_MODES)
                and all(q["conditional_positive_increase_required"]
                        for q in compatible)),
            "same_physical_survivors_verified": False,
            "tender_repair_causation_verified": False,
        })
    out["status"] = (
        COMPLETE if (bundle["status"] == stages.READY
                     and out["conditional_slot_ranges"]
                     and not out["not_assessable_slot_labels"]
                     and all(q["all_three_rounding_modes_compatible"]
                             for q in out["conditional_slot_ranges"]))
        else PARTIAL)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--hp-assumptions", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()
    result = analyze(
        json.loads(args.record.read_text(encoding="utf-8")),
        json.loads(args.manifest.read_text(encoding="utf-8")),
        args.evidence_root,
        json.loads(args.hp_assumptions.read_text(encoding="utf-8")))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output_json)}))
    if result["status"] in (INVALID, GATED):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
