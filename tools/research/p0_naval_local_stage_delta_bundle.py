"""Conservative local image-byte gate for unverified R1/R2 naval deltas.

Reads local files ONLY through the existing secure manifest binder.
Two distinct local stage files are necessary but NEVER sufficient to prove
Gameforge origin, screenshot time, physical ship identity or healing logic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.research import p0_naval_capture_local_image_manifest as images
from tools.research import p0_naval_stage_pair_deltas as deltas

SCHEMA = "p0_naval_local_stage_delta_bundle_v1"
READY = "UNVERIFIED_STAGE_DELTAS_LOCAL_BYTES_BOUND"
PARTIAL = "UNVERIFIED_PARTIAL_STAGE_DELTAS_LOCAL_BYTES_BOUND"
UNBOUND = "UNVERIFIED_STAGE_BYTES_UNBOUND"
INVALID = "INVALID_OR_HASH_MISMATCH"
STAGES = ("r1_end", "r2_prefire")
SAFE_BINDING_STATUSES = frozenset((
    "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED",
    "LOCAL_HASHES_MATCH_UNAUTHENTICATED",
    "UNVERIFIED_PARTIAL_SOURCE_BUNDLE",
))


def compare_local_bundle(record, manifest, evidence_root: Path) -> dict:
    """Use the same in-memory transcription for both the local byte gate
    and delta arithmetic; never accept a reusable/stale external digest report.
    """
    pair = deltas.compare(record)
    binding = images.bind_files(record, manifest, evidence_root)
    out = {
        "schema": SCHEMA,
        "status": INVALID,
        "stage_pair_status": pair["status"],
        "image_binding_status": binding["status"],
        "manual_transcription_sha256": pair["manual_transcription_sha256"],
        "binding_transcription_sha256_matches": False,
        "local_image_bytes_sha256_by_stage": {},
        "candidate_label_matches": [],
        "stage_pair_unmatched_r1_labels": pair["unmatched_r1_labels"],
        "stage_pair_unmatched_r2_labels": pair["unmatched_r2_labels"],
        "stage_pair_ambiguous_physical_slots": pair["ambiguous_physical_slots"],
        "stage_pair_missing_for_followup": pair["missing_for_followup"],
        "comparability_blockers": list(pair["comparability_blockers"]),
        "image_binding_errors": list(binding["invalid_manifest_or_file_errors"]),
        "image_missing_or_unbound_source_refs": list(
            binding["missing_or_unbound_source_refs"]),
        "local_file_hashes_are_not_gameforge_authentication": True,
        "original_game_screenshots_authenticated": False,
        "stage_timing_independently_verified": False,
        "physical_ship_identity_independently_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "tender_healing_causation_verified": False,
        "notes": [
            "Two different local screenshot-byte hashes only establish different local byte sequences.",
            "The user-labelled phase, slot, timing and source metadata remain unverified.",
            "PNG/JPEG signatures are not full image decoding or visual inspection.",
            "Rendered HP percentage point differences are not an HP or Tender-healing rule.",
            "Neither the screenshot bytes nor local file paths are copied to this report.",
        ],
    }
    a, b = pair["manual_transcription_sha256"], binding[
        "manual_transcription_sha256"]
    out["binding_transcription_sha256_matches"] = (
        isinstance(a, str) and bool(a) and a == b)
    if pair["status"] == deltas.INVALID:
        out["comparability_blockers"].append("archive transcription invalid/empty")
        return out
    if not out["binding_transcription_sha256_matches"]:
        out["comparability_blockers"].append(
            "binding digest differs from the current transcription JSON")
        return out
    if (binding["status"] not in SAFE_BINDING_STATUSES
            or out["image_binding_errors"]):
        out["comparability_blockers"].append(
            "local image binding invalid, unsafe, ambiguous or hash mismatched")
        return out

    # A PARTIAL binding may lack OPTIONAL fleet setup, but it must bind BOTH
    # named R1/R2 files. Do not promote user-supplied labels to game provenance.
    refs = record["source_refs"]
    named = [refs.get(phase) for phase in STAGES]
    if (any(not isinstance(v, str) or not v.strip() for v in named)
            or len(set(named)) != 2):
        out["comparability_blockers"].append(
            "distinct nonempty R1/R2 stage source refs required")
        out["status"] = UNBOUND
        return out
    digests = {}
    for file_info in binding["files"]:
        ref = file_info["source_ref"]
        if ref in named and file_info["supplied_hash_matches_actual_bytes"] is not False:
            digests[ref] = file_info["sha256_file_bytes"]
    if (any(ref not in digests for ref in named)
            or any(ref in out["image_missing_or_unbound_source_refs"]
                   for ref in named)):
        out["comparability_blockers"].append(
            "R1/R2 must each have a non-ambiguous local image-byte binding")
        out["status"] = UNBOUND
        return out
    if digests[named[0]] == digests[named[1]]:
        out["comparability_blockers"].append(
            "R1/R2 stage images contain identical local bytes")
        out["status"] = INVALID
        return out
    out["local_image_bytes_sha256_by_stage"] = {
        phase: digests[refs[phase]] for phase in STAGES
    }

    # File-byte identity is NOT phase authenticity. Pairing restrictions
    # (including no declared reinforcements and no conflicting slot owners)
    # are still applied by the existing read-only comparator.
    if pair["comparability_blockers"]:
        out["status"] = PARTIAL
        return out
    out["candidate_label_matches"] = pair["candidate_label_matches"]
    out["status"] = (READY if pair["status"] == deltas.SUCCESS else PARTIAL)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    args = p.parse_args()
    result = compare_local_bundle(
        json.loads(args.record.read_text(encoding="utf-8")),
        json.loads(args.manifest.read_text(encoding="utf-8")),
        args.evidence_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output_json)}))
    if result["status"] in (INVALID, UNBOUND):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
