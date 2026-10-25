"""Invented local byte fixtures only, never genuine Gameforge screenshots."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.research import p0_naval_capture_archive as archive
from tools.research import p0_naval_capture_local_image_manifest as binder


# Deliberately ONLY a PNG signature + IHDR marker; not a decoded game image.
FAKE_PNG_HEADER = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(20)
FAKE_JPG_HEADER = b"\xff\xd8\xff" + bytes(25) + b"\xff\xd9"


def _invented_record():
    record = archive.blank_template()
    record.update({
        "record_kind": archive.TRANSCRIPTION,
        "record_id": "TEST_ONLY_NO_REAL_GAME_SOURCE",
        "source_refs": {
            "r1_end": "test-r1", "r2_prefire": "test-r2", "fleet_setup": "test-setup"
        },
        "battle_context": {
            "battlefield_id": "naval-small",
            "attacker_forge_level": 0,
            "defender_forge_level": 3,
            "attacker_units": {"barbarian_wedge_paddler": 5},
            "defender_units": {"carrier": 3},
            "workshop_upgrades": {
                "attacker": {"barbarian_wedge_paddler": {"attack": 0, "armor": 0}},
                "defender": {"carrier": {"attack": 1, "armor": 2}},
            },
            "reinforcements_between": "none",
            "r2_prefire_confirmed": True,
        },
        "observations": [
            {
                "phase": "r1_end", "side": "defender", "unit_id": "carrier",
                "wave_label": "fake-wave", "physical_slot_label": "fake-slot",
                "visible_percent": 80, "units_alive": 3, "source_ref": "test-r1"
            },
            {
                "phase": "r2_prefire", "side": "defender", "unit_id": "carrier",
                "wave_label": "fake-wave", "physical_slot_label": "fake-slot",
                "visible_percent": 90, "units_alive": 3, "source_ref": "test-r2"
            },
        ],
    })
    assert archive.archive(record)["status"] == "UNVERIFIED_ARCHIVE_READY"
    return record


def _manifest():
    return {
        "schema": binder.SCHEMA,
        "record_kind": "user_supplied_unverified_files",
        "images": [
            {"source_ref": "test-r1", "relative_path": "r1.png", "expected_sha256": None},
            {"source_ref": "test-r2", "relative_path": "r2.jpeg", "expected_sha256": None},
            {"source_ref": "test-setup", "relative_path": "setup.png", "expected_sha256": None},
        ],
    }


def _write_images(root):
    root.mkdir(exist_ok=True)
    (root / "r1.png").write_bytes(FAKE_PNG_HEADER)
    (root / "r2.jpeg").write_bytes(FAKE_JPG_HEADER)
    (root / "setup.png").write_bytes(FAKE_PNG_HEADER + b"test-distinct-byte")


def test_empty_manifest_not_an_observation():
    assert binder.blank_manifest() == {
        "schema": binder.SCHEMA,
        "record_kind": "empty_manifest_no_images",
        "images": [],
    }
    actual = binder.bind_files(_invented_record(), binder.blank_manifest(), ".")
    assert actual["status"] == "INVALID_OR_HASH_MISMATCH"
    assert actual["local_file_bytes_read"] == 0
    assert actual["independently_verified_game_observations"] == 0


def test_local_bytes_fingerprint_matches_stages_but_authenticity_always_false(tmp_path):
    _write_images(tmp_path)
    record, manifest = _invented_record(), _manifest()
    original = deepcopy(record), deepcopy(manifest)
    result = binder.bind_files(record, manifest, tmp_path)
    assert result["status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert len(result["files"]) == 3
    assert result["local_file_bytes_read"] == sum(x["byte_size"] for x in result["files"])
    assert result["files"][0]["sha256_file_bytes"] == sha256(FAKE_PNG_HEADER).hexdigest()
    assert result["files"][0]["format_signature_only"] == "png"
    assert result["files"][1]["format_signature_only"] == "jpeg"
    assert all(x["image_decoded_or_visually_inspected"] is False for x in result["files"])
    assert all(x["supplied_hash_matches_actual_bytes"] is None for x in result["files"])
    assert result["manual_transcription_sha256"] == archive.archive(record)["user_record_sha256"]
    assert record == original[0] and manifest == original[1]
    assert result["original_game_screenshots_authenticated"] is False
    assert result["official_game_mechanism_verified"] is False
    assert result["independent_holdouts"] == 0
    assert result["game_combat_hypothesis_comparison_performed"] is False
    assert "fake-slot" not in json.dumps(result)


def test_predeclared_local_hash_match_is_still_unverified(tmp_path):
    _write_images(tmp_path)
    manifest = _manifest()
    for row in manifest["images"]:
        row["expected_sha256"] = sha256(
            (tmp_path / row["relative_path"]).read_bytes()
        ).hexdigest()
    got = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert got["status"] == "LOCAL_HASHES_MATCH_UNAUTHENTICATED"
    assert len(got["files"]) == 3
    assert all(x["supplied_hash_matches_actual_bytes"] is True for x in got["files"])
    assert got["source_provenance_independently_verified"] is False


def test_modified_file_detected_even_though_new_image_has_same_header(tmp_path):
    _write_images(tmp_path)
    manifest = _manifest()
    manifest["images"][0]["expected_sha256"] = sha256(FAKE_PNG_HEADER).hexdigest()
    (tmp_path / "r1.png").write_bytes(FAKE_PNG_HEADER + b"changed-byte")
    result = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert result["status"] == "INVALID_OR_HASH_MISMATCH"
    assert any("SHA-256" in v for v in result["invalid_manifest_or_file_errors"])
    assert result["files"][0]["supplied_hash_matches_actual_bytes"] is False
    assert result["original_game_screenshots_authenticated"] is False


def test_broken_or_missing_source_file_yields_error_without_fabrication(tmp_path):
    _write_images(tmp_path)
    (tmp_path / "r1.png").unlink()
    result = binder.bind_files(_invented_record(), _manifest(), tmp_path)
    assert result["status"] == "INVALID_OR_HASH_MISMATCH"
    assert result["local_file_bytes_read"] > 0
    assert all(f["source_ref"] != "test-r1" for f in result["files"])
    assert not result["official_game_mechanism_verified"]


@pytest.mark.parametrize("bad_path", [
    "../outside.png", "/etc/passwd", "./r1.png", "a//b.png", "a/../r1.png",
    "C:/Windows/win.ini", r"foo\..\r1.png", "https://host/image.png", "",
    " r1.png", "~home/file.png",
])
def test_bad_path_rejected_before_any_bytes_are_read(tmp_path, bad_path):
    _write_images(tmp_path)
    manifest = _manifest()
    manifest["images"][0]["relative_path"] = bad_path
    result = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert result["status"] == "INVALID_OR_HASH_MISMATCH"
    assert all(x["relative_path"] != bad_path for x in result["files"])
    assert any("unsafe relative_path" in e for e in result["invalid_manifest_or_file_errors"])


def test_symlink_or_directory_as_source_is_not_read(tmp_path):
    _write_images(tmp_path)
    (tmp_path / "alias.png").symlink_to(tmp_path / "r1.png")
    manifest = _manifest()
    manifest["images"][0]["relative_path"] = "alias.png"
    report = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert report["status"] == "INVALID_OR_HASH_MISMATCH"
    (tmp_path / "folder.png").mkdir()
    manifest["images"][0]["relative_path"] = "folder.png"
    assert binder.bind_files(_invented_record(), manifest, tmp_path)["status"] == "INVALID_OR_HASH_MISMATCH"


def test_symlinked_parent_directory_not_followed(tmp_path):
    _write_images(tmp_path)
    (tmp_path / "images").symlink_to(tmp_path, target_is_directory=True)
    manifest = _manifest()
    manifest["images"][0]["relative_path"] = "images/r1.png"
    got = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"


@pytest.mark.parametrize("invalid", [
    b"NOT AN IMAGE", b"\xff\xd8\xffmissing-end", b"\x89PNG\r\n\x1a\nnot-IHDR",
])
def test_wrong_or_truncated_image_signature_detected(tmp_path, invalid):
    _write_images(tmp_path)
    (tmp_path / "r1.png").write_bytes(invalid)
    got = binder.bind_files(_invented_record(), _manifest(), tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert not any(x["source_ref"] == "test-r1" for x in got["files"])


@pytest.mark.parametrize("mutation", [
    "extra_key", "forged_claim", "wrong_kind", "duplicate_ref",
    "duplicate_path", "unknown_ref", "invalid_hash", "uppercase_hash",
    "too_many_images", "flat_manifest",
])
def test_invalid_manifest_or_ambiguous_binding_never_accepted(tmp_path, mutation):
    _write_images(tmp_path)
    manifest = _manifest()
    if mutation == "extra_key":
        manifest["unknown"] = "x"
    elif mutation == "forged_claim":
        manifest["official_gameforge_authenticated"] = True
    elif mutation == "wrong_kind":
        manifest["record_kind"] = "real_game_verified"
    elif mutation == "duplicate_ref":
        manifest["images"][1]["source_ref"] = "test-r1"
    elif mutation == "duplicate_path":
        manifest["images"][1]["relative_path"] = "r1.png"
    elif mutation == "unknown_ref":
        manifest["images"][0]["source_ref"] = "not-registered"
    elif mutation == "invalid_hash":
        manifest["images"][0]["expected_sha256"] = "a" * 63
    elif mutation == "uppercase_hash":
        manifest["images"][0]["expected_sha256"] = "A" * 64
    elif mutation == "too_many_images":
        manifest["images"].append(deepcopy(manifest["images"][0]))
    else:
        manifest["images"][0] = {"source_ref": "test-r1", "path": "r1.png"}
    got = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert got["original_game_screenshots_authenticated"] is False
    assert got["independently_verified_game_observations"] == 0


def test_duplicate_stage_source_ref_is_ambiguous_even_with_bytes(tmp_path):
    _write_images(tmp_path)
    record = _invented_record()
    record["source_refs"]["r2_prefire"] = "test-r1"
    record["observations"][1]["source_ref"] = "test-r1"
    got = binder.bind_files(record, _manifest(), tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert any("ambiguous duplicate" in x for x in got["invalid_manifest_or_file_errors"])


def test_partial_transcription_can_bind_some_local_sources_without_claiming_ready(tmp_path):
    _write_images(tmp_path)
    record = _invented_record()
    record["observations"][0]["units_alive"] = None
    manifest = _manifest()
    manifest["images"] = manifest["images"][:1]
    got = binder.bind_files(record, manifest, tmp_path)
    assert got["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert got["manual_transcription_status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert got["missing_or_unbound_source_refs"] == ["test-r2", "test-setup"]
    assert got["files"][0]["source_ref"] == "test-r1"
    assert got["official_game_mechanism_verified"] is False


def test_source_manifest_empty_image_list_is_partial(tmp_path):
    record = _invented_record()
    manifest = _manifest()
    manifest["images"] = []
    got = binder.bind_files(record, manifest, tmp_path)
    assert got["status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert got["files"] == []
    assert len(got["missing_or_unbound_source_refs"]) == 3


def test_user_report_without_real_record_never_produces_bytes_verified(tmp_path):
    _write_images(tmp_path)
    got = binder.bind_files(archive.blank_template(), _manifest(), tmp_path)
    assert got["status"] == "INVALID"
    assert got["files"] == []
    assert got["manual_transcription_status"] == "EMPTY_TEMPLATE"


def test_size_bound_disallows_oversized_untrusted_bytes(tmp_path, monkeypatch):
    _write_images(tmp_path)
    monkeypatch.setattr(binder, "MAX_IMAGE_BYTES", 16)
    got = binder.bind_files(_invented_record(), _manifest(), tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert got["local_file_bytes_read"] == 0


def test_nested_ordinary_local_file_is_supported(tmp_path):
    _write_images(tmp_path)
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "r1.png").write_bytes(FAKE_PNG_HEADER)
    manifest = _manifest()
    manifest["images"][0]["relative_path"] = "nested/r1.png"
    got = binder.bind_files(_invented_record(), manifest, tmp_path)
    assert got["status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert got["files"][0]["relative_path"] == "nested/r1.png"


def test_unreadable_or_digest_mismatched_stage_is_not_counted_as_bound(tmp_path):
    _write_images(tmp_path)
    record, manifest = _invented_record(), _manifest()
    (tmp_path / "r1.png").unlink()
    manifest["images"][1]["expected_sha256"] = "0" * 64
    result = binder.bind_files(record, manifest, tmp_path)
    assert result["status"] == "INVALID_OR_HASH_MISMATCH"
    assert result["missing_or_unbound_source_refs"] == ["test-r1", "test-r2"]
    assert result["local_file_bytes_read"] > 0
    assert result["original_game_screenshots_authenticated"] is False


def test_duplicate_stage_label_does_not_read_even_one_local_file(tmp_path):
    _write_images(tmp_path)
    record = _invented_record()
    record["source_refs"]["r2_prefire"] = record["source_refs"]["r1_end"]
    got = binder.bind_files(record, _manifest(), tmp_path)
    assert got["status"] == "INVALID_OR_HASH_MISMATCH"
    assert got["local_file_bytes_read"] == 0
    assert got["files"] == []


@pytest.mark.parametrize("mutation", ["wrong_schema", "wrong_kind", "forged_flag"])
def test_incorrect_manifest_header_rejected_before_file_access(tmp_path, mutation):
    _write_images(tmp_path)
    raw = _manifest()
    if mutation == "wrong_schema":
        raw["schema"] = "p0_naval_capture_falsely_verified"
    elif mutation == "wrong_kind":
        raw["record_kind"] = "official_gameforge"
    else:
        raw["authenticated_gameforge_screenshot"] = True
    out = binder.bind_files(_invented_record(), raw, tmp_path)
    assert out["status"] == "INVALID_OR_HASH_MISMATCH"
    assert out["local_file_bytes_read"] == 0
    assert out["files"] == []
