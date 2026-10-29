"""Locally fingerprint source image bytes for browser battle-report case captures.

Research-only. The v1 case JSON is validated by its canonical JS model
through Node; then explicit capture-ID -> local image relationships are checked.
This tool NEVER copies, uploads, decodes, or authenticates a Gameforge image.
The SHA-256 reports byte identity, NOT battle provenance or event timing.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

from tools.research.p0_naval_capture_local_image_manifest import (
    _digest,
    _file_digest,
    _safe_relative,
)

SCHEMA = "p0_report_case_local_image_manifest_v1"
RESULT_SCHEMA = "p0_report_case_local_image_binding_result_v1"
CASE_SCHEMA = "ikariam-report-cases-v1"
MAX_CASE_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024

# The same browser model is the sole authority on v1 case structure.
# Parsing untrusted JSON does not entail executing any user-supplied JS.
NODE_VALIDATION = r"""
const fs=require('node:fs');
const M=require(process.argv[1]);
try {
  const c=JSON.parse(fs.readFileSync(0,'utf8'));
  const issues=M.validateCase(c);
  if(issues.length){process.stdout.write(JSON.stringify({ok:false}));process.exit(0);}
  process.stdout.write(JSON.stringify({
    ok:true,id:c.id,rounds:c.rounds.map(r=>({
      id:r.id,number:r.number,phase:r.phase,has_source_note:!!r.source.trim()
    }))
  }));
} catch(e) {
  process.stdout.write(JSON.stringify({ok:false}));
}
"""


def blank_manifest() -> dict:
    return {
        "schema": SCHEMA,
        "record_kind": "empty_manifest_no_images",
        "case_id": None,
        "captures": [],
    }


def _read_limited(path: Path, limit: int) -> bytes:
    if path.stat().st_size > limit:
        raise ValueError("input exceeds file-size limit")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("input exceeds file-size limit")
    return payload


def _inspect_case(case_bytes: bytes) -> dict | None:
    if len(case_bytes) > MAX_CASE_BYTES or not shutil.which("node"):
        return None
    model = Path(__file__).resolve().parents[2] / "battle-cases-model.js"
    if not model.is_file():
        return None
    try:
        result = subprocess.run(
            ["node", "-e", NODE_VALIDATION, str(model)],
            input=case_bytes,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            return None
        decoded = json.loads(result.stdout.decode("utf-8"))
        return decoded if decoded.get("ok") is True else None
    except (OSError, ValueError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return None


def bind_case_images(case_bytes: bytes, manifest: dict, evidence_root: Path) -> dict:
    """Bind user-selected local image *bytes* to valid captured-round IDs.

    Does not claim evidence provenance, image authenticity or mechanic proof.
    Refuses nonunique image bytes across different capture IDs as ambiguous
    stage identity, not as proof that an image is fraudulent.
    """
    images: list[dict] = []
    errors: list[str] = []
    missing: list[dict] = []
    report = {
        "schema": RESULT_SCHEMA,
        "status": "INVALID",
        "case_schema_validation": "NOT_VALIDATED",
        "case_backup_bytes_sha256": sha256(case_bytes).hexdigest(),
        "case_id": None,
        "captured_rounds": 0,
        "image_files": images,
        "missing_or_unbound_captures": missing,
        "errors": errors,
        "local_file_bytes_read": 0,
        "original_game_screenshots_authenticated": False,
        "source_provenance_independently_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "game_combat_hypothesis_comparison_performed": False,
        "notes": [
            "The original browser v1 case is user-entered and NOT verified Gameforge evidence.",
            "A round.source filename/note is text, not proof of image existence.",
            "PNG/JPEG signatures and file hashes do NOT decode or authenticate screenshots.",
            "This result contains no screenshot bytes or absolute image paths.",
            "Only the local caller can inspect screenshot provenance and image contents.",
        ],
    }
    case = _inspect_case(case_bytes)
    if case is None:
        errors.append("case: canonical browser ReportCases.validateCase rejected input (or Node unavailable)")
        return report
    report["case_schema_validation"] = "BROWSER_MODEL_V1_STRUCTURALLY_VALID"
    report["case_id"] = case["id"]
    rounds = case["rounds"]
    report["captured_rounds"] = len(rounds)
    known = {r["id"]: r for r in rounds}

    if not isinstance(manifest, dict) or set(manifest) != {
        "schema", "record_kind", "case_id", "captures"
    }:
        errors.append("manifest: requires exactly schema, record_kind, case_id, captures")
        return report
    if manifest["schema"] != SCHEMA or manifest["record_kind"] != "user_supplied_unverified_files":
        errors.append("manifest: correct nonempty user_supplied_unverified_files declaration required")
        return report
    if manifest["case_id"] != case["id"]:
        errors.append("manifest: case_id does not match the validated case JSON")
        return report
    entries = manifest["captures"]
    if not isinstance(entries, list) or len(entries) > len(rounds):
        errors.append("manifest: captures must be an array no longer than captured rounds")
        return report

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    bound_ids: set[str] = set()
    digests: dict[str, set[str]] = {}
    for i, entry in enumerate(entries):
        label = f"captures[{i}]"
        if not isinstance(entry, dict) or set(entry) != {
            "capture_id", "relative_path", "expected_sha256"
        }:
            errors.append(f"{label}: requires exactly capture_id, relative_path, expected_sha256")
            continue
        capture_id = entry["capture_id"]
        relative = entry["relative_path"]
        expected = entry["expected_sha256"]
        if not isinstance(capture_id, str) or capture_id not in known:
            errors.append(f"{label}: capture_id not in the validated case")
            continue
        if capture_id in seen_ids:
            errors.append(f"{label}: duplicate capture_id")
            continue
        seen_ids.add(capture_id)
        if not isinstance(relative, str) or not _safe_relative(relative):
            errors.append(f"{label}: unsafe relative image path")
            continue
        if relative in seen_paths:
            errors.append(f"{label}: image path bound to multiple capture IDs")
            continue
        seen_paths.add(relative)
        if expected is not None and not _digest(expected):
            errors.append(f"{label}: expected_sha256 must be lowercase hex SHA-256 or null")
            continue
        try:
            actual = _file_digest(Path(evidence_root), relative)
        except (ValueError, OSError) as exc:
            errors.append(f"{label}: unreadable or malformed local image ({type(exc).__name__})")
            continue
        report["local_file_bytes_read"] += actual["byte_size"]
        item = {
            "capture_id": capture_id,
            "capture_round": known[capture_id]["number"],
            "capture_phase": known[capture_id]["phase"],
            "source_note_status": (
                "SOURCE_NOTE_TYPED_UNVERIFIED" if known[capture_id]["has_source_note"]
                else "SOURCE_NOTE_MISSING"
            ),
            "relative_path": relative,
            **actual,
            "expected_sha256_supplied": expected is not None,
            "supplied_hash_matches_actual_bytes": (
                None if expected is None else expected == actual["sha256_file_bytes"]
            ),
        }
        images.append(item)
        digests.setdefault(actual["sha256_file_bytes"], set()).add(capture_id)
        if expected is not None and expected != actual["sha256_file_bytes"]:
            errors.append(f"{label}: supplied SHA-256 does not match read bytes")
        else:
            bound_ids.add(capture_id)

    for ids in digests.values():
        if len(ids) > 1:
            errors.append("identical image bytes for distinct captured rounds; stage identity ambiguous")
            bound_ids.difference_update(ids)
    for r in sorted(rounds, key=lambda x: x["number"]):
        if r["id"] not in bound_ids:
            missing.append({"capture_id": r["id"], "capture_round": r["number"],
                            "capture_phase": r["phase"]})
    if errors:
        report["status"] = "INVALID_OR_HASH_MISMATCH"
    elif missing:
        report["status"] = "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    elif all(x["expected_sha256_supplied"] for x in images):
        report["status"] = "LOCAL_HASHES_MATCH_UNAUTHENTICATED"
    else:
        report["status"] = "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-template", type=Path)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if args.write_template is not None:
        if any(v is not None for v in (
            args.case, args.manifest, args.evidence_root, args.output_json
        )):
            parser.error("--write-template must be used alone")
        path, result = args.write_template, blank_manifest()
    else:
        if any(v is None for v in (
            args.case, args.manifest, args.evidence_root, args.output_json
        )):
            parser.error("requires --case --manifest --evidence-root --output-json")
        path = args.output_json
        try:
            case_bytes = _read_limited(args.case, MAX_CASE_BYTES)
            manifest_bytes = _read_limited(args.manifest, MAX_MANIFEST_BYTES)
            manifest = json.loads(manifest_bytes)
            result = bind_case_images(case_bytes, manifest, args.evidence_root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result = {"schema": RESULT_SCHEMA, "status": "INVALID",
                      "errors": [f"input: rejected ({type(exc).__name__})"],
                      "original_game_screenshots_authenticated": False,
                      "independently_verified_game_observations": 0}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Critical P2: even an accidental --output-json pointing to a screenshot,
    # case backup, manifest, hard link or symlink must NEVER overwrite data.
    # Exclusive creation is atomic for the final directory entry (O_EXCL);
    # an existence-check followed by write_text() would be race-prone.
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\\n")
    except FileExistsError:
        parser.exit(2, "refusing to overwrite an existing output file\n")
    print(json.dumps({"status": result.get("status", "EMPTY_TEMPLATE")}))
    if args.write_template is None and result["status"] in (
        "INVALID", "INVALID_OR_HASH_MISMATCH"
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
