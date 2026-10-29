"""Run REAL production simulator and optionally align its slots to local review.

Research-only: a reproducible local engine execution is NOT evidence that
the input scenario reconstructs a Gameforge battle. The physical address
map is explicitly user-asserted, not game-authenticated. Engine HP is not
assumed equivalent to the screenshot's HP bar.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from ikariam_battle import simulate
from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_manual_visual_review as manual

SCHEMA = "p0_real_engine_snapshot_handoff_v1"
MAP_SCHEMA = "p0_real_engine_slot_map_v1"
MAX_JSON_BYTES = 64 * 1024 * 1024
SOURCE = "EXECUTED_CURRENT_PRODUCTION_ENGINE_HYPOTHETICAL_SCENARIO"
SIDES = ("attacker", "defender")


def _bytes_json(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def engine_trace(scenario_bytes: bytes) -> dict:
    """Call the actual ikariam_battle.simulate, never handcraft outcomes."""
    scenario = json.loads(scenario_bytes)
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a JSON object")
    outcome = simulate(scenario)
    if not isinstance(outcome, dict):
        raise ValueError("engine did not return a result object")
    rounds = outcome.get("rounds")
    if not isinstance(rounds, list):
        raise ValueError("engine result has no round snapshots")
    engine_path = Path(__file__).resolve().parents[2] / "ikariam_battle" / "engine.py"
    # A preserved snapshot at an unsupported mechanic boundary is not
    # a completed model round, even when its numeric round is >0.
    unsupported = [
        {"round": e.get("round"), "phase": e.get("phase"),
         "rule_id": (e.get("details") or {}).get("rule_id")}
        for e in outcome.get("events", []) if e.get("type") == "unsupported_mechanic"
    ]
    blocked_rounds = {e["round"] for e in unsupported}
    snapshots = []
    for round_state in rounds:
        number = round_state.get("round")
        if type(number) is not int or number < 0:
            raise ValueError("engine emitted invalid round")
        for side in SIDES:
            slots = round_state.get(side, {}).get("slots", [])
            if not isinstance(slots, list):
                raise ValueError("engine emitted invalid slot array")
            for s in slots:
                fields = ("slot_id", "unit_id", "wave_id", "line",
                          "physical_position", "damage_position", "units",
                          "damage", "hit_points_percent", "casualties")
                if not isinstance(s, dict) or any(k not in s for k in fields):
                    raise ValueError("engine slot projection fields unavailable")
                snapshots.append({
                    "engine_round": number,
                    "engine_phase": (
                        "initial" if number == 0 else
                        "unsupported_boundary_not_round_end"
                        if number in blocked_rounds else "round_end_model_snapshot"
                    ),
                    "side": side,
                    **{key: s[key] for key in fields},
                })
    return {
        "schema": SCHEMA,
        "source_class": SOURCE,
        "scenario_sha256": sha256(scenario_bytes).hexdigest(),
        "engine_file_sha256": sha256(engine_path.read_bytes()).hexdigest(),
        "engine_output_sha256": sha256(_bytes_json(outcome)).hexdigest(),
        "scenario_battlefield": scenario.get("battlefield"),
        # Actual deployment geometry may differ from requested battlefield
        # when a garrison/open-field condition selects land-max.
        "engine_effective_battlefield": (
            (outcome.get("garrison_status") or {}).get("effective_battlefield")
            or scenario.get("battlefield")
        ),
        "engine_policy": outcome.get("policy"),
        "engine_status": outcome.get("status"),
        "engine_rounds_completed": outcome.get("rounds_completed"),
        "engine_applied_assumptions": outcome.get("assumptions", []),
        "engine_warnings": outcome.get("warnings", []),
        "engine_unsupported_events": unsupported,
        "engine_slots": snapshots,
        "engine_execution_recorded": True,
        "scenario_reconstructed_from_original_game": False,
        "original_game_screenshots_authenticated": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "model_calibration_verified": False,
    }


def compare_to_captures(
    trace: dict, case_bytes: bytes, manifest: dict, evidence_root: Path,
    review_bytes: bytes, mapping: dict,
) -> dict:
    """Strict opt-in slot map. No guessed round offsets or inferred Wave IDs."""
    case = binder._inspect_case(case_bytes)
    if case is None:
        raise ValueError("invalid browser case")
    review = manual.assess_review(
        case_bytes, manifest, evidence_root, json.loads(review_bytes)
    )
    case_obj = json.loads(case_bytes)
    if trace["scenario_battlefield"] != case_obj["battlefield"]:
        raise ValueError("different requested model and case battlefield IDs")
    if trace["engine_effective_battlefield"] != case_obj["battlefield"]:
        # The same number cannot represent the same physical slot across
        # land-mini and land-max geometry. Stop *before* reading a map.
        raise ValueError("effective engine deployment battlefield differs from case")
    if not isinstance(mapping, dict) or set(mapping) != {
        "schema", "case_id", "case_sha256", "scenario_sha256", "bindings"
    } or mapping["schema"] != MAP_SCHEMA:
        raise ValueError("invalid explicit slot-map manifest")
    if (mapping["case_id"] != case_obj["id"] or
        mapping["case_sha256"] != sha256(case_bytes).hexdigest() or
        mapping["scenario_sha256"] != trace["scenario_sha256"]):
        raise ValueError("slot-map source hashes do not match")
    bindings = mapping["bindings"]
    if not isinstance(bindings, list) or len(bindings) > len(review["review_items"]):
        raise ValueError("invalid slot binding count")
    # Binding rows refer to the exact canonical review item index. No
    # assumption is made that the model's wave label means the user's Wave.
    images = {r["id"]: r for r in case_obj["rounds"]}
    seen: set[int] = set()
    matched = []
    for row in bindings:
        if not isinstance(row, dict) or set(row) != {
            "review_item_index", "target_capture_id", "engine_round",
            "side", "line", "physical_position", "engine_wave_id"
        }:
            raise ValueError("slot binding must include all explicit fields")
        i = row["review_item_index"]
        if type(i) is not int or i < 0 or i >= len(review["review_items"]) or i in seen:
            raise ValueError("unknown or duplicate review row")
        seen.add(i)
        item = review["review_items"][i]
        if (row["target_capture_id"] != item["target_capture_id"] or
            row["side"] != item["side"] or row["line"] != item["line"] or
            row["physical_position"] != item["physical_position"] or
            type(row["engine_round"]) is not int or
            row["engine_round"] != item["target_round"]):
            raise ValueError("model slot address/round/capture must equal recorded review item")
        snapshot = images.get(row["target_capture_id"])
        if snapshot is None:
            raise ValueError("missing target captured round")
        matches = [s for s in trace["engine_slots"] if (
            s["engine_round"] == row["engine_round"]
            and s["side"] == row["side"]
            and s["line"] == row["line"]
            and s["physical_position"] == row["physical_position"]
            and s["wave_id"] == row["engine_wave_id"]
        )]
        if len(matches) > 1:
            raise ValueError("ambiguous model wave/physical position")
        model = matches[0] if matches else None
        reason = None
        if snapshot["phase"] != "round_end":
            reason = "GAME_CAPTURE_NOT_ROUND_END"
        elif (item["reviewer_reported_status"] !=
              "REVIEWER_REPORTS_IMAGES_READABLE"):
            reason = "NO_READABLE_USER_REVIEW"
        elif item["round_number_gap"] != 1 or not item["same_capture_phase"]:
            reason = "UNOBSERVED_ROUND_OR_PHASE_MISMATCH"
        elif any(e["round"] is None or e["round"] <= row["engine_round"]
                 for e in trace["engine_unsupported_events"]):
            reason = "ENGINE_UNSUPPORTED_MECHANIC_BOUNDARY"
        elif model is None or row["engine_round"] == 0:
            reason = "ENGINE_ROUND_OR_SLOT_NOT_AVAILABLE"
        elif item["review_reason"] in ("NO_ENTERED_VISIBLE_SLOTS", "LABEL_CHANGED"):
            reason = "UNSTABLE_TARGET_IDENTITY"
        elif item["review_reason"] != "INCOMPLETE":
            # A physical target without an earlier matching address cannot
            # support even a scoped target-count diagnostic.
            reason = "TYPED_PAIR_NOT_CONTINUOUSLY_COMPARABLE"
        elif _target_slot(case_obj, row) is None:
            reason = "TARGET_TYPED_SLOT_NOT_FOUND"
        elif (
            _target_slot(case_obj, row)["unit"] != model["unit_id"]
            or _target_slot(case_obj, row)["wave"] != model["wave_id"]
        ):
            # No inferred user-Wave -> engine-Wave equivalence permitted.
            reason = "MODEL_UNIT_OR_WAVE_DIFFERS_FROM_TYPED_TARGET"
        elif _earlier_labels_conflict(case_obj, item, row):
            reason = "EARLIER_UNIT_OR_WAVE_MISSING_OR_CHANGED"
        elif type(_target_slot(case_obj, row)["count"]) is not int:
            reason = "TARGET_TYPED_COUNT_INCOMPLETE"
        elif type(model["units"]) is not int or model["units"] < 0:
            reason = "MODEL_SLOT_COUNT_UNAVAILABLE"
        else:
            # This is a NUMERICAL DIAGNOSTIC, not Gameforge validation.
            # The explicit user map, readable claim and complete typed
            # target alone do not prove the scenario or screenshot.
            reason = None
        matched.append({
            "review_item_index": i,
            "target_capture_id": row["target_capture_id"],
            "engine_round": row["engine_round"],
            "side": row["side"], "line": row["line"],
            "physical_position": row["physical_position"],
            "engine_wave_id": row["engine_wave_id"],
            "engine_slot_found": model is not None,
            "engine_unit_id": model["unit_id"] if model else None,
            "engine_units": model["units"] if model else None,
            "engine_hp_metric_percent": (
                model["hit_points_percent"] if model else None
            ),
            "engine_hp_metric_not_game_ui_bar": True,
            "user_reported_review_status": item["reviewer_reported_status"],
            "diagnostic_status": (
                "ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED"
                if reason is None else "NOT_ASSESSABLE_" + reason
            ),
            "count_difference": (
                model["units"] - _target_slot(case_obj, row)["count"]
                if reason is None else None
            ),
            "hp_percentage_point_difference": None,
            "game_mechanism_verified": False,
        })
    return {
        "schema": "p0_real_engine_vs_report_capture_alignment_v1",
        "source_class": SOURCE,
        "scenario_sha256": trace["scenario_sha256"],
        "engine_output_sha256": trace["engine_output_sha256"],
        "case_sha256": sha256(case_bytes).hexdigest(),
        "review_worksheet_sha256": sha256(review_bytes).hexdigest(),
        "bindings": matched,
        "engine_executed": True,
        "physical_slot_and_wave_mapping_user_asserted": True,
        "original_game_screenshots_authenticated": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "model_calibration_verified": False,
        "notes": [
            "Actual current engine simulated the supplied scenario; not a Gameforge battle replay.",
            "Explicit slot map only locates model snapshots, never certifies the game round origin.",
            "Engine aggregate slot HP percent is NOT established equal to Gameforge UI HP bar.",
            "No numeric differences produced until independent source and wave semantics verified.",
        ],
    }


def _target_slot(case: dict, row: dict) -> dict | None:
    for capture in case["rounds"]:
        if capture["id"] == row["target_capture_id"]:
            for s in capture[row["side"]]["slots"]:
                if s["line"] == row["line"] and s["pos"] == row["physical_position"]:
                    return s
    return None


def _earlier_labels_conflict(case: dict, item: dict, row: dict) -> bool:
    target = _target_slot(case, row)
    if target is None:
        return True
    for capture in case["rounds"]:
        if capture["id"] == item["earlier_capture_id"]:
            for s in capture[row["side"]]["slots"]:
                if s["line"] == row["line"] and s["pos"] == row["physical_position"]:
                    # Missing labels are UNKNOWN, not evidence of a
                    # continuous identical Wave. Require both earlier
                    # labels to be nonblank and exactly equal.
                    return bool(
                        not s["unit"] or not s["wave"]
                        or s["unit"] != target["unit"]
                        or s["wave"] != target["wave"]
                    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--review-worksheet", type=Path)
    parser.add_argument("--slot-map", type=Path)
    args = parser.parse_args()
    extra = [args.case, args.manifest, args.evidence_root,
             args.review_worksheet, args.slot_map]
    if any(x is not None for x in extra) and not all(x is not None for x in extra):
        parser.error("slot alignment requires --case --manifest --evidence-root --review-worksheet --slot-map together")
    try:
        scenario = binder._read_limited(args.scenario, MAX_JSON_BYTES)
        trace = engine_trace(scenario)
        if all(x is not None for x in extra):
            value = {
                "engine_execution": trace,
                "capture_alignment": compare_to_captures(
                    trace,
                    binder._read_limited(args.case, binder.MAX_CASE_BYTES),
                    json.loads(binder._read_limited(args.manifest, binder.MAX_MANIFEST_BYTES)),
                    args.evidence_root,
                    binder._read_limited(args.review_worksheet, manual.MAX_REVIEW_BYTES),
                    json.loads(binder._read_limited(args.slot_map, MAX_JSON_BYTES)),
                ),
            }
        else:
            value = {"engine_execution": trace, "capture_alignment": None}
        encoded = _bytes_json(value) + b"\n"
        if len(encoded) > MAX_JSON_BYTES:
            raise ValueError("engine report exceeds output size limit")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        parser.exit(2, f"rejected scenario or slot binding: {type(exc).__name__}\n")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.output_json.open("xb") as out:
            out.write(encoded)
    except FileExistsError:
        parser.exit(2, "refusing to overwrite original evidence or earlier trace\n")
    print(json.dumps({
        "status": "ACTUAL_ENGINE_RUN_HYPOTHETICAL_NOT_GAME_VERIFIED",
        "matched_bindings": (
            len(value["capture_alignment"]["bindings"])
            if value["capture_alignment"] else 0
        ),
    }))


if __name__ == "__main__":
    main()
