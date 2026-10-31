"""Read-only multi-round actual-engine comparison of source-typed partial captures.

Calls the exact existing focused diagnostic for each selected source capture;
each invocation runs the real simulator and revalidates original local source
bytes, reviewer assertions and explicit engine Wave/slot mappings. No model
mechanics are inferred from observed changes, and no snapshots are filled in.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tools.research import p0_report_case_focused_engine_diagnostic as focused
from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_manual_visual_review as manual
from tools.research import p0_report_case_real_engine_trace as engine

SCHEMA = "p0_multi_round_actual_engine_capture_diagnostic_v1"
STATUS = "DESCRIPTIVE_MULTI_ROUND_HYPOTHESIS_NOT_GAME_CALIBRATION"
MAX_CAPTURES = 10
ELIGIBLE = "ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED"
PROVENANCE_KEYS = (
    "case_sha256", "scenario_sha256", "engine_source_sha256",
    "engine_output_sha256", "review_worksheet_sha256", "case_id", "side",
    "line", "engine_policy", "source_class",
)
NO_MECHANISM_INFERENCE = (
    "Casualties, damage, healing, reserve handoff, accuracy, identity "
    "continuity across rounds and actual game mechanics are NOT inferred."
)


def _pair(prior: dict, later: dict) -> dict:
    """Compare two prevalidated source-capture projections without extrapolation."""
    if prior["side"] != later["side"] or prior["line"] != later["line"]:
        raise ValueError("capture projections disagree on selected side or line")
    for key in PROVENANCE_KEYS:
        if prior[key] != later[key]:
            raise ValueError("capture projections disagree on evidence/engine provenance")
    gap = later["capture_round"] - prior["capture_round"]
    if gap <= 0:
        raise ValueError("captured rounds must be strictly increasing")
    left = {r["physical_position"]: r for r in prior["rows"]}
    right = {r["physical_position"]: r for r in later["rows"]}
    if len(left) != len(prior["rows"]) or len(right) != len(later["rows"]):
        raise ValueError("duplicated physical address in focused projection")
    rows = []
    comparable = 0
    # Only positions typed in at least one capture. No new/empty slots invented.
    for position in sorted(left.keys() | right.keys()):
        a, b = left.get(position), right.get(position)
        state = None
        if gap != 1:
            state = "NOT_ASSESSABLE_MISSING_INTERVENING_CAPTURE_ROUNDS"
        elif a is None or b is None:
            state = "NOT_ASSESSABLE_TYPED_POSITION_MISSING_IN_ONE_CAPTURE"
        elif a["count_comparison_status"] != ELIGIBLE or b["count_comparison_status"] != ELIGIBLE:
            state = "NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE"
        elif not all(
            isinstance(row.get("typed_unit_label"), str)
            and row["typed_unit_label"].strip()
            and isinstance(row.get("typed_wave_label"), str)
            and row["typed_wave_label"].strip()
            for row in (a, b)
        ):
            # Source labels containing only whitespace are UNKNOWN, even
            # when the user typed the same whitespace in both captures.
            state = "NOT_ASSESSABLE_INCOMPLETE_TYPED_WAVE_IDENTITY"
        elif not all(
            isinstance(row.get("engine_unit_id"), str)
            and row["engine_unit_id"].strip()
            and isinstance(row.get("engine_wave_id_user_asserted"), str)
            and row["engine_wave_id_user_asserted"].strip()
            for row in (a, b)
        ):
            # An explicitly asserted model Wave that is merely whitespace
            # is not proof of stable identity across snapshots either.
            state = "NOT_ASSESSABLE_INCOMPLETE_ENGINE_WAVE_IDENTITY"
        elif (
            a["typed_unit_label"] != b["typed_unit_label"]
            or a["typed_wave_label"] != b["typed_wave_label"]
            or a["engine_wave_id_user_asserted"] != b["engine_wave_id_user_asserted"]
            or a["engine_unit_id"] != b["engine_unit_id"]
        ):
            state = "NOT_ASSESSABLE_DIFFERENT_WAVE_OR_UNIT_IDENTITY"
        elif not all(
            type(row["typed_count"]) is int
            and type(row["engine_count_context_only"]) is int
            and type(row["engine_minus_typed_count"]) is int
            for row in (a, b)
        ):
            raise ValueError("eligible count comparison missing exact integer data")
        else:
            state = "DESCRIPTIVE_COUNT_CHANGES_ONLY_NOT_CAUSAL"
            comparable += 1
        observed_delta = b["typed_count"] - a["typed_count"] if state == (
            "DESCRIPTIVE_COUNT_CHANGES_ONLY_NOT_CAUSAL"
        ) else None
        engine_delta = b["engine_count_context_only"] - a["engine_count_context_only"] if (
            observed_delta is not None
        ) else None
        rows.append({
            "physical_position": position,
            "comparison_status": state,
            "earlier_typed_position_present": a is not None,
            "later_typed_position_present": b is not None,
            "earlier_eligibility_status": a["count_comparison_status"] if a else None,
            "later_eligibility_status": b["count_comparison_status"] if b else None,
            "earlier_typed_count": a["typed_count"] if a else None,
            "later_typed_count": b["typed_count"] if b else None,
            "earlier_engine_count_context_only": a["engine_count_context_only"] if a else None,
            "later_engine_count_context_only": b["engine_count_context_only"] if b else None,
            "typed_count_change": observed_delta,
            "engine_count_change": engine_delta,
            "engine_minus_typed_change": (
                engine_delta - observed_delta if observed_delta is not None else None
            ),
            "hp_or_casualty_mechanism_inferred": False,
        })
    return {
        "earlier_capture_id": prior["capture_id"],
        "later_capture_id": later["capture_id"],
        "earlier_round": prior["capture_round"],
        "later_round": later["capture_round"],
        "round_number_gap": gap,
        "adjacent_rounds_only": gap == 1,
        "descriptive_change_comparisons": comparable,
        "rows": rows,
    }



# These categories describe agreement or disagreement between two sets of
# typed NUMBERS only. They are not a battle-model accuracy or damage verdict.
SUMMARY_SCHEMA = "p0_multi_round_difference_evidence_summary_v1"
COMPARABLE_STATUS = "DESCRIPTIVE_COUNT_CHANGES_ONLY_NOT_CAUSAL"
NUMERIC_SAME = "NUMERIC_CHANGE_EQUAL_UNVERIFIED"
NUMERIC_ABOVE = "NUMERIC_ENGINE_CHANGE_ABOVE_TYPED_UNVERIFIED"
NUMERIC_BELOW = "NUMERIC_ENGINE_CHANGE_BELOW_TYPED_UNVERIFIED"
UNKNOWN_REASONS = frozenset({
    "NOT_ASSESSABLE_MISSING_INTERVENING_CAPTURE_ROUNDS",
    "NOT_ASSESSABLE_TYPED_POSITION_MISSING_IN_ONE_CAPTURE",
    "NOT_ASSESSABLE_SOURCE_OR_ENGINE_MAPPING_GATE",
    "NOT_ASSESSABLE_INCOMPLETE_TYPED_WAVE_IDENTITY",
    "NOT_ASSESSABLE_INCOMPLETE_ENGINE_WAVE_IDENTITY",
    "NOT_ASSESSABLE_DIFFERENT_WAVE_OR_UNIT_IDENTITY",
})
COUNT_FIELDS = (
    "typed_count_change", "engine_count_change", "engine_minus_typed_change",
)


def _evidence_category(row: dict) -> str:
    """Classify an existing source-gated row; never create its numbers."""
    status = row.get("comparison_status")
    if status in UNKNOWN_REASONS:
        if any(row.get(key) is not None for key in COUNT_FIELDS):
            raise ValueError("unassessable row must have null numeric changes")
        return status
    if status != COMPARABLE_STATUS:
        raise ValueError("unknown comparison status is not evidence")
    if any(type(row.get(key)) is not int for key in COUNT_FIELDS):
        raise ValueError("eligible row must have three exact integer changes")
    observed, simulated, residual = (row[key] for key in COUNT_FIELDS)
    if simulated - observed != residual:
        raise ValueError("numeric change difference does not reconcile")
    if residual == 0:
        return NUMERIC_SAME
    return NUMERIC_ABOVE if residual > 0 else NUMERIC_BELOW


def summarize_evidence(pairs: list[dict]) -> dict:
    """Produce audited counts per captured pair, not a global accuracy score.

    Each physical slot at each source-capture pair is one *descriptive row*.
    Repeated positions between pairs are not independent held-out evidence.
    """
    all_counts: dict[str, int] = {}
    pair_summaries = []
    total_rows = 0
    eligible_rows = 0
    for pair in pairs:
        counts: dict[str, int] = {}
        rows = pair["rows"]
        if not isinstance(rows, list):
            raise ValueError("pair has invalid comparison rows")
        if pair["descriptive_change_comparisons"] < 0:
            raise ValueError("invalid pair eligible count")
        for row in rows:
            category = _evidence_category(row)
            # The status is preserved for audit; the added category permits
            # grouping while leaving both original count changes intact.
            row["evidence_category"] = category
            counts[category] = counts.get(category, 0) + 1
            all_counts[category] = all_counts.get(category, 0) + 1
            total_rows += 1
            if category in (NUMERIC_SAME, NUMERIC_ABOVE, NUMERIC_BELOW):
                eligible_rows += 1
        comparable = sum(counts.get(c, 0) for c in (NUMERIC_SAME, NUMERIC_ABOVE, NUMERIC_BELOW))
        if comparable != pair["descriptive_change_comparisons"]:
            raise ValueError("pair's numeric comparison count does not reconcile")
        pair_summaries.append({
            "earlier_capture_id": pair["earlier_capture_id"],
            "later_capture_id": pair["later_capture_id"],
            "earlier_round": pair["earlier_round"],
            "later_round": pair["later_round"],
            "round_number_gap": pair["round_number_gap"],
            "typed_position_pairs": len(rows),
            "descriptive_numeric_change_rows": comparable,
            "unassessable_rows": len(rows) - comparable,
            "category_counts": dict(sorted(counts.items())),
        })
    if total_rows != sum(all_counts.values()):
        raise ValueError("summary category counts do not reconcile")
    return {
        "schema": SUMMARY_SCHEMA,
        "status": "DESCRIPTIVE_TYPED_POSITION_COVERAGE_NOT_MODEL_ACCURACY",
        "capture_pairs_count": len(pairs),
        "typed_position_pair_rows": total_rows,
        "descriptive_numeric_change_rows": eligible_rows,
        "unassessable_rows": total_rows - eligible_rows,
        "numeric_change_equal_rows": all_counts.get(NUMERIC_SAME, 0),
        "numeric_engine_change_above_typed_rows": all_counts.get(NUMERIC_ABOVE, 0),
        "numeric_engine_change_below_typed_rows": all_counts.get(NUMERIC_BELOW, 0),
        "category_counts": dict(sorted(all_counts.items())),
        "pair_summaries": pair_summaries,
        "denominator_is_typed_slot_pair_rows_not_complete_battle": True,
        "cross_pair_rows_are_not_independent_holdouts": True,
        "descriptive_zero_residual_is_not_model_verification": True,
        "battle_causality_or_calibration_verified": False,
        "notes": [
            "Only already source-gated and explicitly Wave-mapped count-change rows are numerically classified.",
            "All unassessable source gaps or identities stay in separate categories; never silently drop them from coverage.",
            "Equal numerical count changes do not prove Gameforge mechanics, casualties, or independent source authenticity.",
            "Repeated typed positions across pairs are correlated; no precision, recall, accuracy percentage, HP or healing score is calculated.",
        ],
    }


def multi_round_diagnostic(
    scenario_bytes: bytes,
    case_bytes: bytes,
    manifest: dict,
    evidence_root: Path,
    review_bytes: bytes,
    slot_map: dict,
    *,
    capture_ids: list[str],
    side: str,
    line: str,
) -> dict:
    """Validate the selected ordered captures and re-run each strict P0 gate."""
    if (
        not isinstance(capture_ids, list)
        or not 2 <= len(capture_ids) <= MAX_CAPTURES
        or any(not isinstance(i, str) or not i for i in capture_ids)
        or len(set(capture_ids)) != len(capture_ids)
    ):
        raise ValueError("capture IDs must be 2-10 unique, nonempty, ordered case IDs")
    # Validate selection *before* running an expensive engine for every capture.
    if binder._inspect_case(case_bytes) is None:
        raise ValueError("invalid canonical browser case or Node unavailable")
    case = json.loads(case_bytes)
    indexed = {r["id"]: r for r in case["rounds"]}
    if any(i not in indexed for i in capture_ids):
        raise ValueError("selected source capture ID not found")
    rounds = [indexed[i]["number"] for i in capture_ids]
    if any(b <= a for a, b in zip(rounds, rounds[1:])):
        raise ValueError("capture selection must be in increasing numeric round order")
    if side not in engine.SIDES or line not in focused.LINES:
        raise ValueError("invalid selected side or line")
    projections = [
        focused.focused_diagnostic(
            scenario_bytes, case_bytes, manifest, evidence_root,
            review_bytes, slot_map, capture_id=capture_id, side=side, line=line,
        )
        for capture_id in capture_ids
    ]
    for capture_id, round_number, projection in zip(capture_ids, rounds, projections):
        if (
            projection["schema"] != focused.SCHEMA
            or projection["source_class"] != engine.SOURCE
            or projection["capture_id"] != capture_id
            or projection["capture_round"] != round_number
            or projection["capture_phase"] != "round_end"
            or projection["side"] != side or projection["line"] != line
            or projection["game_source_authenticated"] is not False
            or projection["global_calibration_allowed"] is not False
            or projection["hp_bar_comparison_performed"] is not False
            or projection["engine_output_sha256"] is None
            or projection["case_sha256"] != sha256(case_bytes).hexdigest()
        ):
            raise ValueError("focused projection violated strict source gate")
    if any(
        any(p[k] != projections[0][k] for k in PROVENANCE_KEYS)
        for p in projections[1:]
    ):
        raise ValueError("selected projections disagree on engine/evidence digests")
    pairs = [_pair(a, b) for a, b in zip(projections, projections[1:])]
    evidence_summary = summarize_evidence(pairs)
    if evidence_summary["descriptive_numeric_change_rows"] != sum(
        p["descriptive_change_comparisons"] for p in pairs
    ):
        raise ValueError("evidence summary does not match gated comparisons")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_class": engine.SOURCE,
        "case_sha256": projections[0]["case_sha256"],
        "scenario_sha256": projections[0]["scenario_sha256"],
        "engine_source_sha256": projections[0]["engine_source_sha256"],
        "engine_output_sha256": projections[0]["engine_output_sha256"],
        "review_worksheet_sha256": projections[0]["review_worksheet_sha256"],
        "case_id": projections[0]["case_id"],
        "side": side,
        "line": line,
        "capture_ids": list(capture_ids),
        "captured_rounds": rounds,
        "strictly_adjacent_pairs": sum(p["adjacent_rounds_only"] for p in pairs),
        "descriptive_change_comparisons": sum(
            p["descriptive_change_comparisons"] for p in pairs
        ),
        "capture_projections": projections,
        "round_pairs": pairs,
        "comparison_evidence_summary": evidence_summary,
        "actual_current_engine_executed": True,
        "number_of_engine_executions": len(projections),
        "unentered_positions_or_rounds_invented": False,
        "original_game_screenshots_authenticated": False,
        "scenario_reconstructed_from_game": False,
        "physical_wave_mapping_independently_verified": False,
        "hp_bar_comparison_performed": False,
        "casualty_damage_healing_or_reserve_mechanism_inferred": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "global_calibration_allowed": False,
        "note": NO_MECHANISM_INFERENCE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--review-worksheet", type=Path, required=True)
    parser.add_argument("--slot-map", type=Path, required=True)
    parser.add_argument("--capture-id", dest="capture_ids", action="append", required=True)
    parser.add_argument("--side", choices=engine.SIDES, required=True)
    parser.add_argument("--line", choices=focused.LINES, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = multi_round_diagnostic(
            binder._read_limited(args.scenario, engine.MAX_JSON_BYTES),
            binder._read_limited(args.case, binder.MAX_CASE_BYTES),
            json.loads(binder._read_limited(args.manifest, binder.MAX_MANIFEST_BYTES)),
            args.evidence_root,
            binder._read_limited(args.review_worksheet, manual.MAX_REVIEW_BYTES),
            json.loads(binder._read_limited(args.slot_map, engine.MAX_JSON_BYTES)),
            capture_ids=args.capture_ids, side=args.side, line=args.line,
        )
        payload = engine._bytes_json(value) + b"\n"
        if len(payload) > engine.MAX_JSON_BYTES:
            raise ValueError("multi-round report exceeds output size limit")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"rejected multi-round engine diagnostic: {type(exc).__name__}\n")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output_json.open("xb") as output:
            output.write(payload)
    except FileExistsError:
        parser.exit(2, "refusing to overwrite prior diagnostic or source evidence\n")
    print(json.dumps({
        "status": STATUS,
        "source_captures": len(value["capture_ids"]),
        "adjacent_pairs": value["strictly_adjacent_pairs"],
        "descriptive_change_comparisons": value["descriptive_change_comparisons"],
        "game_mechanics_verified": False,
    }))


if __name__ == "__main__":
    main()
