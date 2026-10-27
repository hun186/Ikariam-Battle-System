"""Research-only R1-end versus R2-prefire screenshot TRANSCRIPTION arithmetic.

Pairs are based on USER-DECLARED labels, not authenticated ship identity.
Does not read images, infer Tender healing or modify the combat simulator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.research import p0_naval_capture_archive as archive_module

SCHEMA = "p0_naval_stage_pair_deltas_v1"
SUCCESS = "UNVERIFIED_LABEL_MATCHED_STAGE_DELTAS"
PARTIAL = "UNVERIFIED_PARTIAL_STAGE_COMPARISON"
INVALID = "INVALID"
FIELDS = ("side", "unit_id", "wave_label", "physical_slot_label")


def _nonblank(v):
    return isinstance(v, str) and bool(v.strip())


def compare(record):
    out = {
        "schema": SCHEMA, "status": INVALID,
        "archive_status": "NOT_EVALUATED",
        "manual_transcription_sha256": None,
        "manual_transcription_digest_is_image_digest": False,
        "source_class": archive_module.SOURCE_CLASS,
        "candidate_label_matches": [], "unmatched_r1_labels": [],
        "unmatched_r2_labels": [], "ambiguous_physical_slots": [],
        "missing_for_followup": [],
        "comparability_blockers": [],
        "matching_is_independent_physical_ship_identity": False,
        "screenshot_source_provenance_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "game_combat_hypothesis_comparison_performed": False,
        "official_healing_or_damage_mechanism_verified": False,
        "notes": [
            "Only user-supplied labels and integer subtraction are compared.",
            "Displayed slot HP percentages are NOT measured individual ship HP.",
            "Exact wave/slot labels do not independently prove physical identity.",
            "Multiple unit/wave rows occupying one self-labeled slot in a phase are ambiguous, not separately confirmed physical groups.",
            "A JSON transcription digest is NOT screenshot byte SHA-256.",
            "An increased percent does NOT prove Tender healing or Heal/RR order.",
            "No screenshot was loaded, inspected or authenticated.",
        ],
    }
    try:
        result = archive_module.archive(record)
    except (KeyError, TypeError, AttributeError, ValueError):
        out["comparability_blockers"].append("record: malformed archival input")
        return out
    out["archive_status"] = result["status"]
    out["manual_transcription_sha256"] = result["user_record_sha256"]
    if result["status"] not in ("UNVERIFIED_ARCHIVE_READY",
                                "UNVERIFIED_ARCHIVE_INCOMPLETE"):
        out["comparability_blockers"].append(
            "record: valid nonempty archival transcription required")
        return out

    out["status"] = PARTIAL
    missing = set(result["missing_for_followup"])
    ctx = record["battle_context"]
    refs = record["source_refs"]
    r1, r2 = refs.get("r1_end"), refs.get("r2_prefire")
    if not (_nonblank(r1) and _nonblank(r2) and r1 != r2):
        out["comparability_blockers"].append(
            "source_refs: distinct nonblank R1-end and R2-prefire refs required")
    if ctx.get("r2_prefire_confirmed") is not True:
        out["comparability_blockers"].append(
            "battle_context.r2_prefire_confirmed: true required")
    if ctx.get("reinforcements_between") != "none":
        out["comparability_blockers"].append(
            "battle_context.reinforcements_between: explicit none required")
    out["missing_for_followup"] = sorted(missing)
    if out["comparability_blockers"]:
        return out

    rows = {"r1_end": {}, "r2_prefire": {}}
    for i, row in enumerate(record["observations"]):
        values = [row.get(field) for field in FIELDS]
        if not all(_nonblank(value) for value in values):
            for field, value in zip(FIELDS, values):
                if not _nonblank(value):
                    missing.add(f"observations[{i}].{field}")
            continue
        phase = row["phase"]
        if not _nonblank(row.get("source_ref")) or row["source_ref"] != refs[phase]:
            missing.add(f"observations[{i}].source_ref_mismatch")
            continue
        rows[phase][tuple(values)] = (i, row)

    # The v2 archive permits separate unit/wave rows to name the same physical
    # slot in one side and phase. Such rows are independently well-typed but
    # cannot both establish unique slot ownership. Do NOT choose one wave
    # and report a misleading cross-round HP/casualty delta for that slot.
    slot_owners = {}
    for phase, entries in rows.items():
        for key, (index, _) in entries.items():
            side, unit_id, wave, slot = key
            locator = (phase, side, slot)
            slot_owners.setdefault(locator, []).append(
                (index, unit_id, wave))
    ambiguous = set()
    for locator, owners in sorted(slot_owners.items()):
        if len({(unit_id, wave) for _, unit_id, wave in owners}) <= 1:
            continue
        ambiguous.add(locator)
        phase, side, slot = locator
        out["ambiguous_physical_slots"].append({
            "phase": phase,
            "side": side,
            "physical_slot_label": slot,
            "observation_indices": sorted(i for i, _, _ in owners),
            "competing_unit_wave_labels": [
                {"unit_id": unit_id, "wave_label": wave}
                for unit_id, wave in sorted(
                    {(unit_id, wave) for _, unit_id, wave in owners})
            ],
            "physical_slot_ownership_verified": False,
        })
    left, right = rows["r1_end"], rows["r2_prefire"]
    for key in sorted(left.keys() - right.keys()):
        out["unmatched_r1_labels"].append(dict(zip(FIELDS, key)))
    for key in sorted(right.keys() - left.keys()):
        out["unmatched_r2_labels"].append(dict(zip(FIELDS, key)))
    for key in sorted(left.keys() & right.keys()):
        side, _, _, slot = key
        if (("r1_end", side, slot) in ambiguous
                or ("r2_prefire", side, slot) in ambiguous):
            # A collision in EITHER snapshot invalidates an otherwise
            # apparently identical wave/slot pairing.
            continue
        ai, a = left[key]
        bi, b = right[key]
        if any(type(row.get(field)) is not int for row in (a, b)
               for field in ("visible_percent", "units_alive")):
            for idx, row in ((ai, a), (bi, b)):
                for field in ("visible_percent", "units_alive"):
                    if type(row.get(field)) is not int:
                        missing.add(f"observations[{idx}].{field}")
            continue
        out["candidate_label_matches"].append({
            **dict(zip(FIELDS, key)),
            "r1_observation_index": ai, "r2_observation_index": bi,
            "r1_units_alive": a["units_alive"],
            "r2_units_alive": b["units_alive"],
            "units_alive_delta_r2_minus_r1": b["units_alive"] - a["units_alive"],
            "r1_visible_percent": a["visible_percent"],
            "r2_visible_percent": b["visible_percent"],
            "visible_percentage_point_delta_r2_minus_r1": (
                b["visible_percent"] - a["visible_percent"]),
            "physical_group_identity_verified": False,
            "healing_causation_verified": False,
        })
    out["missing_for_followup"] = sorted(missing)
    if (out["candidate_label_matches"] and not out["missing_for_followup"]
            and not out["unmatched_r1_labels"] and not out["unmatched_r2_labels"]
            and not out["ambiguous_physical_slots"]):
        out["status"] = SUCCESS
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()
    result = compare(json.loads(args.input.read_text(encoding="utf-8")))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output_json)}))
    if result["status"] == INVALID:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
