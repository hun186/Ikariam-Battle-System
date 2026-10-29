"""Source-anchored model CANDIDATE vs typed capture diagnostic; never calibration.

Candidate predictions are USER-ENTERED projections, NOT attested engine output.
Only full adjacent same-phase typed target snapshots with readable-image
USER REPORTS may receive descriptive discrepancies. None are verified Gameforge
observations, target shots, reserve mechanics, or independent holdouts.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from tools.research import p0_report_case_local_image_binding as binder
from tools.research import p0_report_case_manual_visual_review as manual

SCHEMA = "p0_report_case_model_candidate_worksheet_v1"
REPORT_SCHEMA = "p0_report_case_model_candidate_diagnostic_v1"
MAX_WORKSHEET_BYTES = 64 * 1024 * 1024
USER_MODEL_SOURCE = "USER_ENTERED_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED"
MODEL_FIELDS = {
    "predicted_target_unit", "predicted_target_wave",
    "predicted_target_count", "predicted_target_hp_percent",
}
NODE_TARGET_SNAPSHOTS = r"""
const fs=require('node:fs');
const M=require(process.argv[1]);
try{
 const c=JSON.parse(fs.readFileSync(0,'utf8'));
 const pairs=M.summarizeCapturedTimeline(c);
 const out=[];
 for(const p of pairs){
   const comparison=M.compareCapturedRounds(c,p.targetId,p.sourceId);
   const pending=comparison.rows.length
      ? comparison.rows.filter(r=>r.code!=='FIELDS_COMPARABLE')
      : [{code:'NO_ENTERED_VISIBLE_SLOTS',side:null,line:null,pos:null,current:null}];
   for(const r of pending){
      out.push({
        earlier_capture_id:p.sourceId,target_capture_id:p.targetId,
        earlier_round:p.sourceRound,target_round:p.targetRound,
        round_number_gap:p.roundNumberGap,same_capture_phase:p.samePhase,
        side:r.side,line:r.line,physical_position:r.pos,
        review_reason:r.code,
        target_typed_unit:r.current?.unit??null,
        target_typed_wave:r.current?.wave??null,
        target_typed_count:r.current?.count??null,
        target_typed_hp_percent:r.current?.hp??null
      });
   }
 }
 process.stdout.write(JSON.stringify(out));
}catch(e){process.stderr.write('invalid canonical model comparison');process.exit(2);}
"""


def _target_snapshots(case_bytes: bytes) -> list[dict]:
    model = Path(binder.__file__).resolve().parents[2] / "battle-cases-model.js"
    try:
        completed = subprocess.run(
            ["node", "-e", NODE_TARGET_SNAPSHOTS, str(model)],
            input=case_bytes, capture_output=True, check=False, timeout=25,
        )
        if completed.returncode != 0:
            raise ValueError("canonical target comparison unavailable")
        rows = json.loads(completed.stdout)
        if not isinstance(rows, list) or len(rows) > 75000:
            raise ValueError("canonical target comparison too large")
        return rows
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ValueError("unable to obtain canonical typed target values") from exc


def create_model_worksheet(
    case_bytes: bytes, manifest: dict, evidence_root: Path, review_bytes: bytes,
) -> dict:
    """Validate latest local screenshot bytes and manual reports before ANY input.

    A completed reviewer row is still only a user-reported judgment. No label
    here implies official empirical truth or that an engine was called.
    """
    review = json.loads(review_bytes)
    assessment = manual.assess_review(case_bytes, manifest, evidence_root, review)
    target_rows = _target_snapshots(case_bytes)
    review_items = assessment["review_items"]
    if len(target_rows) != len(review_items):
        raise ValueError("canonical target projection differs from review items")
    rows = []
    for reviewed, target in zip(review_items, target_rows):
        if any(reviewed[k] != target[k] for k in (
            "earlier_capture_id", "target_capture_id", "earlier_round",
            "target_round", "round_number_gap", "same_capture_phase",
            "side", "line", "physical_position", "review_reason",
        )):
            raise ValueError("canonical target identity mismatch")
        rows.append({
            **reviewed,
            **{k: target[k] for k in (
                "target_typed_unit", "target_typed_wave",
                "target_typed_count", "target_typed_hp_percent",
            )},
            "predicted_target_unit": None,
            "predicted_target_wave": None,
            "predicted_target_count": None,
            "predicted_target_hp_percent": None,
        })
    return {
        "schema": SCHEMA,
        "record_kind": "draft_user_model_candidate_not_empirical_evidence",
        "case_id": assessment["case_id"],
        "case_backup_bytes_sha256": assessment["case_backup_bytes_sha256"],
        "review_worksheet_bytes_sha256": sha256(review_bytes).hexdigest(),
        "model_source_class": USER_MODEL_SOURCE,
        "model_run_label": None,
        "comparison_rows": rows,
    }


def assess_model_candidate(
    case_bytes: bytes, manifest: dict, evidence_root: Path,
    review_bytes: bytes, proposed: dict,
) -> dict:
    expected = create_model_worksheet(
        case_bytes, manifest, evidence_root, review_bytes,
    )
    if not isinstance(proposed, dict) or set(proposed) != set(expected):
        raise ValueError("candidate worksheet has invalid top-level fields")
    if any(proposed[k] != expected[k] for k in expected
           if k not in ("comparison_rows", "model_run_label")):
        raise ValueError("candidate worksheet anchors are stale or forged")
    label = proposed["model_run_label"]
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 120:
        raise ValueError("enter a short model run label before assessment")
    supplied = proposed["comparison_rows"]
    reference = expected["comparison_rows"]
    if not isinstance(supplied, list) or len(supplied) != len(reference):
        raise ValueError("candidate worksheet has missing/additional rows")
    reports = []
    for index, (candidate, original) in enumerate(zip(supplied, reference)):
        if not isinstance(candidate, dict) or set(candidate) != set(original):
            raise ValueError(f"candidate row {index}: invalid fields")
        if any(candidate[k] != original[k] for k in original
               if k not in MODEL_FIELDS):
            raise ValueError(f"candidate row {index}: altered case or reviewer report")
        unit, wave = candidate["predicted_target_unit"], candidate["predicted_target_wave"]
        if any(value is not None and (
            not isinstance(value, str) or len(value) > 120
        ) for value in (unit, wave)):
            raise ValueError(f"candidate row {index}: invalid unit/Wave label")
        count = candidate["predicted_target_count"]
        hp = candidate["predicted_target_hp_percent"]
        if count is not None and (type(count) is not int or not 0 <= count <= 1000000):
            raise ValueError(f"candidate row {index}: invalid model count")
        if hp is not None and (type(hp) is not int or not 0 <= hp <= 100):
            raise ValueError(f"candidate row {index}: invalid model HP percentage")
        reason = None
        if original["reviewer_reported_status"] != "REVIEWER_REPORTS_IMAGES_READABLE":
            reason = "NO_READABLE_USER_REVIEW_OR_REVIEW_CONFLICT"
        elif original["round_number_gap"] != 1:
            reason = "UNOBSERVED_INTERMEDIATE_GAME_ROUNDS"
        elif not original["same_capture_phase"]:
            reason = "DIFFERENT_CAPTURE_PHASE"
        elif original["review_reason"] in ("NO_ENTERED_VISIBLE_SLOTS", "LABEL_CHANGED"):
            reason = "TARGET_IDENTITY_NOT_STABLE_OR_MISSING"
        elif not all(
            original[k] is not None and original[k] != ""
            for k in ("target_typed_unit", "target_typed_wave",
                      "target_typed_count", "target_typed_hp_percent")
        ):
            reason = "TARGET_USER_TRANSCRIPTION_INCOMPLETE"
        elif count is None or hp is None or not unit or not wave:
            reason = "MODEL_CANDIDATE_INCOMPLETE"
        elif unit != original["target_typed_unit"] or wave != original["target_typed_wave"]:
            reason = "MODEL_AND_TYPED_TARGET_LABELS_DIFFER"
        if reason:
            result = "NOT_ASSESSABLE_" + reason
            count_delta = None
            hp_delta = None
        else:
            count_delta = count - original["target_typed_count"]
            hp_delta = hp - original["target_typed_hp_percent"]
            result = ("USER_ENTERED_MODEL_TARGET_SNAPSHOT_EQUAL_UNVERIFIED"
                      if count_delta == 0 and hp_delta == 0 else
                      "USER_ENTERED_MODEL_TARGET_SNAPSHOT_DIFFERENT_UNVERIFIED")
        reports.append({
            **original,
            **{k: candidate[k] for k in sorted(MODEL_FIELDS)},
            "diagnostic_status": result,
            "model_minus_user_typed_count": count_delta,
            "model_minus_user_typed_hp_percentage_points": hp_delta,
            "gameforge_observation_authenticated": False,
            "target_slot_transcription_independently_verified": False,
            "model_prediction_engine_attested": False,
            "combat_mechanic_validated": False,
        })
    return {
        "schema": REPORT_SCHEMA,
        "status": "USER_MODEL_CANDIDATE_DIAGNOSTICS_NOT_EMPIRICAL_VALIDATION",
        "case_id": expected["case_id"],
        "case_backup_bytes_sha256": expected["case_backup_bytes_sha256"],
        "review_worksheet_bytes_sha256": expected["review_worksheet_bytes_sha256"],
        "model_source_class": USER_MODEL_SOURCE,
        "model_run_label": label,
        "candidate_rows": reports,
        "candidate_rows_with_numeric_diagnostic": sum(
            v["model_minus_user_typed_count"] is not None for v in reports
        ),
        "original_game_screenshots_authenticated": False,
        "source_provenance_independently_verified": False,
        "image_decoded_or_visually_inspected_by_tool": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "model_calibration_verified": False,
        "model_prediction_engine_attested": False,
        "combat_causality_inferred": False,
        "notes": [
            "All typed observations and visual review statuses are USER-SUPPLIED.",
            "Model candidate values are USER-ENTERED, not validated simulator output.",
            "Numeric differences are same-capture TARGET SNAPSHOT diagnostics only.",
            "No original screenshot content or timing was independently authenticated.",
            "No unseen rounds, casualties, healing, target shots or Reserve HP inferred.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--review-worksheet", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-model-worksheet", type=Path)
    group.add_argument("--model-worksheet", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if args.write_model_worksheet is not None and args.output_json is not None:
        parser.error("--write-model-worksheet cannot use --output-json")
    if args.model_worksheet is not None and args.output_json is None:
        parser.error("--model-worksheet requires --output-json")
    try:
        original = binder._read_limited(args.case, binder.MAX_CASE_BYTES)
        manifest = json.loads(binder._read_limited(
            args.manifest, binder.MAX_MANIFEST_BYTES
        ))
        review = binder._read_limited(args.review_worksheet, manual.MAX_REVIEW_BYTES)
        if args.write_model_worksheet is not None:
            value = create_model_worksheet(original, manifest, args.evidence_root, review)
            destination = args.write_model_worksheet
            status = "DRAFT_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED"
        else:
            prediction = json.loads(binder._read_limited(
                args.model_worksheet, MAX_WORKSHEET_BYTES
            ))
            value = assess_model_candidate(original, manifest, args.evidence_root,
                                           review, prediction)
            destination = args.output_json
            status = value["status"]
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"invalid model candidate or stale source: {type(exc).__name__}\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except FileExistsError:
        parser.exit(2, "refusing to overwrite existing evidence or research output\n")
    print(json.dumps({"status": status}))


if __name__ == "__main__":
    main()
