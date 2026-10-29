"""Local-only research triage for pending browser-case screenshot coverage.

Combines canonical user-entered captured-round comparisons with newly opened
local image bytes. Even when all files are fingerprinted, NO screenshot is
authenticated or visually inspected, and NO Gameforge mechanic is proved.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from tools.research import p0_report_case_local_image_binding as binder

SCHEMA = "p0_report_case_pending_image_coverage_v1"
NODE_PAIRS = r"""
const fs=require('node:fs');
const M=require(process.argv[1]);
try {
  const c=JSON.parse(fs.readFileSync(0,'utf8'));
  const pairs=M.summarizeCapturedTimeline(c).map(p=>({
    earlier_capture_id:p.sourceId,target_capture_id:p.targetId,
    earlier_round:p.sourceRound,target_round:p.targetRound,
    round_number_gap:p.roundNumberGap,
    unknown_intermediate_game_rounds:p.roundNumberGap-1,
    same_capture_phase:p.samePhase,
    pending_review_counts:Object.fromEntries(
      Object.entries(p.counts).filter(([key])=>key!=='FIELDS_COMPARABLE')
    ),
    comparable_typed_position_count:p.counts.FIELDS_COMPARABLE
  }));
  process.stdout.write(JSON.stringify(pairs));
} catch(e) {
  process.stderr.write('invalid canonical captured timeline');
  process.exit(2);
}
"""


def _pairs(case_bytes: bytes) -> list[dict]:
    model = Path(binder.__file__).resolve().parents[2] / "battle-cases-model.js"
    try:
        result = subprocess.run(
            ["node", "-e", NODE_PAIRS, str(model)],
            input=case_bytes, capture_output=True, check=False, timeout=20,
        )
        if result.returncode != 0:
            raise ValueError("canonical captured timeline unavailable")
        data = json.loads(result.stdout)
        if not isinstance(data, list) or len(data) > 999:
            raise ValueError("unexpected captured timeline output")
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ValueError("cannot build canonical captured timeline") from exc


def audit_coverage(case_bytes: bytes, manifest: dict, evidence_root: Path) -> dict:
    """Re-hash local files NOW, never trust an older editable receipt.

    All source-presence flags mean byte fingerprinted only; they MUST NOT
    imply screenshot authenticity, per-slot transcription correctness,
    image content validity, or independently witnessed battle observations.
    """
    binding = binder.bind_case_images(case_bytes, manifest, evidence_root)
    report = {
        "schema": SCHEMA,
        "status": "INVALID",
        "case_backup_bytes_sha256": sha256(case_bytes).hexdigest(),
        "case_id": binding["case_id"],
        "image_binding_status": binding["status"],
        "image_binding_errors": list(binding["errors"]),
        "missing_or_unbound_captures": list(binding["missing_or_unbound_captures"]),
        "captured_pairs": [],
        "pending_review_positions_total": 0,
        "pairs_with_unbound_image": 0,
        "pairs_with_skipped_game_rounds": 0,
        "original_game_screenshots_authenticated": False,
        "source_provenance_independently_verified": False,
        "image_decoded_or_visually_inspected": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "model_calibration_verified": False,
        "notes": [
            "Pending status concerns typed physical-slot fields only.",
            "Image presence means a local byte hash was computed just now.",
            "No screenshot authenticity, origin, visual content or Gameforge timing verified.",
            "Gaps between captured rounds are NOT synthesized into observations.",
            "Neither matching hashes nor matching manually typed fields prove a combat rule.",
        ],
    }
    if binding["status"] in ("INVALID", "INVALID_OR_HASH_MISMATCH"):
        return report
    try:
        pairs = _pairs(case_bytes)
    except ValueError:
        report["image_binding_errors"].append("canonical timeline comparison unavailable")
        return report

    # Only successfully and unambiguously bound captures count. The binder
    # marks duplicate file-byte stages and mismatched expected hashes unbound.
    missing_ids = {row["capture_id"] for row in binding["missing_or_unbound_captures"]}
    bound_ids = {row["capture_id"] for row in binding["image_files"]} - missing_ids
    for pair in pairs:
        earlier = pair["earlier_capture_id"] in bound_ids
        target = pair["target_capture_id"] in bound_ids
        if earlier and target:
            coverage = "BOTH_FILES_FINGERPRINTED_UNAUTHENTICATED"
        elif earlier:
            coverage = "ONLY_EARLIER_FILE_FINGERPRINTED_UNAUTHENTICATED"
        elif target:
            coverage = "ONLY_TARGET_FILE_FINGERPRINTED_UNAUTHENTICATED"
        else:
            coverage = "NEITHER_FILE_FINGERPRINTED"
        counts = pair["pending_review_counts"]
        count = sum(counts.values())
        report["pending_review_positions_total"] += count
        report["pairs_with_unbound_image"] += int(not (earlier and target))
        report["pairs_with_skipped_game_rounds"] += int(pair["unknown_intermediate_game_rounds"] > 0)
        report["captured_pairs"].append({
            **pair,
            "pending_review_positions": count,
            "earlier_file_fingerprinted": earlier,
            "target_file_fingerprinted": target,
            "file_coverage": coverage,
            "original_image_authenticated": False,
            "manual_visible_slot_transcription_verified": False,
            "combat_causality_verified": False,
            "next_action": (
                "COLLECT_MISSING_CAPTURE_IMAGES_THEN_VISUALLY_REVIEW"
                if not (earlier and target) else
                "MANUALLY_VERIFY_ORIGINAL_CAPTURE_CONTENTS_AND_TIMING"
            ),
        })
    if not pairs:
        report["status"] = "NO_ADJACENT_CAPTURES_NOT_AUTHENTICATED"
    elif report["pairs_with_unbound_image"]:
        report["status"] = "UNVERIFIED_MISSING_IMAGE_COVERAGE"
    else:
        report["status"] = "UNVERIFIED_LOCAL_FILES_PRESENT_PENDING_VISUAL_REVIEW"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    try:
        case = binder._read_limited(args.case, binder.MAX_CASE_BYTES)
        manifest = json.loads(binder._read_limited(
            args.manifest, binder.MAX_MANIFEST_BYTES
        ))
        result = audit_coverage(case, manifest, args.evidence_root)
    except (ValueError, OSError) as exc:
        result = {
            "schema": SCHEMA, "status": "INVALID",
            "image_binding_errors": ["input rejected: " + type(exc).__name__],
            "original_game_screenshots_authenticated": False,
            "independently_verified_game_observations": 0,
            "model_calibration_verified": False,
        }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    # Same exclusive-create invariant as original source-byte binder: never
    # overwrite a screenshot, case backup, manifest or previous audit.
    try:
        with args.output_json.open("x", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except FileExistsError:
        parser.exit(2, "refusing to overwrite an existing file\n")
    print(json.dumps({"status": result["status"]}))
    if result["status"] == "INVALID":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
