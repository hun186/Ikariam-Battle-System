"""Rank local research case reports by missing-evidence work; NOT model accuracy.

Offline consumer of explicitly supplied previous multi-round JSON reports. It
recomputes internal category arithmetic but DOES NOT rerun the simulator,
re-hash screenshots, authenticate Gameforge captures or prove the reports'
origins. Use the source-gated live CLI to generate each fresh input first.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_multi_round_engine_diagnostic as multi
from tools.research import p0_report_case_real_engine_trace as engine

SCHEMA = "p0_multi_case_research_evidence_triage_index_v1"
MAX_REPORTS = 20
MAX_INPUT_BYTES = engine.MAX_JSON_BYTES


def rank_report_bytes(reports: list[bytes]) -> dict:
    """Internally reconcile supplied report JSON; never attest its provenance."""
    if not isinstance(reports, list) or not 1 <= len(reports) <= MAX_REPORTS:
        raise ValueError("requires 1-20 existing local research reports")
    rows = []
    seen = set()
    for raw in reports:
        if type(raw) is not bytes or not raw or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("input report bytes missing or excessive")
        report = json.loads(raw)
        if not isinstance(report, dict) or report.get("schema") != multi.SCHEMA:
            raise ValueError("expected prior multi-round diagnostic schema")
        if (
            report.get("actual_current_engine_executed") is not True
            or report.get("original_game_screenshots_authenticated") is not False
            or report.get("global_calibration_allowed") is not False
            or report.get("independent_holdouts") != 0
            or report.get("hp_bar_comparison_performed") is not False
        ):
            raise ValueError("input report violates non-calibration provenance flags")
        pairs = report.get("round_pairs")
        if not isinstance(pairs, list) or not 1 <= len(pairs) <= multi.MAX_CAPTURES - 1:
            raise ValueError("invalid source-capture pair collection")
        # Recompute FROM the included row values and statuses rather than
        # believing cached summary/triage fields in a user-provided report.
        rebuilt = multi.summarize_evidence(pairs)
        if rebuilt != report.get("comparison_evidence_summary"):
            raise ValueError("input source report has inconsistent category summary")
        triage = multi.build_research_triage(pairs, rebuilt)
        if triage != report.get("research_evidence_triage"):
            raise ValueError("input source report has inconsistent triage")
        case_id = report.get("case_id")
        case_hash = report.get("case_sha256")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("source case id is unknown")
        if not isinstance(case_hash, str) or len(case_hash) != 64 or any(
            x not in "0123456789abcdef" for x in case_hash
        ):
            raise ValueError("source case hash is invalid")
        if case_hash in seen:
            raise ValueError("duplicate source case SHA cannot be ranked twice")
        seen.add(case_hash)
        if report.get("descriptive_count_comparisons") != rebuilt[
            "descriptive_numeric_change_rows"
        ]:
            raise ValueError("source diagnostic and summary comparable counts differ")
        rows.append({
            "case_id": case_id,
            "case_sha256_user_reported_binding": case_hash,
            "local_report_bytes_sha256": sha256(raw).hexdigest(),
            "readiness_not_accuracy": triage["readiness_not_accuracy"],
            "source_capture_pair_count": triage["source_capture_pair_count"],
            "typed_position_pair_rows": triage["typed_position_pair_rows"],
            "descriptive_numeric_change_rows": triage["descriptive_numeric_change_rows"],
            "unassessable_rows": triage["unassessable_rows"],
            "priority_order_not_accuracy_score": triage[
                "case_priority_derived_from_first_action_only"
            ],
            "next_manual_action_code": (
                triage["manual_evidence_actions"][0]["recommended_manual_action_code"]
                if triage["manual_evidence_actions"] else None
            ),
        })
    # Never order by a synthetic residual magnitude or a fabricated fit rate.
    # A missing source-round block should be acquired before fine comparisons.
    rows.sort(key=lambda row: (
        row["priority_order_not_accuracy_score"]
        if row["priority_order_not_accuracy_score"] is not None else 99,
        row["case_sha256_user_reported_binding"],
    ))
    for i, row in enumerate(rows, 1):
        row["evidence_acquisition_queue_position_not_research_quality_rank"] = i
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_SELF_REPORTED_EVIDENCE_TRIAGE_NOT_GAME_AUTHENTICATION",
        "number_of_local_report_inputs": len(reports),
        "ranked_case_tasks": rows,
        "source_reports_recomputed_for_internal_consistency": True,
        "production_engine_or_image_bytes_revalidated_during_index": False,
        "screenshot_file_paths_or_original_content_exported": False,
        "original_game_sources_independently_authenticated": False,
        "model_accuracy_or_mechanism_verified": False,
        "ranking_is_a_manual_source_acquisition_queue_not_model_quality": True,
        "warning": (
            "Supplied JSON can be forged despite internally valid counters or hashes. "
            "Re-run source-image/reviewer/engine gates and obtain independent Gameforge "
            "captures before drawing any battle or calibration conclusion."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not 1 <= len(args.report) <= MAX_REPORTS:
            raise ValueError("requires 1-20 input reports")
        total = 0
        blobs = []
        for path in args.report:
            remaining = MAX_INPUT_BYTES - total
            if remaining <= 0:
                raise ValueError("aggregate report data exceeds 64 MiB")
            raw = binder._read_limited(path, remaining)
            total += len(raw)
            blobs.append(raw)
        result = rank_report_bytes(blobs)
        output = engine._bytes_json(result) + b"\n"
        if len(output) > engine.MAX_JSON_BYTES:
            raise ValueError("index report too large")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"rejected research index: {type(exc).__name__}\n")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output_json.open("xb") as out:
            out.write(output)
    except FileExistsError:
        parser.exit(2, "refusing to overwrite existing evidence index\n")
    print(json.dumps({
        "status": result["status"],
        "ranked_local_reports": len(result["ranked_case_tasks"]),
        "model_accuracy_verified": False,
    }))


if __name__ == "__main__":
    main()
