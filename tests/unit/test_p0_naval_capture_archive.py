"""Adversarial archival tests; ALL observations in this file are INVENTED."""
from copy import deepcopy
import json

import pytest

from tools.research import p0_naval_capture_archive as archive


def invented_other_fleet():
    record = archive.blank_template()
    record["record_kind"] = archive.TRANSCRIPTION
    record["record_id"] = "TEST_ONLY_UNVERIFIED_ANOTHER_NAVAL_FLEET"
    record["source_refs"] = {
        "r1_end": "FAKE_TEST_REFERENCE_R1", "r2_prefire": "FAKE_TEST_REFERENCE_R2",
        "fleet_setup": "FAKE_TEST_REFERENCE_SETUP",
    }
    record["battle_context"] = {
        "battlefield_id": "naval-small",
        "attacker_forge_level": 0,
        "defender_forge_level": 3,
        "attacker_units": {"barbarian_wedge_paddler": 10},
        "defender_units": {"carrier": 5, "tender": 2},
        "workshop_upgrades": {"carrier": {"attack": 1, "armor": 2}},
        "reinforcements_between": "none",
        "r2_prefire_confirmed": True,
    }
    record["observations"] = [
        {
            "phase": "r1_end", "side": "defender", "unit_id": "carrier",
            "wave_label": "source_user_wave_1",
            "physical_slot_label": "visible_slot_L", "visible_percent": 53,
            "units_alive": 3, "source_ref": "FAKE_TEST_REFERENCE_R1",
        },
        {
            "phase": "r2_prefire", "side": "defender", "unit_id": "carrier",
            "wave_label": "source_user_wave_1",
            "physical_slot_label": "visible_slot_L", "visible_percent": 65,
            "units_alive": 3, "source_ref": "FAKE_TEST_REFERENCE_R2",
        },
    ]
    return record


def test_blank_archive_template_is_not_empirical_evidence():
    template = archive.blank_template()
    result = archive.archive(template)
    assert result["status"] == "EMPTY_TEMPLATE"
    assert template["observations"] == []
    assert result["user_submitted_record"] is None
    assert result["user_record_sha256"] is None
    assert not result["official_game_mechanism_verified"]
    assert result["independently_verified_game_observations"] == 0


def test_different_fleet_can_be_retained_without_fake_tender_screening():
    record = invented_other_fleet()
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert got["missing_for_followup"] == []
    assert got["user_submitted_record"] == record
    assert got["user_record_sha256"] and len(got["user_record_sha256"]) == 64
    assert not got["user_record_digest_is_screenshot_hash"]
    assert got["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"] is False
    assert "battlefield_id" in got["synthetic_setup_comparison"]["nonmatching_or_missing_fields"]
    assert not got["synthetic_setup_comparison"]["comparison_performed"]
    assert not got["official_game_mechanism_verified"]
    assert got["independent_holdouts"] == 0


def test_matching_named_control_only_identifies_setup_never_game_mechanism():
    existing = archive._expected_control_setup()
    record = invented_other_fleet()
    setup = record["battle_context"]
    for field in ("battlefield_id", "attacker_forge_level", "defender_forge_level",
                  "attacker_units", "defender_units"):
        setup[field] = existing[field]
    setup["workshop_upgrades"] = {
        "ram_ship": {
            "attack": existing["ram_ship_attack_upgrade"],
            "armor": existing["ram_ship_armor_upgrade"],
        },
        "steam_ram": {
            "attack": existing["steam_ram_attack_upgrade"],
            "armor": existing["steam_ram_armor_upgrade"],
        },
    }
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert got["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"]
    assert got["synthetic_setup_comparison"]["game_battle_identity_verified"] is False
    assert got["conditional_hp_model_comparison_performed"] is False
    assert got["independently_verified_game_observations"] == 0


def test_incomplete_transcription_is_not_lost_or_called_verified():
    record = invented_other_fleet()
    record["record_id"] = ""
    record["source_refs"]["r1_end"] = ""
    record["battle_context"]["attacker_forge_level"] = None
    record["observations"][0]["wave_label"] = None
    record["observations"][0]["source_ref"] = None
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert got["user_submitted_record"] == record
    assert "source_refs.r1_end" in got["missing_for_followup"]
    assert "record_id" in got["missing_for_followup"]
    assert "battle_context.attacker_forge_level" in got["missing_for_followup"]
    assert "observations[0].source_ref" in got["missing_for_followup"]
    assert got["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"] is False
    assert got["official_game_mechanism_verified"] is False


def test_missing_r1_while_retaining_r2_remains_incomplete():
    record = invented_other_fleet()
    record["observations"] = [record["observations"][1]]
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert "observations.r1_end" in got["missing_for_followup"]
    assert got["user_submitted_record"]["observations"][0]["phase"] == "r2_prefire"


def test_mismatched_source_ref_is_flagged_but_record_kept():
    record = invented_other_fleet()
    record["observations"][1]["source_ref"] = "not-the-r2-reference"
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert "observations[1].source_ref_mismatch" in got["missing_for_followup"]
    assert got["user_submitted_record"] == record


def test_same_labeled_slot_can_be_recorded_across_distinct_phases():
    record = invented_other_fleet()
    assert archive.archive(record)["status"] == "UNVERIFIED_ARCHIVE_READY"
    record["observations"].append(deepcopy(record["observations"][1]))
    got = archive.archive(record)
    assert got["status"] == "INVALID"
    assert got["user_submitted_record"] is None
    assert any("duplicate labeled physical Slot" in message for message in got["invalid_fields"])


@pytest.mark.parametrize("mutation", [
    "root_official_claim", "context_official_claim", "bar_official_claim",
    "extra_bad_workshop", "invalid_negative_population", "boolean_population",
    "boolean_percent", "invalid_percent", "boolean_forge", "boolean_prefire",
    "bad_phase", "bad_side", "nonstring_wave", "bad_unit_id",
    "bad_ref_type", "nonfinite_percent", "unsupported_field",
])
def test_invalid_or_forged_evidence_is_never_archived_as_confirmed(mutation):
    record = invented_other_fleet()
    row = record["observations"][0]
    ctx = record["battle_context"]
    if mutation == "root_official_claim":
        record["official_game_mechanic_verified"] = True
    elif mutation == "context_official_claim":
        ctx["gameforge_confirmed"] = True
    elif mutation == "bar_official_claim":
        row["official_hit_point_bar"] = True
    elif mutation == "extra_bad_workshop":
        ctx["workshop_upgrades"]["carrier"]["official"] = 1
    elif mutation == "invalid_negative_population":
        row["units_alive"] = -4
    elif mutation == "boolean_population":
        row["units_alive"] = True
    elif mutation == "boolean_percent":
        row["visible_percent"] = False
    elif mutation == "invalid_percent":
        row["visible_percent"] = 101
    elif mutation == "boolean_forge":
        ctx["defender_forge_level"] = True
    elif mutation == "boolean_prefire":
        ctx["r2_prefire_confirmed"] = 1
    elif mutation == "bad_phase":
        row["phase"] = []
    elif mutation == "bad_side":
        row["side"] = "all"
    elif mutation == "nonstring_wave":
        row["wave_label"] = ["user1"]
    elif mutation == "bad_unit_id":
        row["unit_id"] = ""
    elif mutation == "bad_ref_type":
        record["source_refs"]["r1_end"] = {"uri": "fake"}
    elif mutation == "nonfinite_percent":
        row["visible_percent"] = float("nan")
    else:
        record["unknown"] = "should fail closed"
    got = archive.archive(record)
    assert got["status"] == "INVALID"
    assert got["user_submitted_record"] is None
    assert got["user_record_sha256"] is None
    assert not got["official_game_mechanism_verified"]


def test_reordered_json_keys_have_stable_transcription_digest():
    raw = invented_other_fleet()
    other = json.loads(json.dumps(raw, sort_keys=True))
    x, y = archive.archive(raw), archive.archive(other)
    assert x["status"] == y["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert x["user_record_sha256"] == y["user_record_sha256"]
    assert x["user_record_digest_is_screenshot_hash"] is False
    other["observations"][0]["visible_percent"] = 54
    z = archive.archive(other)
    assert z["user_record_sha256"] != x["user_record_sha256"]
    assert z["source_class"] == archive.SOURCE_CLASS


def test_archive_does_not_mutate_input_and_accepts_no_named_physical_slot():
    row = invented_other_fleet()
    row["observations"][0]["physical_slot_label"] = None
    previous = deepcopy(row)
    got = archive.archive(row)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert row == previous
    assert "observations[0].physical_slot_label" in got["missing_for_followup"]
    assert got["user_submitted_record"]["observations"][0]["visible_percent"] == 53
