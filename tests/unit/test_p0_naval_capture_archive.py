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
        "workshop_upgrades": {
            "attacker": {"barbarian_wedge_paddler": {"attack": 0, "armor": 0}},
            "defender": {
                "carrier": {"attack": 1, "armor": 2},
                "tender": {"attack": 0, "armor": 0},
            },
        },
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
        "attacker": {
            uid: {"attack": 0, "armor": 0}
            for uid in existing["attacker_units"]
        },
        "defender": {
            "ram_ship": {
                "attack": existing["ram_ship_attack_upgrade"],
                "armor": existing["ram_ship_armor_upgrade"],
            },
            "steam_ram": {
                "attack": existing["steam_ram_attack_upgrade"],
                "armor": existing["steam_ram_armor_upgrade"],
            },
            "tender": {"attack": 0, "armor": 0},
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
        ctx["workshop_upgrades"]["defender"]["carrier"]["official"] = 1
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


@pytest.mark.parametrize("field", [
    "battlefield_id", "attacker_forge_level", "defender_forge_level",
])
def test_omitted_optional_setup_keys_remain_archivable_with_followup(field):
    record = invented_other_fleet()
    record["battle_context"].pop(field)
    before = deepcopy(record)
    outcome = archive.archive(record)
    assert outcome["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert f"battle_context.{field}" in outcome["missing_for_followup"]
    assert outcome["user_submitted_record"] == before
    assert record == before
    assert outcome["user_record_sha256"]
    assert outcome["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"] is False
    assert field in outcome["synthetic_setup_comparison"]["nonmatching_or_missing_fields"]
    assert outcome["independently_verified_game_observations"] == 0
    assert outcome["official_game_mechanism_verified"] is False


@pytest.mark.parametrize("field", [
    "battlefield_id", "attacker_forge_level", "defender_forge_level",
])
def test_explicit_null_setup_keys_not_crash_informational_comparison(field):
    record = invented_other_fleet()
    record["battle_context"][field] = None
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert f"battle_context.{field}" in got["missing_for_followup"]
    assert got["synthetic_setup_comparison"]["comparison_performed"] is False
    assert got["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"] is False


@pytest.mark.parametrize(("mutation", "expected_missing"), [
    ("attacker_null_quantity", "battle_context.attacker_units.barbarian_wedge_paddler.quantity"),
    ("defender_null_quantity", "battle_context.defender_units.carrier.quantity"),
    ("missing_workshop_attack", "battle_context.workshop_upgrades.defender.carrier.attack"),
    ("missing_workshop_armor", "battle_context.workshop_upgrades.defender.carrier.armor"),
    ("null_workshop_attack", "battle_context.workshop_upgrades.defender.carrier.attack"),
    ("null_workshop_armor", "battle_context.workshop_upgrades.defender.carrier.armor"),
    ("empty_nested_workshop", "battle_context.workshop_upgrades.defender.carrier.attack"),
])
def test_nested_unknown_values_force_incomplete_without_dropping_record(
        mutation, expected_missing):
    record = invented_other_fleet()
    ctx = record["battle_context"]
    if mutation == "attacker_null_quantity":
        ctx["attacker_units"]["barbarian_wedge_paddler"] = None
    elif mutation == "defender_null_quantity":
        ctx["defender_units"]["carrier"] = None
    elif mutation == "missing_workshop_attack":
        ctx["workshop_upgrades"]["defender"]["carrier"].pop("attack")
    elif mutation == "missing_workshop_armor":
        ctx["workshop_upgrades"]["defender"]["carrier"].pop("armor")
    elif mutation == "null_workshop_attack":
        ctx["workshop_upgrades"]["defender"]["carrier"]["attack"] = None
    elif mutation == "null_workshop_armor":
        ctx["workshop_upgrades"]["defender"]["carrier"]["armor"] = None
    else:
        ctx["workshop_upgrades"]["defender"]["carrier"] = {}
    expected = deepcopy(record)
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert expected_missing in got["missing_for_followup"]
    assert got["user_submitted_record"] == expected
    assert got["user_record_sha256"] and not got["user_record_digest_is_screenshot_hash"]
    assert got["synthetic_setup_comparison"]["comparison_performed"] is False
    assert got["official_game_mechanism_verified"] is False
    assert got["independently_verified_game_observations"] == 0


def test_complete_nested_quantities_and_workshop_levels_still_ready():
    record = invented_other_fleet()
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert got["missing_for_followup"] == []
    assert got["user_submitted_record"] == record


@pytest.mark.parametrize(("row_index", "condition"), [
    (0, "explicit_null"), (0, "omitted_key"),
    (1, "explicit_null"), (1, "omitted_key"),
])
def test_missing_per_slot_survivor_counts_preserved_as_incomplete(row_index, condition):
    raw = invented_other_fleet()
    row = raw["observations"][row_index]
    if condition == "omitted_key":
        del row["units_alive"]
    else:
        row["units_alive"] = None
    original = deepcopy(raw)
    result = archive.archive(raw)
    assert result["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert result["missing_for_followup"] == [
        f"observations[{row_index}].units_alive"
    ]
    assert result["user_submitted_record"] == original
    assert raw == original
    assert result["user_record_sha256"]
    assert result["independently_verified_game_observations"] == 0
    assert result["official_game_mechanism_verified"] is False
    assert result["conditional_hp_model_comparison_performed"] is False


def test_zero_and_invalid_per_slot_survivor_counts_fail_closed():
    for invalid in (0, -1, False, True, 1.2, "12", []):
        raw = invented_other_fleet()
        raw["observations"][1]["units_alive"] = invalid
        result = archive.archive(raw)
        assert result["status"] == "INVALID"
        assert result["user_submitted_record"] is None
        assert result["user_record_sha256"] is None
        assert any("observations[1].units_alive" in e for e in result["invalid_fields"])


def test_complete_per_slot_survivors_still_ready():
    data = invented_other_fleet()
    result = archive.archive(data)
    assert result["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert result["missing_for_followup"] == []
    assert [x["units_alive"] for x in result["user_submitted_record"]["observations"]] == [3, 3]
    assert result["game_screenshot_contents_verified"] is False



@pytest.mark.parametrize(("kind", "expected_path"), [
    ("record_id", "record_id"),
    ("round1_ref", "source_refs.r1_end"),
    ("round2_ref", "source_refs.r2_prefire"),
    ("fleet_ref", "source_refs.fleet_setup"),
    ("r1_observation_ref", "observations[0].source_ref"),
    ("r2_observation_ref", "observations[1].source_ref"),
    ("r1_wave", "observations[0].wave_label"),
    ("r2_wave", "observations[1].wave_label"),
    ("r1_slot", "observations[0].physical_slot_label"),
    ("r2_slot", "observations[1].physical_slot_label"),
])
def test_whitespace_only_evidence_labels_remain_archivable_but_incomplete(kind, expected_path):
    record = invented_other_fleet()
    if kind == "record_id":
        record["record_id"] = " \t "
    elif kind == "round1_ref":
        record["source_refs"]["r1_end"] = "   "
    elif kind == "round2_ref":
        record["source_refs"]["r2_prefire"] = "\t "
    elif kind == "fleet_ref":
        record["source_refs"]["fleet_setup"] = "\n\t "
    elif kind == "r1_observation_ref":
        record["observations"][0]["source_ref"] = " \t"
    elif kind == "r2_observation_ref":
        record["observations"][1]["source_ref"] = "   "
    elif kind == "r1_wave":
        record["observations"][0]["wave_label"] = "   "
    elif kind == "r2_wave":
        record["observations"][1]["wave_label"] = "\t"
    elif kind == "r1_slot":
        record["observations"][0]["physical_slot_label"] = " \t"
    else:
        record["observations"][1]["physical_slot_label"] = "   "
    original = deepcopy(record)
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert expected_path in got["missing_for_followup"]
    assert got["user_submitted_record"] == original
    assert got["user_record_sha256"] and not got["user_record_digest_is_screenshot_hash"]
    assert got["official_game_mechanism_verified"] is False
    assert got["independently_verified_game_observations"] == 0
    assert record == original


def test_matching_whitespace_source_references_still_unfilled():
    record = invented_other_fleet()
    for name in ("r1_end", "r2_prefire", "fleet_setup"):
        record["source_refs"][name] = " \t "
    for row in record["observations"]:
        row["source_ref"] = " \t "
    got = archive.archive(record)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert all(f"source_refs.{phase}" in got["missing_for_followup"]
               for phase in ("r1_end", "r2_prefire", "fleet_setup"))
    assert all(f"observations[{i}].source_ref" in got["missing_for_followup"]
               for i in (0, 1))
    assert got["user_submitted_record"] == record
    assert got["synthetic_setup_comparison"]["comparison_performed"] is False


def test_duplicate_whitespace_only_wave_and_slot_labels_cannot_make_archive_ready():
    record = invented_other_fleet()
    sample = record["observations"][1]
    sample["wave_label"] = "   "
    sample["physical_slot_label"] = " \t "
    record["observations"].append(deepcopy(sample))
    result = archive.archive(record)
    assert result["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    for row_id in (1, 2):
        assert f"observations[{row_id}].wave_label" in result["missing_for_followup"]
        assert f"observations[{row_id}].physical_slot_label" in result["missing_for_followup"]
    assert result["user_submitted_record"] == record


def test_nonblank_valid_source_labels_and_slot_names_still_archive_ready():
    record = invented_other_fleet()
    result = archive.archive(record)
    assert result["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert result["missing_for_followup"] == []
    assert result["game_screenshot_contents_verified"] is False



def test_pvp_same_ship_can_retain_distinct_attacker_and_defender_upgrades():
    # Different Workshop levels for SAME ship type must never be flattened.
    raw = invented_other_fleet()
    ctx = raw["battle_context"]
    ctx["attacker_units"] = {"carrier": 8}
    ctx["workshop_upgrades"] = {
        "attacker": {"carrier": {"attack": 0, "armor": 0}},
        "defender": {
            "carrier": {"attack": 1, "armor": 2},
            "tender": {"attack": 0, "armor": 0},
        },
    }
    raw["observations"].append({
        "phase": "r2_prefire", "side": "attacker", "unit_id": "carrier",
        "wave_label": "attacker-wave", "physical_slot_label": "attacker-slot",
        "visible_percent": 91, "units_alive": 4,
        "source_ref": raw["source_refs"]["r2_prefire"],
    })
    got = archive.archive(raw)
    assert got["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert got["missing_for_followup"] == []
    assert got["user_submitted_record"] == raw
    assert got["user_submitted_record"]["battle_context"]["workshop_upgrades"]["attacker"]["carrier"] == {
        "attack": 0, "armor": 0
    }
    assert got["user_submitted_record"]["battle_context"]["workshop_upgrades"]["defender"]["carrier"] == {
        "attack": 1, "armor": 2
    }
    assert got["synthetic_setup_comparison"]["comparison_performed"] is False
    assert not got["official_game_mechanism_verified"]


@pytest.mark.parametrize(("side", "unit_id"), [
    ("attacker", "barbarian_wedge_paddler"),
    ("defender", "carrier"), ("defender", "tender"),
])
def test_entirely_missing_workshop_entry_for_declared_unit_is_followup(side, unit_id):
    raw = invented_other_fleet()
    del raw["battle_context"]["workshop_upgrades"][side][unit_id]
    got = archive.archive(raw)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert f"battle_context.workshop_upgrades.{side}.{unit_id}" in got["missing_for_followup"]
    assert got["user_submitted_record"] == raw
    assert got["user_record_sha256"]


@pytest.mark.parametrize("missing_side", ["attacker", "defender"])
def test_missing_side_workshop_dict_is_incomplete_not_flattened(missing_side):
    raw = invented_other_fleet()
    raw["battle_context"]["workshop_upgrades"].pop(missing_side)
    got = archive.archive(raw)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert f"battle_context.workshop_upgrades.{missing_side}" in got["missing_for_followup"]
    assert got["user_submitted_record"] == raw
    assert got["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"] is False


@pytest.mark.parametrize("attribute", ["attack", "armor"])
def test_missing_or_null_side_specific_workshop_fields_incomplete(attribute):
    raw = invented_other_fleet()
    raw["battle_context"]["workshop_upgrades"]["attacker"]["barbarian_wedge_paddler"].pop(attribute)
    first = archive.archive(raw)
    assert first["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    path = f"battle_context.workshop_upgrades.attacker.barbarian_wedge_paddler.{attribute}"
    assert path in first["missing_for_followup"]
    raw["battle_context"]["workshop_upgrades"]["attacker"]["barbarian_wedge_paddler"][attribute] = None
    second = archive.archive(raw)
    assert second["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert path in second["missing_for_followup"]


@pytest.mark.parametrize("invalid", [
    {"carrier": {"attack": 1, "armor": 2}},
    {"spectator": {"carrier": {"attack": 1, "armor": 2}}},
    {"attacker": {"carrier": {"attack": False, "armor": 0}}, "defender": {}},
    {"attacker": [], "defender": {}},
])
def test_unscoped_or_malformed_workshop_rejected_instead_of_silent_ready(invalid):
    raw = invented_other_fleet()
    raw["battle_context"]["workshop_upgrades"] = invalid
    got = archive.archive(raw)
    assert got["status"] == "INVALID"
    assert got["user_submitted_record"] is None
    assert got["user_record_sha256"] is None


def test_other_ship_workshop_values_do_not_hide_unrecorded_carrier():
    raw = invented_other_fleet()
    raw["battle_context"]["workshop_upgrades"]["defender"] = {
        "ram_ship": {"attack": 0, "armor": 0},
        "tender": {"attack": 0, "armor": 0},
    }
    got = archive.archive(raw)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert "battle_context.workshop_upgrades.defender.carrier" in got["missing_for_followup"]
    assert got["user_submitted_record"] == raw


def test_observed_ship_not_declared_gets_side_population_and_upgrade_followups():
    raw = invented_other_fleet()
    raw["observations"][1]["unit_id"] = "ram_ship"
    got = archive.archive(raw)
    assert got["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE"
    assert "battle_context.defender_units.ram_ship.quantity" in got["missing_for_followup"]
    assert "battle_context.workshop_upgrades.defender.ram_ship" in got["missing_for_followup"]
    assert got["user_submitted_record"] == raw


def test_attacker_workshop_changes_in_original_synthetic_fleet_break_setup_hint():
    source = archive._expected_control_setup()
    raw = invented_other_fleet()
    ctx = raw["battle_context"]
    ctx.update({name: deepcopy(source[name]) for name in (
        "battlefield_id", "attacker_forge_level", "defender_forge_level",
        "attacker_units", "defender_units",
    )})
    ctx["workshop_upgrades"] = {
        "attacker": {
            unit_id: {"attack": 0, "armor": 0}
            for unit_id in source["attacker_units"]
        },
        "defender": {
            "ram_ship": {"attack": source["ram_ship_attack_upgrade"],
                         "armor": source["ram_ship_armor_upgrade"]},
            "steam_ram": {"attack": source["steam_ram_attack_upgrade"],
                          "armor": source["steam_ram_armor_upgrade"]},
            "tender": {"attack": 0, "armor": 0},
        },
    }
    matched = archive.archive(raw)
    assert matched["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert matched["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"]
    attacker_id = next(iter(ctx["attacker_units"]))
    ctx["workshop_upgrades"]["attacker"][attacker_id]["attack"] = 1
    different = archive.archive(raw)
    assert different["status"] == "UNVERIFIED_ARCHIVE_READY"
    assert not different["synthetic_setup_comparison"]["exact_original_synthetic_setup_fields_match"]
    assert f"attacker_workshop.{attacker_id}.attack" in different[
        "synthetic_setup_comparison"]["nonmatching_or_missing_fields"]
