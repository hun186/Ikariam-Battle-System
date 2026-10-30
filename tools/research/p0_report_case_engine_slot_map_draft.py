"""Prepare user-reviewed candidate positions for PR116 actual-engine mappings.

A candidate engine Wave/address is NOT an authenticated Gameforge battle Wave.
This output is deliberately NOT a valid executable or verified slot map.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_manual_visual_review as manual
from tools.research import p0_report_case_real_engine_trace as engine

SCHEMA = "p0_real_engine_slot_map_preparation_v1"


def prepare_draft(
    scenario_bytes: bytes, case_bytes: bytes, manifest: dict,
    evidence_root: Path, review_bytes: bytes,
) -> dict:
    """Index actual-engine slots after fresh source validation; assert no match."""
    case_info = binder._inspect_case(case_bytes)
    if case_info is None:
        raise ValueError("invalid canonical browser case")
    case = json.loads(case_bytes)
    review = manual.assess_review(
        case_bytes, manifest, evidence_root, json.loads(review_bytes)
    )
    trace = engine.engine_trace(scenario_bytes)
    if (trace["scenario_battlefield"] != case["battlefield"] or
        trace["engine_effective_battlefield"] != case["battlefield"]):
        raise ValueError("requested/effective engine battlefield differs from case")
    captures = {r["id"]: r for r in case["rounds"]}
    rows = []
    for index, item in enumerate(review["review_items"]):
        capture = captures.get(item["target_capture_id"])
        if capture is None or capture["number"] != item["target_round"]:
            raise ValueError("review row does not identify a canonical capture")
        address = (item["side"], item["line"], item["physical_position"])
        candidates = []
        if (address[0] in engine.SIDES and isinstance(address[1], str)
                and type(address[2]) is int):
            for snapshot in trace["engine_slots"]:
                if (snapshot["engine_round"] == item["target_round"] and
                    (snapshot["side"], snapshot["line"],
                     snapshot["physical_position"]) == address):
                    candidates.append({
                        "engine_wave_id": snapshot["wave_id"],
                        "engine_unit_id": snapshot["unit_id"],
                        "engine_slot_id": snapshot["slot_id"],
                        "engine_phase": snapshot["engine_phase"],
                        "engine_units": snapshot["units"],
                    })
        # Never prefer candidates based on typed HP or label similarity.
        candidates.sort(key=lambda s: (str(s["engine_wave_id"]), str(s["engine_slot_id"])))
        if address[0] not in engine.SIDES or address[1] is None or address[2] is None:
            status = "NO_TYPED_PHYSICAL_ADDRESS"
        elif capture["phase"] != "round_end":
            status = "CAPTURE_PHASE_NOT_ROUND_END"
        elif item["round_number_gap"] != 1 or not item["same_capture_phase"]:
            status = "MISSING_INTERMEDIATE_GAME_ROUND_OR_PHASE_MISMATCH"
        elif item["reviewer_reported_status"] != "REVIEWER_REPORTS_IMAGES_READABLE":
            status = "NO_USER_REPORTED_READABLE_PAIR"
        elif not candidates:
            status = "NO_ENGINE_SLOT_AT_ADDRESS"
        elif any(s["engine_phase"] != "round_end_model_snapshot" for s in candidates):
            status = "ENGINE_ROUND_NOT_COMPLETED"
        elif any(e["round"] is None or e["round"] <= item["target_round"]
                 for e in trace["engine_unsupported_events"]):
            status = "ENGINE_UNSUPPORTED_MECHANIC_BOUNDARY"
        else:
            status = "CANDIDATE_ADDRESS_REQUIRES_HUMAN_WAVE_ASSERTION"
        rows.append({
            "review_item_index": index,
            "target_capture_id": item["target_capture_id"],
            "target_round": item["target_round"],
            "side": item["side"], "line": item["line"],
            "physical_position": item["physical_position"],
            "reviewer_reported_status": item["reviewer_reported_status"],
            "preparation_status": status,
            "engine_candidates_unverified": candidates,
            "selected_engine_wave_id": None,
        })
    return {
        "schema": SCHEMA,
        "record_kind": "UNVERIFIED_RESEARCH_PREPARATION_NOT_A_SLOT_MAP",
        "case_id": case_info["id"],
        "case_sha256": sha256(case_bytes).hexdigest(),
        "scenario_sha256": trace["scenario_sha256"],
        "review_worksheet_sha256": sha256(review_bytes).hexdigest(),
        "engine_output_sha256": trace["engine_output_sha256"],
        "engine_effective_battlefield": trace["engine_effective_battlefield"],
        "rows": rows,
        "automatic_slot_bindings_created": 0,
        "can_be_used_as_verified_slot_map": False,
        "user_wave_and_physical_slot_assertion_required": True,
        "original_game_screenshots_authenticated": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "model_calibration_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--review-worksheet", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = prepare_draft(
            binder._read_limited(args.scenario, engine.MAX_JSON_BYTES),
            binder._read_limited(args.case, binder.MAX_CASE_BYTES),
            json.loads(binder._read_limited(args.manifest, binder.MAX_MANIFEST_BYTES)),
            args.evidence_root,
            binder._read_limited(args.review_worksheet, manual.MAX_REVIEW_BYTES),
        )
        encoded = engine._bytes_json(report) + b"\n"
        if len(encoded) > engine.MAX_JSON_BYTES:
            raise ValueError("preparation report exceeds output byte limit")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"invalid source or actual engine scenario: {type(exc).__name__}\n")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output_json.open("xb") as out:
            out.write(encoded)
    except FileExistsError:
        parser.exit(2, "refusing to overwrite an existing report or evidence file\n")
    print(json.dumps({
        "status": "UNVERIFIED_ENGINE_SLOT_MAP_PREPARATION_ONLY",
        "review_rows": len(report["rows"]),
        "automatic_slot_bindings_created": 0,
    }))


if __name__ == "__main__":
    main()
