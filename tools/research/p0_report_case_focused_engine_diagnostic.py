"""Local read-only focused research diagnostic from ACTUAL production engine.

Requires the original, independently *unverified* local image files, manual
review worksheet and explicit slot/Wave mapping used by the existing strict
engine trace tool. A user-asserted mapping is not an authenticated Gameforge
battle or a calibrated model. This tool never produces browser candidate
worksheets (which have a USER_ENTERED source class).
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_manual_visual_review as manual
from tools.research import p0_report_case_real_engine_trace as engine

SCHEMA = "p0_focused_actual_engine_capture_diagnostic_v1"
LINES = ("first", "second", "third", "flank", "balloon", "anti-balloon")
STATUS = "CONDITIONAL_ENGINE_MINUS_USER_TRANSCRIPTION_NOT_CALIBRATION"


def focused_diagnostic(
    scenario_bytes: bytes,
    case_bytes: bytes,
    manifest: dict,
    evidence_root: Path,
    review_bytes: bytes,
    slot_map: dict,
    *,
    capture_id: str,
    side: str,
    line: str,
) -> dict:
    """Re-execute the current engine and reuse the fully gated PR #116 alignment.

    An omitted mapping row is UNKNOWN, never an implicit Wave match or a
    guessed empty position. Count deltas come only from the source-reviewed,
    explicitly aligned predecessor, never from this presenter itself.
    """
    if binder._inspect_case(case_bytes) is None:
        raise ValueError("invalid canonical browser case or Node unavailable")
    case = json.loads(case_bytes)
    research = case.get("research")
    if (
        not isinstance(research, dict)
        or research.get("kind") != "partial_observation"
        or not isinstance(research.get("objective"), str)
        or not research["objective"].strip()
        or not isinstance(research.get("observed_scope"), str)
        or not research["observed_scope"].strip()
    ):
        raise ValueError("focused actual-engine comparison requires declared partial_observation scope")
    if side not in engine.SIDES or line not in LINES:
        raise ValueError("focused side/line must be a canonical formation address")
    if not isinstance(capture_id, str) or not capture_id:
        raise ValueError("focused captured-round ID missing")
    matches = [r for r in case["rounds"] if r["id"] == capture_id]
    if len(matches) != 1:
        raise ValueError("focused captured-round ID not unique or not found")
    capture = matches[0]
    if capture["phase"] != "round_end":
        raise ValueError("game prefire/unknown phase cannot align to model round-end")
    observations = [s for s in capture[side]["slots"] if s["line"] == line]
    if not observations or not any(
        s["count"] is not None or s["hp"] is not None or s["deaths"] is not None
        for s in observations
    ):
        raise ValueError("selected captured side/line has no typed numeric observation")

    # Real execution and strict file-byte, reviewer, user-asserted address gates.
    # The existing adapter must be allowed to reject stale image hashes,
    # unsupported phases, wrong effective geometry or forged Wave bindings.
    trace = engine.engine_trace(scenario_bytes)
    alignment = engine.compare_to_captures(
        trace, case_bytes, manifest, evidence_root, review_bytes, slot_map
    )
    if (
        alignment.get("schema") != "p0_real_engine_vs_report_capture_alignment_v1"
        or alignment.get("case_sha256") != sha256(case_bytes).hexdigest()
        or alignment.get("scenario_sha256") != trace["scenario_sha256"]
        or alignment.get("engine_output_sha256") != trace["engine_output_sha256"]
        or alignment.get("engine_executed") is not True
        or alignment.get("model_calibration_verified") is not False
    ):
        raise ValueError("strict engine alignment provenance invalid")
    indexed = {}
    for bound in alignment["bindings"]:
        if (
            bound["target_capture_id"] != capture_id or bound["side"] != side
            or bound["line"] != line
        ):
            continue
        pos = bound["physical_position"]
        if pos in indexed:
            raise ValueError("ambiguous multiple source-review bindings for same focused slot")
        indexed[pos] = bound

    rows = []
    seen_positions = set()
    assessed = 0
    for slot in sorted(observations, key=lambda s: s["pos"]):
        pos = slot["pos"]
        if pos in seen_positions:
            raise ValueError("duplicate typed physical slot")
        seen_positions.add(pos)
        binding = indexed.pop(pos, None)
        status = (
            binding["diagnostic_status"] if binding
            else "NOT_ASSESSABLE_NO_EXPLICIT_REVIEW_SLOT_BINDING"
        )
        delta = binding["count_difference"] if binding else None
        if status != "ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED":
            if delta is not None:
                raise ValueError("ineligible binding must never contain a numeric delta")
        else:
            if type(delta) is not int or type(slot["count"]) is not int:
                raise ValueError("eligible difference requires both typed and model counts")
            assessed += 1
        rows.append({
            "physical_position": pos,
            "typed_unit_label": slot["unit"],
            "typed_wave_label": slot["wave"],
            "typed_count": slot["count"],
            "typed_hp_percent": slot["hp"],
            "typed_deaths": slot["deaths"],
            "explicit_binding_present": binding is not None,
            "engine_wave_id_user_asserted": binding["engine_wave_id"] if binding else None,
            "engine_unit_id": binding["engine_unit_id"] if binding else None,
            "engine_count_context_only": binding["engine_units"] if binding else None,
            "engine_internal_hp_context_only": (
                binding["engine_hp_metric_percent"] if binding else None
            ),
            "count_comparison_status": status,
            "engine_minus_typed_count": delta,
            "engine_minus_game_hp_points": None,
            "mechanic_verified": False,
        })
    if indexed:
        raise ValueError("strict mapping referenced a slot not present in selected transcription")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_class": engine.SOURCE,
        "case_sha256": sha256(case_bytes).hexdigest(),
        "scenario_sha256": trace["scenario_sha256"],
        "engine_source_sha256": trace["engine_file_sha256"],
        "engine_output_sha256": trace["engine_output_sha256"],
        "review_worksheet_sha256": alignment["review_worksheet_sha256"],
        "case_id": case["id"],
        "capture_id": capture_id,
        "capture_round": capture["number"],
        "capture_phase": capture["phase"],
        "side": side, "line": line,
        "research_scope_declared": True,
        "engine_policy": trace["engine_policy"],
        "engine_applied_assumptions": trace["engine_applied_assumptions"],
        "engine_unsupported_events": trace["engine_unsupported_events"],
        "selected_typed_slot_rows_only": True,
        "typed_positions": len(rows),
        "explicit_bindings_in_focus": sum(r["explicit_binding_present"] for r in rows),
        "descriptive_count_comparisons": assessed,
        "unknown_positions_not_invented": True,
        "hp_bar_comparison_performed": False,
        "game_source_authenticated": False,
        "scenario_reconstructed_from_game": False,
        "physical_mapping_independently_verified": False,
        "independent_holdouts": 0,
        "global_calibration_allowed": False,
        "source_notes_or_image_paths_exported": False,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--review-worksheet", required=True, type=Path)
    parser.add_argument("--slot-map", required=True, type=Path)
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--side", required=True, choices=engine.SIDES)
    parser.add_argument("--line", required=True, choices=LINES)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = focused_diagnostic(
            binder._read_limited(args.scenario, engine.MAX_JSON_BYTES),
            binder._read_limited(args.case, binder.MAX_CASE_BYTES),
            json.loads(binder._read_limited(args.manifest, binder.MAX_MANIFEST_BYTES)),
            args.evidence_root,
            binder._read_limited(args.review_worksheet, manual.MAX_REVIEW_BYTES),
            json.loads(binder._read_limited(args.slot_map, engine.MAX_JSON_BYTES)),
            capture_id=args.capture_id, side=args.side, line=args.line,
        )
        serialized = engine._bytes_json(result) + b"\n"
        if len(serialized) > engine.MAX_JSON_BYTES:
            raise ValueError("focused report exceeds output size limit")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"rejected focused engine diagnostic: {type(exc).__name__}\n")
    # Never overwrite an existing evidence/result file.
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output_json.open("xb") as out:
            out.write(serialized)
    except FileExistsError:
        parser.exit(2, "refusing to overwrite earlier diagnostic or source evidence\n")
    print(json.dumps({
        "status": STATUS,
        "typed_positions": result["typed_positions"],
        "explicit_bindings": result["explicit_bindings_in_focus"],
        "descriptive_count_comparisons": result["descriptive_count_comparisons"],
        "verified_game_mechanics": False,
    }))


if __name__ == "__main__":
    main()
