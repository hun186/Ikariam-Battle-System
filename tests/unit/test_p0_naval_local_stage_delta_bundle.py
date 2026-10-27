"""Invented image headers and invented navy labels ONLY; not game evidence."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.research import p0_naval_capture_archive as archive
from tools.research import p0_naval_capture_local_image_manifest as binder
from tools.research import p0_naval_local_stage_delta_bundle as bundle

FAKE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(20)
FAKE_JPEG = b"\xff\xd8\xff" + bytes(20) + b"\xff\xd9"


def invented_record():
    return {
        "schema": archive.SCHEMA, "record_kind": archive.TRANSCRIPTION,
        "record_id": "INVENTED_UNVERIFIED_BUNDLE",
        "source_refs": {"r1_end": "fake-r1", "r2_prefire": "fake-r2",
                        "fleet_setup": "fake-setup"},
        "battle_context": {
            "battlefield_id": "naval-small",
            "attacker_forge_level": 0, "defender_forge_level": 3,
            "attacker_units": {"barbarian_wedge_paddler": 5},
            "defender_units": {"carrier": 3},
            "workshop_upgrades": {
                "attacker": {"barbarian_wedge_paddler": {"attack": 0, "armor": 0}},
                "defender": {"carrier": {"attack": 1, "armor": 2}}},
            "reinforcements_between": "none", "r2_prefire_confirmed": True},
        "observations": [
            {"phase": "r1_end", "side": "defender", "unit_id": "carrier",
             "wave_label": "invented-wave", "physical_slot_label": "invented-A",
             "visible_percent": 53, "units_alive": 3, "source_ref": "fake-r1"},
            {"phase": "r2_prefire", "side": "defender", "unit_id": "carrier",
             "wave_label": "invented-wave", "physical_slot_label": "invented-A",
             "visible_percent": 65, "units_alive": 3, "source_ref": "fake-r2"},
        ],
    }


def invented_manifest(include_setup=True):
    entries = [
        {"source_ref": "fake-r1", "relative_path": "r1.png",
         "expected_sha256": None},
        {"source_ref": "fake-r2", "relative_path": "r2.jpg",
         "expected_sha256": None},
    ]
    if include_setup:
        entries.append({"source_ref": "fake-setup",
                        "relative_path": "setup.png", "expected_sha256": None})
    return {"schema": binder.SCHEMA,
            "record_kind": "user_supplied_unverified_files", "images": entries}


def fake_images(root):
    (root / "r1.png").write_bytes(FAKE_PNG)
    (root / "r2.jpg").write_bytes(FAKE_JPEG)
    (root / "setup.png").write_bytes(FAKE_PNG + b"distinct-invented")


def test_locally_bound_deltas_never_prove_game_mechanics(tmp_path):
    fake_images(tmp_path)
    rec, manifest = invented_record(), invented_manifest()
    before = deepcopy(rec), deepcopy(manifest)
    got = bundle.compare_local_bundle(rec, manifest, tmp_path)
    assert got["status"] == bundle.READY
    assert got["binding_transcription_sha256_matches"]
    assert got["manual_transcription_sha256"] == archive.archive(rec)["user_record_sha256"]
    assert got["image_binding_status"] == "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    assert got["local_image_bytes_sha256_by_stage"] == {
        "r1_end": sha256(FAKE_PNG).hexdigest(),
        "r2_prefire": sha256(FAKE_JPEG).hexdigest(),
    }
    assert len(got["candidate_label_matches"]) == 1
    row = got["candidate_label_matches"][0]
    assert row["visible_percentage_point_delta_r2_minus_r1"] == 12
    assert row["units_alive_delta_r2_minus_r1"] == 0
    assert not got["official_game_mechanism_verified"]
    assert not got["original_game_screenshots_authenticated"]
    assert not got["physical_ship_identity_independently_verified"]
    assert got["independent_holdouts"] == 0
    assert rec == before[0] and manifest == before[1]
    assert "relative_path" not in json.dumps(got)
    assert "INVENTED_UNVERIFIED_BUNDLE" not in json.dumps(got)


def test_missing_only_optional_setup_image_keeps_r1_r2_local_bytes(tmp_path):
    fake_images(tmp_path)
    got = bundle.compare_local_bundle(invented_record(),
                                      invented_manifest(include_setup=False),
                                      tmp_path)
    assert got["image_binding_status"] == "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    assert "fake-setup" in got["image_missing_or_unbound_source_refs"]
    assert got["status"] == bundle.READY
    assert len(got["candidate_label_matches"]) == 1


@pytest.mark.parametrize("failed_phase", ["r1_end", "r2_prefire"])
def test_missing_required_stage_file_fails_closed(tmp_path, failed_phase):
    fake_images(tmp_path)
    rec, manifest = invented_record(), invented_manifest()
    path = tmp_path / ("r1.png" if failed_phase == "r1_end" else "r2.jpg")
    path.unlink()
    got = bundle.compare_local_bundle(rec, manifest, tmp_path)
    assert got["status"] == bundle.INVALID
    assert not got["candidate_label_matches"]
    assert not got["local_image_bytes_sha256_by_stage"]
    assert got["image_binding_errors"]


def test_different_file_content_with_stale_expected_digest_blocks_deltas(tmp_path):
    fake_images(tmp_path)
    manifest = invented_manifest()
    manifest["images"][0]["expected_sha256"] = sha256(FAKE_PNG).hexdigest()
    (tmp_path / "r1.png").write_bytes(FAKE_PNG + b"mutated")
    got = bundle.compare_local_bundle(invented_record(), manifest, tmp_path)
    assert got["status"] == bundle.INVALID
    assert got["candidate_label_matches"] == []
    assert any("SHA-256" in error for error in got["image_binding_errors"])


def test_identical_stage_file_bytes_rejected_even_with_matching_hashes(tmp_path):
    fake_images(tmp_path)
    manifest = invented_manifest()
    (tmp_path / "r2.jpg").unlink()
    (tmp_path / "r2.png").write_bytes(FAKE_PNG)
    manifest["images"][1]["relative_path"] = "r2.png"
    for row in manifest["images"][:2]:
        row["expected_sha256"] = sha256(FAKE_PNG).hexdigest()
    got = bundle.compare_local_bundle(invented_record(), manifest, tmp_path)
    assert got["status"] == bundle.INVALID
    assert not got["candidate_label_matches"]
    assert any("identical image bytes" in e for e in got["image_binding_errors"])


def test_wrong_transcription_stage_labels_cannot_reuse_old_manifest(tmp_path):
    fake_images(tmp_path)
    rec = invented_record()
    rec["source_refs"]["r2_prefire"] = "new-transcript-label"
    rec["observations"][1]["source_ref"] = "new-transcript-label"
    got = bundle.compare_local_bundle(rec, invented_manifest(), tmp_path)
    assert got["status"] == bundle.INVALID
    assert not got["candidate_label_matches"]
    assert got["image_binding_errors"]


def test_unknown_reinforcements_do_not_become_healing_comparison(tmp_path):
    fake_images(tmp_path)
    rec = invented_record()
    rec["battle_context"]["reinforcements_between"] = "unknown"
    got = bundle.compare_local_bundle(rec, invented_manifest(), tmp_path)
    assert got["status"] == bundle.PARTIAL
    assert got["candidate_label_matches"] == []
    assert got["local_image_bytes_sha256_by_stage"]["r1_end"]
    assert any("reinforcements_between" in x
               for x in got["comparability_blockers"])


def test_conflicting_slot_does_not_become_comparable_with_real_bytes(tmp_path):
    fake_images(tmp_path)
    rec = invented_record()
    row = deepcopy(rec["observations"][0])
    row["wave_label"] = "another-invented-wave"
    row["source_ref"] = None
    rec["observations"].append(row)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    got = bundle.compare_local_bundle(rec, invented_manifest(), tmp_path)
    assert got["status"] == bundle.PARTIAL
    assert got["candidate_label_matches"] == []
    assert len(got["stage_pair_ambiguous_physical_slots"]) == 1


def test_invalid_archive_does_not_return_byte_gated_candidate(tmp_path):
    fake_images(tmp_path)
    got = bundle.compare_local_bundle(archive.blank_template(),
                                      invented_manifest(), tmp_path)
    assert got["status"] == bundle.INVALID
    assert not got["candidate_label_matches"]
    assert got["independently_verified_game_observations"] == 0


def test_symlink_stage_image_is_rejected_not_read(tmp_path):
    fake_images(tmp_path)
    (tmp_path / "r1.png").unlink()
    (tmp_path / "r1.png").symlink_to(tmp_path / "setup.png")
    got = bundle.compare_local_bundle(invented_record(), invented_manifest(),
                                      tmp_path)
    assert got["status"] == bundle.INVALID
    assert not got["candidate_label_matches"]


def test_cli_writes_unverified_bundle_no_original_image_bytes(tmp_path, monkeypatch):
    fake_images(tmp_path)
    src, manifest, out = [tmp_path / n for n in ("record.json",
                                                   "manifest.json",
                                                   "result.json")]
    src.write_text(json.dumps(invented_record()), encoding="utf-8")
    manifest.write_text(json.dumps(invented_manifest()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["bundle.py", "--record", str(src),
        "--manifest", str(manifest), "--evidence-root", str(tmp_path),
        "--output-json", str(out)])
    bundle.main()
    got = json.loads(out.read_text(encoding="utf-8"))
    assert got["status"] == bundle.READY
    assert len(got["candidate_label_matches"]) == 1


def test_cli_invalid_image_exits_two_and_writes_diagnostics(tmp_path, monkeypatch):
    fake_images(tmp_path)
    (tmp_path / "r1.png").unlink()
    src, manifest, out = [tmp_path / n for n in ("record.json",
                                                   "manifest.json",
                                                   "result.json")]
    src.write_text(json.dumps(invented_record()), encoding="utf-8")
    manifest.write_text(json.dumps(invented_manifest()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["bundle.py", "--record", str(src),
        "--manifest", str(manifest), "--evidence-root", str(tmp_path),
        "--output-json", str(out)])
    with pytest.raises(SystemExit) as exc:
        bundle.main()
    assert exc.value.code == 2
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == bundle.INVALID
