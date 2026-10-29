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
from tools.research import p0_report_case_pending_image_coverage as coverage
from tools.research import p0_report_case_manual_visual_review as manual

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
    invalid_receipt = tmp_path / "invalid-receipt.json"
    run = subprocess.run(args[:-1] + [str(invalid_receipt)],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 2, run.stderr
    assert json.loads(invalid_receipt.read_text(encoding="utf-8"))["status"] == "INVALID_OR_HASH_MISMATCH"
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == (
        "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    )
    templ = tmp_path / "empty-template.json"
    run = subprocess.run([sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
                          "--write-template", str(templ)],
                         capture_output=True, text=True, timeout=10)
    assert run.returncode == 0
    assert json.loads(templ.read_text()) == binder.blank_manifest()


def test_cli_never_overwrites_input_images_manifest_or_existing_receipt(capture_case, tmp_path):
    blob, case = capture_case
    _images(tmp_path)
    case_file = tmp_path / "report-backup.json"
    manifest_file = tmp_path / "source-manifest.json"
    case_file.write_bytes(blob)
    manifest_file.write_text(json.dumps(_manifest(case)), encoding="utf-8")
    fake_original = tmp_path / "r50.png"
    duplicate_hardlink = tmp_path / "hardlink-evidence.png"
    duplicate_hardlink.hardlink_to(fake_original)
    duplicate_symlink = tmp_path / "symlink-evidence.png"
    duplicate_symlink.symlink_to(fake_original)
    prior_receipt = tmp_path / "earlier-receipt.json"
    prior_receipt.write_bytes(b"KEEP THIS OLD RECEIPT")
    original = {
        "case": case_file.read_bytes(),
        "manifest": manifest_file.read_bytes(),
        "image": fake_original.read_bytes(),
        "existing_receipt": prior_receipt.read_bytes(),
    }
    base = [
        sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
        "--case", str(case_file), "--manifest", str(manifest_file),
        "--evidence-root", str(tmp_path), "--output-json",
    ]
    for output in (
        case_file, manifest_file, fake_original,
        duplicate_symlink, duplicate_hardlink, prior_receipt,
    ):
        run = subprocess.run(base + [str(output)], capture_output=True,
                             text=True, timeout=20)
        assert run.returncode == 2, (str(output), run.stderr)
        assert "refusing to overwrite" in run.stderr
        assert case_file.read_bytes() == original["case"]
        assert manifest_file.read_bytes() == original["manifest"]
        assert fake_original.read_bytes() == original["image"]
        assert prior_receipt.read_bytes() == original["existing_receipt"]
        assert duplicate_symlink.is_symlink()
    # Template creation must obey the same no-overwrite contract.
    template = tmp_path / "blank-template.json"
    command = [sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
               "--write-template", str(template)]
    assert subprocess.run(command, capture_output=True, timeout=10).returncode == 0
    before = template.read_bytes()
    run = subprocess.run(command, capture_output=True, timeout=10)
    assert run.returncode == 2
    assert template.read_bytes() == before


def test_case_worksheet_sorted_and_fail_closed_before_image_binding(capture_case, tmp_path):
    blob, c = capture_case
    sheet = binder.case_worksheet(blob)
    assert set(sheet) == {"schema", "record_kind", "case_id", "captures"}
    assert sheet["schema"] == binder.SCHEMA
    assert sheet["record_kind"] == "draft_capture_worksheet_not_evidence"
    assert sheet["case_id"] == c["id"]
    assert [(v["capture_round"], v["capture_phase"]) for v in sheet["captures"]] == [
        (50, "round_end"), (80, "round_end"), (81, "round_prefire")
    ]
    ids = {r["number"]: r["id"] for r in c["rounds"]}
    assert [v["capture_id"] for v in sheet["captures"]] == [ids[50], ids[80], ids[81]]
    assert all(v["relative_path"] is None and v["expected_sha256"] is None
               for v in sheet["captures"])
    assert "UNVERIFIED local-filename.png" not in json.dumps(sheet)
    assert "source" not in sheet["captures"][0]
    _images(tmp_path)
    result = binder.bind_case_images(blob, sheet, tmp_path)
    assert result["status"] == "INVALID"
    assert result["local_file_bytes_read"] == 0
    assert result["image_files"] == []
    assert result["independently_verified_game_observations"] == 0


def test_filled_case_worksheet_binds_correct_captured_rounds_only(capture_case, tmp_path):
    blob, c = capture_case
    _images(tmp_path)
    sheet = binder.case_worksheet(blob)
    before = deepcopy(sheet)
    sheet["record_kind"] = "user_supplied_unverified_files"
    for entry, filename in zip(sheet["captures"], ("r50.png", "r80.png", "r81.jpeg")):
        entry["relative_path"] = filename
    result = binder.bind_case_images(blob, sheet, tmp_path)
    assert result["status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert [(row["capture_round"], row["capture_phase"]) for row in result["image_files"]] == [
        (50, "round_end"), (80, "round_end"), (81, "round_prefire")
    ]
    assert all(not row["image_decoded_or_visually_inspected"] for row in result["image_files"])
    assert result["original_game_screenshots_authenticated"] is False
    assert before["record_kind"] == "draft_capture_worksheet_not_evidence"
    # Missing work can be represented by OMITTING a still-unfilled capture row.
    missing_sheet = deepcopy(sheet)
    missing_sheet["captures"] = missing_sheet["captures"][:2]
    partial = binder.bind_case_images(blob, missing_sheet, tmp_path)
    assert partial["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert [x["capture_round"] for x in partial["missing_or_unbound_captures"]] == [81]


@pytest.mark.parametrize("change", [
    "wrong_round", "wrong_phase", "both_missing", "phase_missing",
    "round_as_bool", "phase_as_none", "blank_image_path",
])
def test_case_worksheet_stage_metadata_cannot_be_forged_or_incomplete(
    capture_case, tmp_path, change
):
    blob, c = capture_case
    _images(tmp_path)
    sheet = binder.case_worksheet(blob)
    sheet["record_kind"] = "user_supplied_unverified_files"
    sheet["captures"] = sheet["captures"][:1]
    entry = sheet["captures"][0]
    entry["relative_path"] = "r50.png"
    if change == "wrong_round":
        entry["capture_round"] = 51
    elif change == "wrong_phase":
        entry["capture_phase"] = "round_prefire"
    elif change == "both_missing":
        del entry["capture_round"]
        del entry["capture_phase"]
        # Both absent is the *legacy* accepted manifest format.
        assert binder.bind_case_images(blob, sheet, tmp_path)["status"] == (
            "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
        )
        return
    elif change == "phase_missing":
        del entry["capture_phase"]
    elif change == "round_as_bool":
        entry["capture_round"] = True
    elif change == "phase_as_none":
        entry["capture_phase"] = None
    elif change == "blank_image_path":
        entry["relative_path"] = None
    result = binder.bind_case_images(blob, sheet, tmp_path)
    assert result["status"] == "INVALID_OR_HASH_MISMATCH"
    assert result["image_files"] == []
    assert result["local_file_bytes_read"] == 0
    assert result["original_game_screenshots_authenticated"] is False


def test_cli_case_worksheet_from_real_case_file_never_overwrites_evidence(
    capture_case, tmp_path
):
    blob, c = capture_case
    case_path = tmp_path / "original-case.json"
    worksheet = tmp_path / "capture-worksheet.json"
    case_path.write_bytes(blob)
    cmd = [sys.executable, "-m", "tools.research.p0_report_case_local_image_binding",
           "--case", str(case_path), "--write-case-worksheet", str(worksheet)]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["status"] == "DRAFT_CAPTURE_WORKSHEET_NOT_EVIDENCE"
    sheet = json.loads(worksheet.read_text(encoding="utf-8"))
    assert [row["capture_round"] for row in sheet["captures"]] == [50, 80, 81]
    assert sheet == binder.case_worksheet(blob)
    assert case_path.read_bytes() == blob
    assert "UNVERIFIED local-filename.png" not in worksheet.read_text()
    original_worksheet = worksheet.read_bytes()
    # Draft output and direct case backup must never be overwritten.
    assert subprocess.run(cmd, capture_output=True, timeout=20).returncode == 2
    assert worksheet.read_bytes() == original_worksheet
    assert subprocess.run(cmd[:-1] + [str(case_path)],
                          capture_output=True, timeout=20).returncode == 2
    assert case_path.read_bytes() == blob
    # A corrupted source case must be rejected BEFORE creating an output.
    wrong_case = tmp_path / "invalid-case.json"
    bad = deepcopy(c)
    bad["rounds"][0]["number"] = 80  # duplicate numeric captured round
    wrong_case.write_text(json.dumps(bad), encoding="utf-8")
    target = tmp_path / "should-not-exist.json"
    run = subprocess.run([sys.executable, "-m",
                          "tools.research.p0_report_case_local_image_binding",
                          "--case", str(wrong_case), "--write-case-worksheet",
                          str(target)], capture_output=True, timeout=20)
    assert run.returncode == 2
    assert not target.exists()
    assert wrong_case.read_bytes() == json.dumps(bad).encode("utf-8")



def _with_pending_slots(record):
    """Construct synthetic, validated-visible typed positions, not battle evidence."""
    altered = deepcopy(record)
    by_round = {r["number"]: r for r in altered["rounds"]}
    by_round[50]["attacker"]["slots"] = [{
        "line": "first", "pos": 1, "unit": "ram_ship", "wave": "W1",
        "count": 7, "hp": 94, "deaths": None,
    }]
    by_round[80]["attacker"]["slots"] = [{
        "line": "first", "pos": 1, "unit": "ram_ship", "wave": "W1",
        "count": None, "hp": None, "deaths": None,
    }]
    return json.dumps(altered).encode("utf-8"), altered


def test_pending_capture_image_coverage_joins_canonical_pairs_and_local_bytes(
    capture_case, tmp_path
):
    _, c = capture_case
    blob, filled = _with_pending_slots(c)
    _images(tmp_path)
    result = coverage.audit_coverage(blob, _manifest(filled), tmp_path)
    assert result["status"] == "UNVERIFIED_LOCAL_FILES_PRESENT_PENDING_VISUAL_REVIEW"
    assert result["image_binding_status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert result["case_backup_bytes_sha256"] == sha256(blob).hexdigest()
    assert result["case_id"] == filled["id"]
    assert result["pairs_with_unbound_image"] == 0
    assert result["pairs_with_skipped_game_rounds"] == 1
    assert len(result["captured_pairs"]) == 2
    first, second = result["captured_pairs"]
    assert (first["earlier_round"], first["target_round"]) == (50, 80)
    assert first["round_number_gap"] == 30
    assert first["unknown_intermediate_game_rounds"] == 29
    assert first["pending_review_counts"]["INCOMPLETE"] == 1
    assert first["pending_review_positions"] == 1
    assert first["file_coverage"] == "BOTH_FILES_FINGERPRINTED_UNAUTHENTICATED"
    assert second["earlier_round"] == 80 and second["target_round"] == 81
    assert second["pending_review_counts"]["ONE_SIDED"] == 1
    assert second["round_number_gap"] == 1
    assert second["same_capture_phase"] is False
    assert second["pending_review_positions"] == 1
    assert result["pending_review_positions_total"] == 2
    assert all(p["original_image_authenticated"] is False for p in result["captured_pairs"])
    assert all(p["manual_visible_slot_transcription_verified"] is False for p in result["captured_pairs"])
    assert all(p["combat_causality_verified"] is False for p in result["captured_pairs"])
    assert result["independently_verified_game_observations"] == 0
    assert result["independent_holdouts"] == 0
    assert result["model_calibration_verified"] is False
    assert "UNVERIFIED local-filename.png" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize("kept,expected", [
    ((50, 80), ("BOTH_FILES_FINGERPRINTED_UNAUTHENTICATED",
                "ONLY_EARLIER_FILE_FINGERPRINTED_UNAUTHENTICATED")),
    ((50,), ("ONLY_EARLIER_FILE_FINGERPRINTED_UNAUTHENTICATED",
             "NEITHER_FILE_FINGERPRINTED")),
    ((81,), ("NEITHER_FILE_FINGERPRINTED",
             "ONLY_TARGET_FILE_FINGERPRINTED_UNAUTHENTICATED")),
    ((), ("NEITHER_FILE_FINGERPRINTED",
          "NEITHER_FILE_FINGERPRINTED")),
])
def test_pending_image_partial_coverage_is_actionable_not_authenticated(
    capture_case, tmp_path, kept, expected
):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    lookup = {r["number"]: r["id"] for r in c["rounds"]}
    selected = {lookup[n] for n in kept}
    manifest["captures"] = [row for row in manifest["captures"]
                            if row["capture_id"] in selected]
    result = coverage.audit_coverage(blob, manifest, tmp_path)
    assert result["status"] == "UNVERIFIED_MISSING_IMAGE_COVERAGE"
    assert tuple(x["file_coverage"] for x in result["captured_pairs"]) == expected
    assert all(x["next_action"] in (
        "COLLECT_MISSING_CAPTURE_IMAGES_THEN_VISUALLY_REVIEW",
        "MANUALLY_VERIFY_ORIGINAL_CAPTURE_CONTENTS_AND_TIMING",
    ) for x in result["captured_pairs"])
    assert result["original_game_screenshots_authenticated"] is False
    assert result["independently_verified_game_observations"] == 0
    assert result["image_decoded_or_visually_inspected"] is False


def test_pending_coverage_invalid_hash_or_ambiguous_image_is_not_counted(
    capture_case, tmp_path
):
    blob, c = capture_case
    _images(tmp_path)
    manifest = _manifest(c)
    manifest["captures"][0]["expected_sha256"] = "0" * 64
    mismatch = coverage.audit_coverage(blob, manifest, tmp_path)
    assert mismatch["status"] == "INVALID"
    assert mismatch["captured_pairs"] == []
    assert mismatch["image_binding_status"] == "INVALID_OR_HASH_MISMATCH"
    manifest["captures"][0]["expected_sha256"] = None
    (tmp_path / "r80.png").write_bytes(FAKE_PNG_A)
    duplicate = coverage.audit_coverage(blob, manifest, tmp_path)
    assert duplicate["status"] == "INVALID"
    assert duplicate["captured_pairs"] == []
    assert any("identical image bytes" in x for x in duplicate["image_binding_errors"])
    bad_case = json.loads(blob)
    bad_case["rounds"][0]["number"] = 80
    invalid = coverage.audit_coverage(json.dumps(bad_case).encode(), _manifest(c), tmp_path)
    assert invalid["status"] == "INVALID"
    assert invalid["captured_pairs"] == []
    assert invalid["independently_verified_game_observations"] == 0


def test_empty_typed_captures_are_review_tasks_not_validated_battles(
    capture_case, tmp_path
):
    blob, c = capture_case
    _images(tmp_path)
    result = coverage.audit_coverage(blob, _manifest(c), tmp_path)
    assert len(result["captured_pairs"]) == 2
    assert all(x["pending_review_counts"]["NO_ENTERED_VISIBLE_SLOTS"] == 1
               for x in result["captured_pairs"])
    assert all(x["pending_review_positions"] == 1 for x in result["captured_pairs"])
    assert result["pending_review_positions_total"] == 2
    assert not result["official_game_mechanism_verified"]


def test_pending_coverage_cli_never_overwrites_evidence_and_exits_on_invalid(
    capture_case, tmp_path
):
    blob, c = capture_case
    _images(tmp_path)
    case_path = tmp_path / "case.json"
    manifest_path = tmp_path / "manifest.json"
    receipt_path = tmp_path / "image-coverage.json"
    case_path.write_bytes(blob)
    manifest_path.write_text(json.dumps(_manifest(c)), encoding="utf-8")
    cmd = [sys.executable, "-m", "tools.research.p0_report_case_pending_image_coverage",
           "--case", str(case_path), "--manifest", str(manifest_path),
           "--evidence-root", str(tmp_path), "--output-json"]
    run = subprocess.run(cmd + [str(receipt_path)], capture_output=True,
                         text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["status"] == "UNVERIFIED_LOCAL_FILES_PRESENT_PENDING_VISUAL_REVIEW"
    result = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert result["status"] == "UNVERIFIED_LOCAL_FILES_PRESENT_PENDING_VISUAL_REVIEW"
    assert result["model_calibration_verified"] is False
    snapshots = {p: p.read_bytes() for p in (
        case_path, manifest_path, tmp_path / "r50.png", receipt_path
    )}
    for target in snapshots:
        run = subprocess.run(cmd + [str(target)], capture_output=True,
                             text=True, timeout=20)
        assert run.returncode == 2
        assert "refusing to overwrite" in run.stderr
        assert {p: p.read_bytes() for p in snapshots} == snapshots
    symbolic = tmp_path / "aliased-receipt.json"
    symbolic.symlink_to(case_path)
    assert subprocess.run(cmd + [str(symbolic)], capture_output=True,
                          timeout=20).returncode == 2
    assert case_path.read_bytes() == snapshots[case_path]
    tampered = _manifest(c)
    tampered["captures"][0]["expected_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
    new_report = tmp_path / "rejected-audit.json"
    run = subprocess.run(cmd + [str(new_report)], capture_output=True,
                         text=True, timeout=20)
    assert run.returncode == 2
    assert json.loads(new_report.read_text())["status"] == "INVALID"
    assert result["original_game_screenshots_authenticated"] is False



def test_manual_visual_review_worksheet_uses_canonical_pending_addresses_and_hashes(
    capture_case, tmp_path
):
    _, case = capture_case
    blob, entered = _with_pending_slots(case)
    _images(tmp_path)
    sheet = manual.review_worksheet(blob, _manifest(entered), tmp_path)
    assert sheet["record_kind"] == "user_reported_visual_review_not_authenticated"
    assert sheet["case_backup_bytes_sha256"] == sha256(blob).hexdigest()
    assert len(sheet["review_items"]) == 2
    r1, r2 = sheet["review_items"]
    assert (r1["earlier_round"], r1["target_round"], r1["review_reason"]) == (
        50, 80, "INCOMPLETE"
    )
    assert (r1["side"], r1["line"], r1["physical_position"]) == (
        "attacker", "first", 1
    )
    assert r1["round_number_gap"] == 30
    assert r1["same_capture_phase"] is True
    assert r1["earlier_image_sha256"] == sha256(FAKE_PNG_A).hexdigest()
    assert r1["target_image_sha256"] == sha256(FAKE_PNG_B).hexdigest()
    assert (r2["earlier_round"], r2["target_round"], r2["review_reason"]) == (
        80, 81, "ONE_SIDED"
    )
    assert r2["same_capture_phase"] is False
    assert all(x["review_status"] == "NOT_REVIEWED" for x in sheet["review_items"])
    assert "UNVERIFIED local-filename.png" not in json.dumps(sheet)
    assert str(tmp_path) not in json.dumps(sheet)
    no_claim = manual.assess_review(blob, _manifest(entered), tmp_path, sheet)
    assert no_claim["status"] == "NO_REVIEWER_REPORTS_NOT_AUTHENTICATED"
    assert no_claim["pending_review_items"] == 2
    assert no_claim["independently_verified_game_observations"] == 0
    assert no_claim["model_calibration_verified"] is False

    edited = deepcopy(sheet)
    edited["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    edited["review_items"][1]["review_status"] = "REVIEWER_REPORTS_TRANSCRIPTION_CONFLICT"
    assessed = manual.assess_review(blob, _manifest(entered), tmp_path, edited)
    assert assessed["status"] == "USER_REPORTED_VISUAL_REVIEW_NOT_AUTHENTICATED"
    assert assessed["review_status_counts"]["REVIEWER_REPORTS_IMAGES_READABLE"] == 1
    assert assessed["review_status_counts"]["REVIEWER_REPORTS_TRANSCRIPTION_CONFLICT"] == 1
    assert assessed["original_game_screenshots_authenticated"] is False
    assert assessed["source_provenance_independently_verified"] is False
    assert assessed["image_decoded_or_visually_inspected_by_tool"] is False
    assert assessed["official_game_mechanism_verified"] is False
    assert assessed["combat_causality_inferred"] is False
    assert edited["review_items"][0]["review_status"] == "REVIEWER_REPORTS_IMAGES_READABLE"


@pytest.mark.parametrize("change", [
    "source_capture_id", "target_capture_id", "review_reason", "phase",
    "pos", "file_hash", "case_hash", "forge_authority", "orphan_item",
    "missing_item", "unexpected_status", "bool_status", "extra_row_key",
])
def test_manual_review_rejects_forged_provenance_and_stale_slot_details(
    capture_case, tmp_path, change
):
    _, c = capture_case
    blob, entered = _with_pending_slots(c)
    _images(tmp_path)
    manifest = _manifest(entered)
    sheet = manual.review_worksheet(blob, manifest, tmp_path)
    altered = deepcopy(sheet)
    row = altered["review_items"][0]
    if change == "source_capture_id":
        row["earlier_capture_id"] = "forged"
    elif change == "target_capture_id":
        row["target_capture_id"] = "forged"
    elif change == "review_reason":
        row["review_reason"] = "FIELDS_COMPARABLE"
    elif change == "phase":
        row["same_capture_phase"] = False
    elif change == "pos":
        row["physical_position"] = 2
    elif change == "file_hash":
        row["target_image_sha256"] = "0" * 64
    elif change == "case_hash":
        altered["case_backup_bytes_sha256"] = "0" * 64
    elif change == "forge_authority":
        altered["original_game_screenshots_authenticated"] = True
    elif change == "orphan_item":
        altered["review_items"].append(deepcopy(row))
    elif change == "missing_item":
        altered["review_items"].pop()
    elif change == "unexpected_status":
        row["review_status"] = "GAMEFORGE_VERIFIED"
    elif change == "bool_status":
        row["review_status"] = True
    elif change == "extra_row_key":
        row["official_verified"] = True
    with pytest.raises(ValueError):
        manual.assess_review(blob, manifest, tmp_path, altered)


def test_manual_review_stale_image_bytes_and_case_changes_fail_closed(
    capture_case, tmp_path
):
    _, c = capture_case
    blob, entered = _with_pending_slots(c)
    _images(tmp_path)
    manifest = _manifest(entered)
    sheet = manual.review_worksheet(blob, manifest, tmp_path)
    sheet["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    (tmp_path / "r80.png").write_bytes(FAKE_PNG_B + b"later local edit")
    with pytest.raises(ValueError):
        manual.assess_review(blob, manifest, tmp_path, sheet)
    (tmp_path / "r80.png").write_bytes(FAKE_PNG_B)
    altered = deepcopy(entered)
    altered["notes"] = "changed manual description"
    with pytest.raises(ValueError):
        manual.assess_review(json.dumps(altered).encode(), manifest, tmp_path, sheet)
    manifest["captures"] = manifest["captures"][:2]
    with pytest.raises(ValueError):
        manual.assess_review(blob, manifest, tmp_path, sheet)


def test_manual_review_partial_image_bundle_rejects_positive_claims(
    capture_case, tmp_path
):
    _, c = capture_case
    blob, entered = _with_pending_slots(c)
    _images(tmp_path)
    manifest = _manifest(entered)
    manifest["captures"] = manifest["captures"][:1]
    sheet = manual.review_worksheet(blob, manifest, tmp_path)
    assert all(x["target_image_sha256"] is None for x in sheet["review_items"])
    draft = manual.assess_review(blob, manifest, tmp_path, sheet)
    assert draft["status"] == "NO_REVIEWER_REPORTS_NOT_AUTHENTICATED"
    sheet["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    with pytest.raises(ValueError, match="both source images required"):
        manual.assess_review(blob, manifest, tmp_path, sheet)
    # A deliberately synthetic blank transcription does not have fields to check.
    all_blank, fresh = capture_case
    fresh_manifest = _manifest(fresh)
    one = manual.review_worksheet(all_blank, fresh_manifest, tmp_path)
    assert all(x["review_reason"] == "NO_ENTERED_VISIBLE_SLOTS"
               for x in one["review_items"])
    one["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    with pytest.raises(ValueError, match="no visible field"):
        manual.assess_review(all_blank, fresh_manifest, tmp_path, one)


def test_manual_visual_review_cli_two_phase_private_and_exclusive(
    capture_case, tmp_path
):
    _, c = capture_case
    blob, entered = _with_pending_slots(c)
    _images(tmp_path)
    case_path = tmp_path / "private-case.json"
    manifest_path = tmp_path / "private-manifest.json"
    sheet_path = tmp_path / "review-worksheet.json"
    audit_path = tmp_path / "manual-audit.json"
    case_path.write_bytes(blob)
    manifest_path.write_text(json.dumps(_manifest(entered)), encoding="utf-8")
    common = [sys.executable, "-m", "tools.research.p0_report_case_manual_visual_review",
              "--case", str(case_path), "--manifest", str(manifest_path),
              "--evidence-root", str(tmp_path)]
    make = common + ["--write-review-worksheet", str(sheet_path)]
    run = subprocess.run(make, capture_output=True, text=True, timeout=25)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["status"] == "DRAFT_USER_VISUAL_REVIEW_NOT_AUTHENTICATED"
    draft = json.loads(sheet_path.read_text(encoding="utf-8"))
    assert len(draft["review_items"]) == 2
    assert case_path.read_bytes() == blob
    assert "UNVERIFIED local-filename.png" not in sheet_path.read_text()
    draft["review_items"][0]["review_status"] = "REVIEWER_REPORTS_IMAGES_READABLE"
    sheet_path.write_text(json.dumps(draft), encoding="utf-8")
    check = common + ["--review-worksheet", str(sheet_path),
                      "--output-json", str(audit_path)]
    run = subprocess.run(check, capture_output=True, text=True, timeout=25)
    assert run.returncode == 0, run.stderr
    report = json.loads(audit_path.read_text())
    assert report["status"] == "USER_REPORTED_VISUAL_REVIEW_NOT_AUTHENTICATED"
    assert report["model_calibration_verified"] is False
    original = {path: path.read_bytes() for path in (
        case_path, manifest_path, tmp_path / "r50.png", sheet_path, audit_path
    )}
    for existing in (case_path, sheet_path, tmp_path / "r50.png", audit_path):
        fail = subprocess.run(common + ["--write-review-worksheet", str(existing)],
                              capture_output=True, text=True, timeout=25)
        assert fail.returncode == 2
        assert "refusing to overwrite" in fail.stderr
    assert subprocess.run(check, capture_output=True, timeout=25).returncode == 2
    assert {p: p.read_bytes() for p in original} == original
    spoof = deepcopy(draft)
    spoof["official_gameforge_verified"] = True
    sheet_path.write_text(json.dumps(spoof), encoding="utf-8")
    invalid_output = tmp_path / "no-report-on-invalid-input.json"
    reject = subprocess.run(common + [
        "--review-worksheet", str(sheet_path), "--output-json", str(invalid_output)
    ], capture_output=True, timeout=25)
    assert reject.returncode == 2
    assert not invalid_output.exists()
