"""Invented only: synthetic bytes and labels, never real Gameforge observations."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.research import p0_naval_capture_archive as archive
from tools.research import p0_naval_capture_local_image_manifest as images
from tools.research import p0_naval_conditional_hp_intervals as hp_intervals
from tools.research.p0_naval_hp_bar_inverse_bounds import display_percent

FAKE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(20)
FAKE_JPG = b"\xff\xd8\xff" + bytes(24) + b"\xff\xd9"


def invented(tmp_path):
    (tmp_path / "r1.png").write_bytes(FAKE_PNG)
    (tmp_path / "r2.jpeg").write_bytes(FAKE_JPG)
    (tmp_path / "setup.png").write_bytes(FAKE_PNG + b"fake-different")
    rec = {
        "schema": archive.SCHEMA, "record_kind": archive.TRANSCRIPTION,
        "record_id": "INVENTED_NO_GAME",
        "source_refs": {
            "r1_end": "test-r1", "r2_prefire": "test-r2", "fleet_setup": "test-setup"},
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
             "wave_label": "invented-wave", "physical_slot_label": "slot-A",
             "visible_percent": 53, "units_alive": 3, "source_ref": "test-r1"},
            {"phase": "r2_prefire", "side": "defender", "unit_id": "carrier",
             "wave_label": "invented-wave", "physical_slot_label": "slot-A",
             "visible_percent": 65, "units_alive": 3, "source_ref": "test-r2"},
        ],
    }
    manifest = {
        "schema": images.SCHEMA, "record_kind": "user_supplied_unverified_files",
        "images": [
            {"source_ref": "test-r1", "relative_path": "r1.png", "expected_sha256": None},
            {"source_ref": "test-r2", "relative_path": "r2.jpeg", "expected_sha256": None},
            {"source_ref": "test-setup", "relative_path": "setup.png", "expected_sha256": None},
        ]}
    assumptions = {
        "schema": hp_intervals.ASSUMPTIONS_SCHEMA,
        "denominator_assumption": hp_intervals.DENOMINATOR,
        "unit_hp_by_unit_id": {"carrier": 100}}
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    return rec, manifest, assumptions


def test_positive_hp_bounds_not_causal_healing(tmp_path):
    record, manifest, assumptions = invented(tmp_path)
    original = deepcopy(record), deepcopy(manifest), deepcopy(assumptions)
    out = hp_intervals.analyze(record, manifest, tmp_path, assumptions)
    assert out["status"] == hp_intervals.COMPLETE
    assert out["upstream_status"] == "UNVERIFIED_STAGE_DELTAS_LOCAL_BYTES_BOUND"
    assert len(out["conditional_slot_ranges"]) == 1
    row = out["conditional_slot_ranges"][0]
    assert row["positive_hp_increase_required_across_all_three_modes"]
    for mode, item in row["rounding_mode_intervals"].items():
        assert item["compatible_with_display_model"]
        assert item["conditional_positive_increase_required"]
        a, b = item["r1_remaining_wounds_hp_interval"]
        c, d = item["r2_remaining_wounds_hp_interval"]
        assert item["conditional_net_hp_increase_interval"] == [a - d, b - c]
        assert all(display_percent(300 - wound, 300, mode) == 53 for wound in (a, b))
        assert all(display_percent(300 - wound, 300, mode) == 65 for wound in (c, d))
    assert not row["same_physical_survivors_verified"]
    assert not row["tender_repair_causation_verified"]
    assert not out["official_tender_healing_verified"]
    assert not out["official_hp_bar_rounding_verified"]
    assert out["independent_holdouts"] == 0
    assert record == original[0] and manifest == original[1] and assumptions == original[2]
    assert "relative_path" not in json.dumps(out)
    assert "INVENTED_NO_GAME" not in json.dumps(out)


@pytest.mark.parametrize("start,end,expected", [
    (53, 65, "up"), (65, 53, "down"), (65, 65, "zero_possible")])
def test_positive_negative_and_same_bar(tmp_path, start, end, expected):
    r, m, h = invented(tmp_path)
    r["observations"][0]["visible_percent"] = start
    r["observations"][1]["visible_percent"] = end
    out = hp_intervals.analyze(r, m, tmp_path, h)
    row = out["conditional_slot_ranges"][0]
    for q in row["rounding_mode_intervals"].values():
        lo, hi = q["conditional_net_hp_increase_interval"]
        if expected == "up":
            assert lo > 0
        elif expected == "down":
            assert hi < 0
        else:
            assert lo <= 0 <= hi


def test_changed_alive_count_blocks_hp_denominator_comparison(tmp_path):
    r, m, h = invented(tmp_path)
    r["observations"][1]["units_alive"] = 2
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert not out["conditional_slot_ranges"]
    assert out["not_assessable_slot_labels"][0]["reason"].startswith("different_living")


def test_missing_hp_skips_instead_of_guessing_unit_stats(tmp_path):
    r, m, h = invented(tmp_path)
    h["unit_hp_by_unit_id"] = {}
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert not out["conditional_slot_ranges"]
    assert out["not_assessable_slot_labels"][0]["reason"] == "missing_user_supplied_unit_hp"


@pytest.mark.parametrize("bad", [True, 0, -1, 1.5, "100", 1000001])
def test_invalid_unit_hp_rejects_before_local_file_reads(tmp_path, bad):
    r, m, h = invented(tmp_path)
    h["unit_hp_by_unit_id"]["carrier"] = bad
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.INVALID
    assert out["upstream_status"] == "NOT_EVALUATED"
    assert out["conditional_slot_ranges"] == []


def test_assumption_schema_and_denominator_must_be_explicit(tmp_path):
    r, m, h = invented(tmp_path)
    h["denominator_assumption"] = "official_gameforge_rule"
    assert hp_intervals.analyze(r, m, tmp_path, h)["status"] == hp_intervals.INVALID
    h["denominator_assumption"] = hp_intervals.DENOMINATOR
    h["schema"] = "anything_else"
    assert hp_intervals.analyze(r, m, tmp_path, h)["status"] == hp_intervals.INVALID


def test_missing_or_tampered_image_never_releases_intervals(tmp_path):
    r, m, h = invented(tmp_path)
    m["images"][0]["expected_sha256"] = sha256(FAKE_PNG).hexdigest()
    (tmp_path / "r1.png").write_bytes(FAKE_PNG + b"tampered")
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.GATED
    assert not out["conditional_slot_ranges"]
    assert out["local_image_bytes_sha256_by_stage"] == {}


def test_unknown_reinforcements_prevent_candidate_intervals(tmp_path):
    r, m, h = invented(tmp_path)
    r["battle_context"]["reinforcements_between"] = "unknown"
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert out["conditional_slot_ranges"] == []


def test_colliding_wave_with_wrong_source_does_not_infer_hp(tmp_path):
    r, m, h = invented(tmp_path)
    conflict = deepcopy(r["observations"][0])
    conflict["wave_label"] = "different-wave"
    conflict["source_ref"] = None
    r["observations"].append(conflict)
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert not out["conditional_slot_ranges"]


def test_unassessed_other_unit_keeps_clean_slot_as_conditional(tmp_path):
    r, m, h = invented(tmp_path)
    for row in deepcopy(r["observations"]):
        row["unit_id"] = "tender"
        row["physical_slot_label"] = "slot-B"
        r["observations"].append(row)
    r["battle_context"]["defender_units"]["tender"] = 3
    r["battle_context"]["workshop_upgrades"]["defender"]["tender"] = {
        "attack": 0, "armor": 0}
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert len(out["conditional_slot_ranges"]) == 1
    assert len(out["not_assessable_slot_labels"]) == 1


def test_small_capacity_rounding_incompatibility_stays_partial(tmp_path):
    r, m, h = invented(tmp_path)
    h["unit_hp_by_unit_id"]["carrier"] = 1
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.PARTIAL
    assert not out["conditional_slot_ranges"][0]["all_three_rounding_modes_compatible"]
    assert not out["conditional_slot_ranges"][0]["positive_hp_increase_required_across_all_three_modes"]


def test_invalid_archive_does_not_return_interval(tmp_path):
    r, m, h = invented(tmp_path)
    r["schema"] = "invalid_archival_schema"
    out = hp_intervals.analyze(r, m, tmp_path, h)
    assert out["status"] == hp_intervals.GATED
    assert not out["conditional_slot_ranges"]


def test_cli_writes_only_conditional_ranges(tmp_path, monkeypatch):
    r, m, h = invented(tmp_path)
    paths = [tmp_path / name for name in ("record.json", "manifest.json",
                                           "assumptions.json", "output.json")]
    for path, item in zip(paths, (r, m, h)):
        path.write_text(json.dumps(item), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py",
        "--record", str(paths[0]), "--manifest", str(paths[1]),
        "--hp-assumptions", str(paths[2]), "--evidence-root", str(tmp_path),
        "--output-json", str(paths[3])])
    hp_intervals.main()
    assert json.loads(paths[3].read_text(encoding="utf-8"))["status"] == hp_intervals.COMPLETE


def test_cli_invalid_hp_exits_two(tmp_path, monkeypatch):
    r, m, h = invented(tmp_path)
    h["unit_hp_by_unit_id"]["carrier"] = "bad"
    paths = [tmp_path / name for name in ("record.json", "manifest.json",
                                           "assumptions.json", "output.json")]
    for path, item in zip(paths, (r, m, h)):
        path.write_text(json.dumps(item), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py",
        "--record", str(paths[0]), "--manifest", str(paths[1]),
        "--hp-assumptions", str(paths[2]), "--evidence-root", str(tmp_path),
        "--output-json", str(paths[3])])
    with pytest.raises(SystemExit) as err:
        hp_intervals.main()
    assert err.value.code == 2
    assert json.loads(paths[3].read_text(encoding="utf-8"))["status"] == hp_intervals.INVALID
