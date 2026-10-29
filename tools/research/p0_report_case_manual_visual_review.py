"""Private, user-reported visual-review ledger for pending browser battle captures.

A local image SHA-256 and reviewer-entered readability flag are NOT original
Gameforge authentication, independent observation, or a combat-rule finding.
This module never decodes images, copies source notes or changes the simulator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from tools.research import p0_report_case_local_image_binding as binder

SCHEMA = "p0_report_case_manual_visual_review_v1"
MAX_REVIEW_BYTES = 64 * 1024 * 1024
REVIEW_STATUSES = {
    "NOT_REVIEWED",
    "REVIEWER_REPORTS_IMAGES_READABLE",
    "REVIEWER_REPORTS_TRANSCRIPTION_CONFLICT",
    "REVIEWER_REPORTS_IMAGE_UNREADABLE",
}

# The source of physical addresses and problem codes is the browser model,
# NOT an independent Python recreation of game formation/comparison rules.
NODE_PENDING_ITEMS = r"""
const fs=require('node:fs');
const M=require(process.argv[1]);
try {
  const c=JSON.parse(fs.readFileSync(0,'utf8'));
  const pairs=M.summarizeCapturedTimeline(c);
  const all=[];
  for(const p of pairs){
    const compare=M.compareCapturedRounds(c,p.targetId,p.sourceId);
    const pending=compare.rows.length
       ? compare.rows.filter(r=>r.code!=='FIELDS_COMPARABLE')
       : [{code:'NO_ENTERED_VISIBLE_SLOTS',side:null,line:null,pos:null}];
    for(const row of pending){
      all.push({
        earlier_capture_id:p.sourceId,target_capture_id:p.targetId,
        earlier_round:p.sourceRound,target_round:p.targetRound,
        round_number_gap:p.roundNumberGap,same_capture_phase:p.samePhase,
        side:row.side,line:row.line,physical_position:row.pos,
        review_reason:row.code
      });
    }
  }
  process.stdout.write(JSON.stringify(all));
} catch(e) { process.stderr.write('invalid canonical pending fields');process.exit(2); }
"""


def _canonical_pending(case_bytes: bytes) -> list[dict]:
    model = Path(binder.__file__).resolve().parents[2] / "battle-cases-model.js"
    try:
        result = subprocess.run(
            ["node", "-e", NODE_PENDING_ITEMS, str(model)],
            input=case_bytes, capture_output=True, check=False, timeout=25,
        )
        if result.returncode != 0:
            raise ValueError("canonical pending-item comparison failed")
        items = json.loads(result.stdout)
        if not isinstance(items, list) or len(items) > 75000:
            raise ValueError("unexpected canonical pending-item output")
        return items
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ValueError("canonical pending-item comparison unavailable") from exc


def review_worksheet(case_bytes: bytes, manifest: dict, root: Path) -> dict:
    """Make draft rows anchored to current case and *freshly rehashed* files.

    Aborts on invalid/hash-mismatched/ambiguous source bundles. Partial bundles
    remain non-evidence drafts; no positive review status is prepopulated.
    """
    binding = binder.bind_case_images(case_bytes, manifest, root)
    if binding["status"] in {"INVALID", "INVALID_OR_HASH_MISMATCH"}:
        raise ValueError("invalid image bindings: cannot create review worksheet")
    hashes = {x["capture_id"]: x["sha256_file_bytes"] for x in binding["image_files"]}
    return {
        "schema": SCHEMA,
        "record_kind": "user_reported_visual_review_not_authenticated",
        "case_id": binding["case_id"],
        "case_backup_bytes_sha256": sha256(case_bytes).hexdigest(),
        "review_items": [
            {
                **row,
                "earlier_image_sha256": hashes.get(row["earlier_capture_id"]),
                "target_image_sha256": hashes.get(row["target_capture_id"]),
                "review_status": "NOT_REVIEWED",
            }
            for row in _canonical_pending(case_bytes)
        ],
    }


def assess_review(
    case_bytes: bytes, manifest: dict, root: Path, filled: dict
) -> dict:
    """Check every user-entered review claim against case+CURRENT file bytes.

    Matching file hashes are merely integrity anchors. The output is a
    user-report audit and cannot authenticate pictures, typed HP or causality.
    """
    expected = review_worksheet(case_bytes, manifest, root)
    if not isinstance(filled, dict) or set(filled) != set(expected):
        raise ValueError("review worksheet has unexpected top-level fields")
    if any(filled[k] != expected[k] for k in expected if k != "review_items"):
        raise ValueError("review worksheet's case/provenance anchor is stale")
    rows = filled["review_items"]
    baseline = expected["review_items"]
    if not isinstance(rows, list) or len(rows) != len(baseline):
        raise ValueError("review worksheet has missing or additional pending items")
    stats: Counter[str] = Counter()
    for index, (actual, template) in enumerate(zip(rows, baseline)):
        if not isinstance(actual, dict) or set(actual) != set(template):
            raise ValueError(f"review item {index}: invalid fields")
        if any(actual[k] != template[k] for k in template if k != "review_status"):
            raise ValueError(f"review item {index}: changed case, slot or source bytes")
        status = actual["review_status"]
        if not isinstance(status, str) or status not in REVIEW_STATUSES:
            raise ValueError(f"review item {index}: unsupported visual-review status")
        if status != "NOT_REVIEWED" and (
            not template["earlier_image_sha256"]
            or not template["target_image_sha256"]
        ):
            raise ValueError(f"review item {index}: both source images required")
        if status == "REVIEWER_REPORTS_IMAGES_READABLE" and (
            template["review_reason"] == "NO_ENTERED_VISIBLE_SLOTS"
        ):
            raise ValueError(f"review item {index}: no visible field exists to review")
        stats[status] += 1
    return {
        "schema": "p0_report_case_visual_review_assessment_v1",
        "status": (
            "USER_REPORTED_VISUAL_REVIEW_NOT_AUTHENTICATED"
            if len(rows) > stats["NOT_REVIEWED"]
            else "NO_REVIEWER_REPORTS_NOT_AUTHENTICATED"
        ),
        "case_id": expected["case_id"],
        "case_backup_bytes_sha256": expected["case_backup_bytes_sha256"],
        "pending_review_items": len(rows),
        "review_status_counts": {v: stats[v] for v in sorted(REVIEW_STATUSES)},
        "review_items": [
            {**{k: x[k] for k in x if k != "review_status"},
             "reviewer_reported_status": x["review_status"]}
            for x in rows
        ],
        "original_game_screenshots_authenticated": False,
        "source_provenance_independently_verified": False,
        "image_decoded_or_visually_inspected_by_tool": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "model_calibration_verified": False,
        "combat_causality_inferred": False,
        "notes": [
            "All visual-review statuses are USER-REPORTED and NOT independently verified.",
            "Hashes bind byte identity only; they do not authenticate Gameforge images.",
            "Reviewer readability/conflict labels do not certify individual typed HP.",
            "Missing unobserved game rounds, phase mismatches, target selection and",
            "combat casualty/healing/Reserve HP mechanisms are not inferred here.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-review-worksheet", type=Path)
    group.add_argument("--review-worksheet", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if args.review_worksheet is not None and args.output_json is None:
        parser.error("--review-worksheet requires --output-json")
    if args.write_review_worksheet is not None and args.output_json is not None:
        parser.error("--write-review-worksheet cannot take --output-json")
    try:
        case_bytes = binder._read_limited(args.case, binder.MAX_CASE_BYTES)
        manifest = json.loads(binder._read_limited(
            args.manifest, binder.MAX_MANIFEST_BYTES
        ))
        if args.write_review_worksheet is not None:
            value = review_worksheet(case_bytes, manifest, args.evidence_root)
            output = args.write_review_worksheet
            status = "DRAFT_USER_VISUAL_REVIEW_NOT_AUTHENTICATED"
        else:
            filled = json.loads(binder._read_limited(
                args.review_worksheet, MAX_REVIEW_BYTES
            ))
            value = assess_review(case_bytes, manifest, args.evidence_root, filled)
            output = args.output_json
            status = value["status"]
    except (OSError, ValueError) as exc:
        parser.exit(2, f"invalid input or source binding: {type(exc).__name__}\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except FileExistsError:
        parser.exit(2, "refusing to overwrite original evidence or previous worksheet\n")
    print(json.dumps({"status": status}))


if __name__ == "__main__":
    main()
