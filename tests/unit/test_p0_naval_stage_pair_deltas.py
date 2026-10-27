"""Invented-only naval source rows; no real Gameforge observations."""
from copy import deepcopy
import json

import pytest

from tools.research import p0_naval_capture_archive as archive
from tools.research import p0_naval_stage_pair_deltas as pairs


def invented_record():
    return {
        "schema": archive.SCHEMA, "record_kind": archive.TRANSCRIPTION,
        "record_id": "SYNTHETIC_DELTA_TEST_ONLY",
        "source_refs": {
            "r1_end": "INVENTED_R1", "r2_prefire": "INVENTED_R2",
            "fleet_setup": "INVENTED_FLEET",
        },
        "battle_context": {
            "battlefield_id": "naval-small",
            "attacker_forge_level": 0, "defender_forge_level": 3,
            "attacker_units": {"barbarian_wedge_paddler": 10},
            "defender_units": {"carrier": 5},
            "workshop_upgrades": {
                "attacker": {"barbarian_wedge_paddler": {"attack": 0, "armor": 0}},
                "defender": {"carrier": {"attack": 1, "armor": 2}},
            },
            "reinforcements_between": "none", "r2_prefire_confirmed": True,
        },
        "observations": [
            {"phase": "r1_end", "side": "defender", "unit_id": "carrier",
             "wave_label": "invented-wave", "physical_slot_label": "invented-L",
             "visible_percent": 53, "units_alive": 3, "source_ref": "INVENTED_R1"},
            {"phase": "r2_prefire", "side": "defender", "unit_id": "carrier",
             "wave_label": "invented-wave", "physical_slot_label": "invented-L",
             "visible_percent": 65, "units_alive": 3, "source_ref": "INVENTED_R2"},
        ],
    }


def test_label_matching_is_arithmetic_only():
    rec = invented_record()
    orig = deepcopy(rec)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    got = pairs.compare(rec)
    assert rec == orig
    assert got["status"] == pairs.SUCCESS
    row = got["candidate_label_matches"][0]
    assert row["visible_percentage_point_delta_r2_minus_r1"] == 12
    assert row["units_alive_delta_r2_minus_r1"] == 0
    assert row["healing_causation_verified"] is False
    assert row["physical_group_identity_verified"] is False
    assert got["independently_verified_game_observations"] == 0
    assert got["official_healing_or_damage_mechanism_verified"] is False
    assert got["manual_transcription_sha256"] == archive.archive(rec)["user_record_sha256"]
    assert got["manual_transcription_digest_is_image_digest"] is False
    assert "user_submitted_record" not in got


def test_negative_changes_just_record_differences():
    rec = invented_record()
    rec["observations"][1]["visible_percent"] = 25
    rec["observations"][1]["units_alive"] = 2
    got = pairs.compare(rec)
    assert got["status"] == pairs.SUCCESS
    assert got["candidate_label_matches"][0]["visible_percentage_point_delta_r2_minus_r1"] == -28
    assert got["candidate_label_matches"][0]["units_alive_delta_r2_minus_r1"] == -1


def test_reordered_observations_do_not_change_matched_deltas():
    rec = invented_record()
    one = pairs.compare(rec)["candidate_label_matches"][0]
    rec["observations"].reverse()
    two = pairs.compare(rec)["candidate_label_matches"][0]
    for key in ("visible_percentage_point_delta_r2_minus_r1",
                "units_alive_delta_r2_minus_r1"):
        assert one[key] == two[key]


@pytest.mark.parametrize("value", ["present", "unknown", None])
def test_unknown_or_present_reinforcement_blocks_pairs(value):
    rec = invented_record()
    rec["battle_context"]["reinforcements_between"] = value
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert any("reinforcements_between" in q for q in got["comparability_blockers"])


@pytest.mark.parametrize("value", [False, None])
def test_unconfirmed_prefire_blocks_pairs(value):
    rec = invented_record()
    rec["battle_context"]["r2_prefire_confirmed"] = value
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert any("r2_prefire_confirmed" in q for q in got["comparability_blockers"])


def test_incomplete_wave_is_not_fabricated():
    rec = invented_record()
    rec["observations"][0]["wave_label"] = None
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert "observations[0].wave_label" in got["missing_for_followup"]
    assert len(got["unmatched_r2_labels"]) == 1


def test_wrong_phase_source_ref_not_pairable():
    rec = invented_record()
    rec["observations"][1]["source_ref"] = "WRONG"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert "observations[1].source_ref_mismatch" in got["missing_for_followup"]


def test_different_wave_at_same_slot_is_unmatched():
    rec = invented_record()
    rec["observations"][1]["wave_label"] = "different-wave"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert len(got["unmatched_r1_labels"]) == 1
    assert len(got["unmatched_r2_labels"]) == 1


def test_missing_stage_ref_blocks_pairing():
    rec = invented_record()
    rec["source_refs"]["r2_prefire"] = None
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert any("distinct nonblank" in q for q in got["comparability_blockers"])


def test_missing_percent_is_preserved_as_partial():
    rec = invented_record()
    rec["observations"][1]["visible_percent"] = None
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert not got["candidate_label_matches"]
    assert "observations[1].visible_percent" in got["missing_for_followup"]


def test_one_unmatched_slot_keeps_partial_status():
    rec = invented_record()
    rec["observations"].append({
        "phase": "r1_end", "side": "defender", "unit_id": "carrier",
        "wave_label": "invented-wave", "physical_slot_label": "invented-R",
        "visible_percent": 44, "units_alive": 2, "source_ref": "INVENTED_R1",
    })
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert len(got["candidate_label_matches"]) == 1
    assert len(got["unmatched_r1_labels"]) == 1


@pytest.mark.parametrize("mutation", ["empty", "invalid_schema", "duplicate_slot"])
def test_invalid_archive_never_becomes_game_evidence(mutation):
    rec = invented_record()
    if mutation == "empty":
        rec = archive.blank_template()
    elif mutation == "invalid_schema":
        rec["schema"] = "forged_gameforge_report"
    else:
        rec["observations"].append(deepcopy(rec["observations"][0]))
    got = pairs.compare(rec)
    assert got["status"] == pairs.INVALID
    assert not got["candidate_label_matches"]
    assert got["independent_holdouts"] == 0


def test_cli_partial_report_writes_without_error_exit(tmp_path, monkeypatch):
    rec = invented_record()
    rec["observations"][0]["visible_percent"] = None
    src, dst = tmp_path / "source.json", tmp_path / "result.json"
    src.write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py",
        "--input", str(src), "--output-json", str(dst)])
    pairs.main()
    assert json.loads(dst.read_text(encoding="utf-8"))["status"] == pairs.PARTIAL


def test_cli_invalid_archive_exits_2_with_diagnostics(tmp_path, monkeypatch):
    src, dst = tmp_path / "source.json", tmp_path / "result.json"
    src.write_text(json.dumps(archive.blank_template()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["script.py",
        "--input", str(src), "--output-json", str(dst)])
    with pytest.raises(SystemExit) as exc:
        pairs.main()
    assert exc.value.code == 2
    assert json.loads(dst.read_text(encoding="utf-8"))["status"] == pairs.INVALID


@pytest.mark.parametrize("conflict_phase", ["r1_end", "r2_prefire"])
def test_competing_wave_at_same_physical_slot_blocks_apparent_exact_pair(
        conflict_phase):
    rec = invented_record()
    original = deepcopy(rec)
    source_row = rec["observations"][0 if conflict_phase == "r1_end" else 1]
    conflicting = deepcopy(source_row)
    conflicting["wave_label"] = "competing-wave"
    conflicting["units_alive"] = 1
    rec["observations"].append(conflicting)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert got["candidate_label_matches"] == []
    assert len(got["ambiguous_physical_slots"]) == 1
    conflict = got["ambiguous_physical_slots"][0]
    assert conflict["phase"] == conflict_phase
    assert conflict["side"] == "defender"
    assert conflict["physical_slot_label"] == "invented-L"
    assert conflict["observation_indices"] == ([0, 2] if conflict_phase == "r1_end" else [1, 2])
    assert {x["wave_label"] for x in conflict["competing_unit_wave_labels"]} == {
        "invented-wave", "competing-wave"}
    assert conflict["physical_slot_ownership_verified"] is False
    assert got["independently_verified_game_observations"] == 0
    assert got["official_healing_or_damage_mechanism_verified"] is False
    assert rec["observations"][:2] == original["observations"]


def test_competing_ship_type_at_same_slot_excludes_only_conflicted_slot():
    rec = invented_record()
    original_r1, original_r2 = rec["observations"]
    # Keep one independent clean physical slot in both snapshots.
    for item in (original_r1, original_r2):
        clean = deepcopy(item)
        clean["physical_slot_label"] = "invented-R"
        clean["units_alive"] = 2
        rec["observations"].append(clean)
    # Another ship type self-reported at R1's very same physical position.
    colliding = deepcopy(original_r1)
    colliding["unit_id"] = "tender"
    colliding["units_alive"] = 1
    rec["observations"].append(colliding)
    # Add the contender to declared units/upgrades to avoid missing setup.
    rec["battle_context"]["defender_units"]["tender"] = 1
    rec["battle_context"]["workshop_upgrades"]["defender"]["tender"] = {
        "attack": 0, "armor": 0}
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert len(got["candidate_label_matches"]) == 1
    assert got["candidate_label_matches"][0]["physical_slot_label"] == "invented-R"
    assert got["candidate_label_matches"][0]["visible_percentage_point_delta_r2_minus_r1"] == 12
    assert got["ambiguous_physical_slots"][0]["physical_slot_label"] == "invented-L"
    assert {c["unit_id"] for c in got["ambiguous_physical_slots"][0][
        "competing_unit_wave_labels"]} == {"carrier", "tender"}


def test_distinct_sides_reusing_same_position_label_not_ambiguous():
    rec = invented_record()
    for item in rec["observations"][:]:
        other = deepcopy(item)
        other["side"] = "attacker"
        other["unit_id"] = "barbarian_wedge_paddler"
        other["units_alive"] = 2
        rec["observations"].append(other)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    got = pairs.compare(rec)
    assert got["status"] == pairs.SUCCESS
    assert len(got["candidate_label_matches"]) == 2
    assert got["ambiguous_physical_slots"] == []


def test_multiple_waves_different_slots_are_not_false_collisions():
    rec = invented_record()
    for item in rec["observations"][:]:
        other = deepcopy(item)
        other["wave_label"] = "other-wave"
        other["physical_slot_label"] = "invented-R"
        rec["observations"].append(other)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_READY"
    got = pairs.compare(rec)
    assert got["status"] == pairs.SUCCESS
    assert len(got["candidate_label_matches"]) == 2
    assert got["ambiguous_physical_slots"] == []


def test_ambiguous_slot_diagnostics_do_not_depend_on_input_order():
    rec = invented_record()
    conflict = deepcopy(rec["observations"][1])
    conflict["wave_label"] = "conflicting-wave"
    rec["observations"].append(conflict)
    first = pairs.compare(rec)
    rec["observations"].reverse()
    second = pairs.compare(rec)
    assert first["status"] == second["status"] == pairs.PARTIAL
    assert first["candidate_label_matches"] == second["candidate_label_matches"] == []
    assert (first["ambiguous_physical_slots"][0]["competing_unit_wave_labels"]
            == second["ambiguous_physical_slots"][0]["competing_unit_wave_labels"])


@pytest.mark.parametrize("conflict_phase", ["r1_end", "r2_prefire"])
@pytest.mark.parametrize("bad_source", [None, "MISMATCHED-REFERENCE"])
def test_p2_conflict_without_source_ref_still_blocks_matching_slot(
        conflict_phase, bad_source):
    rec = invented_record()
    conflicting = deepcopy(rec["observations"][
        0 if conflict_phase == "r1_end" else 1])
    conflicting["wave_label"] = "other-wave"
    conflicting["source_ref"] = bad_source
    rec["observations"].append(conflicting)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert got["candidate_label_matches"] == []
    assert len(got["ambiguous_physical_slots"]) == 1
    conflict = got["ambiguous_physical_slots"][0]
    assert conflict["phase"] == conflict_phase
    assert conflict["observation_indices"] == (
        [0, 2] if conflict_phase == "r1_end" else [1, 2])
    assert {q["wave_label"] for q in conflict["competing_unit_wave_labels"]} == {
        "invented-wave", "other-wave"}
    assert got["independently_verified_game_observations"] == 0


def test_p2_unknown_wave_at_occupied_slot_blocks_apparent_pair():
    rec = invented_record()
    uncertain = deepcopy(rec["observations"][0])
    uncertain["wave_label"] = None
    rec["observations"].append(uncertain)
    assert archive.archive(rec)["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert got["candidate_label_matches"] == []
    labels = got["ambiguous_physical_slots"][0]["competing_unit_wave_labels"]
    assert {row["wave_label"] for row in labels} == {None, "invented-wave"}


def test_p2_bad_source_collision_does_not_discard_clean_other_slot():
    rec = invented_record()
    for item in deepcopy(rec["observations"]):
        item["physical_slot_label"] = "clean-R"
        rec["observations"].append(item)
    conflicting = deepcopy(rec["observations"][0])
    conflicting["wave_label"] = "untrusted-wave"
    conflicting["source_ref"] = "WRONG"
    rec["observations"].append(conflicting)
    got = pairs.compare(rec)
    assert got["status"] == pairs.PARTIAL
    assert len(got["candidate_label_matches"]) == 1
    assert got["candidate_label_matches"][0]["physical_slot_label"] == "clean-R"
    assert got["ambiguous_physical_slots"][0]["physical_slot_label"] == "invented-L"
