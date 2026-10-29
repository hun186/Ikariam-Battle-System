"""Synthetic PNG/JPEG header fixtures only; NOT original Gameforge images."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tools.research import p0_report_case_local_image_binding as binder

NODE = shutil.which("node")
FAKE_PNG_A = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(20)
FAKE_PNG_B = FAKE_PNG_A + b"SECOND FAKE LOCAL FILE"
FAKE_JPEG_C = b"\xff\xd8\xff" + bytes(27) + b"\xff\xd9"


@pytest.fixture
def capture_case():
    if not NODE:
        pytest.skip("Node required for canonical JS case validation")
    script = r"""
const M=require(process.argv[1]);
const c=M.create('Synthetic only','naval-small');
c.rounds[0].number=50;
const r80=M.newRound(80),r81=M.newRound(81);
c.rounds.push(r81,r80);
c.rounds[0].source='UNVERIFIED local-filename.png';
r80.source='  ';
r81.phase='round_prefire';
r81.source='';
process.stdout.write(JSON.stringify(c));
"""
    module = str(Path(__file__).resolve().parents[2] / "battle-cases-model.js")
    result = subprocess.run(
        [NODE, "-e", script, module], capture_output=True, check=True, timeout=10
    )
    case_bytes = result.stdout
    record = json.loads(case_bytes)
    return case_bytes, record


def _images(root):
    root.mkdir(exist_ok=True)
    (root / "r50.png").write_bytes(FAKE_PNG_A)
    (root / "r80.png").write_bytes(FAKE_PNG_B)
    (root / "r81.jpeg").write_bytes(FAKE_JPEG_C)


def _manifest(c):
    rounds = {r["number"]: r for r in c["rounds"]}
    return {
        "schema": binder.SCHEMA,
        "record_kind": "user_supplied_unverified_files",
        "case_id": c["id"],
        "captures": [
            {"capture_id": rounds[50]["id"], "relative_path": "r50.png",
             "expected_sha256": None},
            {"capture_id": rounds[80]["id"], "relative_path": "r80.png",
             "expected_sha256": None},
            {"capture_id": rounds[81]["id"], "relative_path": "r81.jpeg",
             "expected_sha256": None},
        ],
    }


def test_full_case_capture_binding_tracks_bytes_not_evidence(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    before = deepcopy(manifest)
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert got["case_schema_validation"] == "BROWSER_MODEL_V1_STRUCTURALLY_VALID"
    assert got["case_backup_bytes_sha256"] == sha256(blob).hexdigest()
    assert got["captured_rounds"] == 3
    assert got["missing_or_unbound_captures"] == []
    assert [f["capture_round"] for f in got["image_files"]] == [50, 80, 81]
    assert [f["capture_phase"] for f in got["image_files"]] == [
        "round_end", "round_end", "round_prefire"
    ]
    assert got["image_files"][0]["source_note_status"] == "SOURCE_NOTE_TYPED_UNVERIFIED"
    assert got["image_files"][1]["source_note_status"] == "SOURCE_NOTE_MISSING"
    assert got["image_files"][2]["source_note_status"] == "SOURCE_NOTE_MISSING"
    assert got["image_files"][0]["sha256_file_bytes"] == sha256(FAKE_PNG_A).hexdigest()
    assert got["image_files"][2]["format_signature_only"] == "jpeg"
    assert got["local_file_bytes_read"] == sum(f["byte_size"] for f in got["image_files"])
    assert all(f["image_decoded_or_visually_inspected"] is False for f in got["image_files"])
    assert manifest == before
    assert got["original_game_screenshots_authenticated"] is False
    assert got["source_provenance_independently_verified"] is False
    assert got["independently_verified_game_observations"] == 0
    assert got["independent_holdouts"] == 0
    assert got["official_game_mechanism_verified"] is False
    assert got["game_combat_hypothesis_comparison_performed"] is False
    # Unlike a transcription, this integrity receipt does not leak round notes.
    assert "UNVERIFIED local-filename.png" not in json.dumps(got)
    assert str(tmp_path) not in json.dumps(got)


def test_partial_and_expected_hash_matching_remain_unverified(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    manifest["captures"] = manifest["captures"][:2]
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert [v["capture_round"] for v in got["missing_or_unbound_captures"]] == [81]
    for entry in manifest["captures"]:
        entry["expected_sha256"] = sha256((tmp_path / entry["relative_path"]).read_bytes()).hexdigest()
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    manifest = _manifest(c)
    for entry in manifest["captures"]:
        entry["expected_sha256"] = sha256((tmp_path / entry["relative_path"]).read_bytes()).hexdigest()
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "LOCAL_HASHES_MATCH_UNAUTHENTICATED"
    assert all(x["supplied_hash_matches_actual_bytes"] is True for x in got["image_files"])
    assert not got["original_game_screenshots_authenticated"]


@pytest.mark.parametrize("mutation", [
    "wrong_case_id", "forged_authentication", "extra_manifest_key",
    "duplicate_capture", "duplicate_path", "unknown_capture",
    "invalid_hash", "upper_hash", "unsafe_path", "wrong_kind",
    "too_many_entries",
])
def test_bad_manifest_is_rejected_without_claiming_source(capture_case, tmp_path, mutation):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    if mutation == "wrong_case_id":
        manifest["case_id"] = "other-case"
    elif mutation == "forged_authentication":
        manifest["official_game_mechanism_verified"] = True
    elif mutation == "extra_manifest_key":
        manifest["source_provenance_independently_verified"] = True
    elif mutation == "duplicate_capture":
        manifest["captures"][1]["capture_id"] = manifest["captures"][0]["capture_id"]
    elif mutation == "duplicate_path":
        manifest["captures"][1]["relative_path"] = "r50.png"
    elif mutation == "unknown_capture":
        manifest["captures"][0]["capture_id"] = "not-in-case"
    elif mutation == "invalid_hash":
        manifest["captures"][0]["expected_sha256"] = "0" * 63
    elif mutation == "upper_hash":
        manifest["captures"][0]["expected_sha256"] = "A" * 64
    elif mutation == "unsafe_path":
        manifest["captures"][0]["relative_path"] = "../outside.png"
    elif mutation == "wrong_kind":
        manifest["record_kind"] = "official_gameforge_verified"
    elif mutation == "too_many_entries":
        manifest["captures"].append(deepcopy(manifest["captures"][0]))
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] in ("INVALID", "INVALID_OR_HASH_MISMATCH")
    assert got["original_game_screenshots_authenticated"] is False
    assert got["independently_verified_game_observations"] == 0


def test_identical_bytes_in_two_different_rounds_are_ambiguous(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    (tmp_path / "r80.png").write_bytes(FAKE_PNG_A)
    manifest = _manifest(c)
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert any("identical image bytes" in err for err in got["errors"])
    assert [x["capture_round"] for x in got["missing_or_unbound_captures"]] == [50, 80]
    assert got["independent_holdouts"] == 0


def test_mismatch_signature_symlink_and_hash_refused(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    manifest["captures"][1]["expected_sha256"] = "0" * 64
    assert binder.bind_case_images(blob, manifest, tmp_path)["status"] == "INVALID_OR_HASH_MISMATCH"
    manifest["captures"][1]["expected_sha256"] = None
    (tmp_path / "r80.png").write_bytes(b"not a PNG at all")
    assert binder.bind_case_images(blob, manifest, tmp_path)["status"] == "INVALID_OR_HASH_MISMATCH"
    (tmp_path / "r80.png").unlink()
    (tmp_path / "r80.png").symlink_to(tmp_path / "r50.png")
    assert binder.bind_case_images(blob, manifest, tmp_path)["status"] == "INVALID_OR_HASH_MISMATCH"


def test_malformed_case_fails_before_reading_any_image(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    invalid = deepcopy(c)
    invalid["rounds"][0]["number"] = 80  # duplicated round number
    got = binder.bind_case_images(json.dumps(invalid).encode(), manifest, tmp_path)
    assert got["status"] == "INVALID"
    assert got["local_file_bytes_read"] == 0
    assert got["image_files"] == []
    assert got["case_schema_validation"] == "NOT_VALIDATED"
    got = binder.bind_case_images(b"not-json", manifest, tmp_path)
    assert got["status"] == "INVALID"
    assert got["local_file_bytes_read"] == 0


def test_blank_manifest_and_no_images_are_not_evidence(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest = binder.blank_manifest()
    assert manifest["record_kind"] == "empty_manifest_no_images"
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "INVALID"
    assert not got["original_game_screenshots_authenticated"]
    manifest = _manifest(c)
    manifest["captures"] = []
    got = binder.bind_case_images(blob, manifest, tmp_path)
    assert got["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert len(got["missing_or_unbound_captures"]) == 3
    assert got["local_file_bytes_read"] == 0


def test_cli_writes_private_local_receipt_and_exits_nonzero_for_invalid(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    case_path = tmp_path / "case.json"
    result_path = tmp_path / "local-receipt.json"
    case_path.write_bytes(blob)
    manifest_path.write_text(json.dumps(_manifest(c)), encoding="utf-8")
    args = [sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
            "--case", str(case_path),
            "--manifest", str(manifest_path),
            "--evidence-root", str(tmp_path),
            "--output-json", str(result_path)]
    run = subprocess.run(args, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    receipt = json.loads(result_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert not receipt["original_game_screenshots_authenticated"]
    assert str(tmp_path) not in result_path.read_text(encoding="utf-8")
    tampered = _manifest(c)
    tampered["captures"][0]["expected_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
    run = subprocess.run(args, capture_output=True, text=True, timeout=20)
    assert run.returncode == 2, run.stderr
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "INVALID_OR_HASH_MISMATCH"
    templ = tmp_path / "empty-template.json"
    run = subprocess.run([sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
                          "--write-template", str(templ)],
                         capture_output=True, text=True, timeout=10)
    assert run.returncode == 0
    assert json.loads(templ.read_text()) == binder.blank_manifest()
