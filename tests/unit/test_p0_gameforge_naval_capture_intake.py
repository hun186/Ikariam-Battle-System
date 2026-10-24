"""Capture intake adversarial tests. Test records are INVENTED; not game evidence."""
from copy import deepcopy

import pytest

from tools.research import p0_gameforge_naval_capture_intake as intake
from tools.research import p0_naval_hp_bar_capture_discrimination as model


def _synthetic_test_record(*, mapping=intake.MAPPED, percent_mode="floor"):
    """Generate fake input from synthetic model solely for regression."""
    p = model.build_report()
    result = intake.template()
    result.update({
        "record_kind": intake.USER_TRANSCRIPTION,
        "evidence_id": "TEST_ONLY_INVENTED_CAPTURE_NOT_A_GAME_OBSERVATION",
        "source_refs": {
            "round1_end": "TEST_ONLY_R1",
            "round2_prefire": "TEST_ONLY_R2",
            "fleet_setup": "TEST_ONLY_SETUP",
        },
        "context": {
            **intake._expected_control_setup(),
            "workshop_details_captured": True,
            "reinforcements_between_snapshots": "none",
            "r2_snapshot_is_prefire": True,
        },
        "mapping_mode": mapping, "percent_rounding": percent_mode,
        "model_fleet_equivalence": intake.EQUIVALENCE_ASSERTED,
    })
    baseline = p["case_order"][0]
    channels = p["channels"]
    result["r2_prefire_bars"] = [
        {
            "unit_id": ch["unit_id"], "wave_id": ch["wave_id"],
            "model_damage_position": (
                ch["damage_position"] if mapping == intake.MAPPED else None
            ),
            "visible_percent": p["predicted_integer_percent_bars"][baseline][
                ch["channel_id"]]["floor"],
            "units_alive": ch["simulated_slot_population"] if mapping == intake.MAPPED else None,
            "source_ref": "TEST_ONLY_R2",
        } for ch in channels
    ]
    return result


def test_blank_template_is_empty_and_never_registered_as_observation():
    raw = intake.template()
    report = intake.evaluate_capture(raw)
    assert report["status"] == "TEMPLATE_ONLY"
    assert raw["r2_prefire_bars"] == []
    assert report["original_game_observations_independently_verified"] == 0
    raw["record_kind"] = intake.USER_TRANSCRIPTION
    assert intake.evaluate_capture(raw)["status"] == "NOT_COMPARABLE"


@pytest.mark.parametrize("mode", [intake.MAPPED, intake.UNMAPPED])
def test_fake_synthetic_bars_can_only_be_conditionally_screened(mode):
    row = _synthetic_test_record(mapping=mode)
    actual = intake.evaluate_capture(row)
    assert actual["status"] == "CONDITIONAL_SCREEN_ONLY"
    assert actual["input_requirements_missing_or_invalid"] == []
    assert actual["source_provenance"] == intake.PROVENANCE
    assert actual["original_game_observations_independently_verified"] == 0
    assert actual["independent_holdouts"] == 0
    assert actual["official_game_mechanism_verified"] is False
    assert actual["parsed_r2_prefire_bar_count"] == len(row["r2_prefire_bars"])
    comp = actual["conditional_model_comparison"]
    assert comp["hypothesis_count_total"] == 10
    assert comp["interpretation"] == intake.CONDITIONAL
    assert model.build_report()["case_order"][0] in comp[
        "model_hypotheses_consistent_with_supplied_bars"]
    assert len(comp["model_hypotheses_consistent_with_supplied_bars"]) + len(
        comp["model_hypotheses_inconsistent_if_all_model_assumptions_hold"]) == 10


def test_unknown_rounding_cannot_use_different_display_mode_per_slot():
    p, channels = intake._model_plan()
    cid = next(iter(channels))
    data = _synthetic_test_record()
    data["percent_rounding"] = intake.ROUND_UNKNOWN
    data["r2_prefire_bars"] = data["r2_prefire_bars"][:1]
    tested = intake.evaluate_capture(data)
    assert tested["status"] == "CONDITIONAL_SCREEN_ONLY"
    assert tested["conditional_model_comparison"]["rounding_candidates"] == list(intake.ROUNDS)
    assert p["summary"]["source_model_comparisons"] == 10
    assert cid in p["predicted_integer_percent_bars"][p["case_order"][0]]


def test_unmapped_partial_bars_allow_any_model_slot_subset():
    data = _synthetic_test_record(mapping=intake.UNMAPPED)
    # An unmapped partial record's only observed bar might be a late Slot,
    # rather than the first synthetic damage-position location.
    one = data["r2_prefire_bars"][-1]
    data["r2_prefire_bars"] = [one]
    report = intake.evaluate_capture(data)
    assert report["status"] == "CONDITIONAL_SCREEN_ONLY"
    assert model.build_report()["case_order"][0] in report[
        "conditional_model_comparison"]["model_hypotheses_consistent_with_supplied_bars"]


@pytest.mark.parametrize("patch", [
    "missing_ref", "duplicated_ref", "wrong_stage", "future_r2", "bad_tender",
    "unknown_forge", "wrong_attacker_forge", "wrong_battlefield", "wrong_initial_fleet",
    "wrong_ram_workshop", "wrong_steam_attack_upgrade", "wrong_steam_armor_upgrade",
    "missing_steam_upgrade", "unknown_workshop", "reinforcements", "unasserted_equivalence",
    "wrong_source", "duplicate_slot", "negative_bar", "boolean_bar",
    "wrong_slot_population", "invented_slot", "foreign_wave",
    "hidden_address_with_unmapped_mode", "extra_official_proof_field",
])
def test_reject_unverified_or_incompatible_observation(patch):
    data = _synthetic_test_record()
    row = data["r2_prefire_bars"][0]
    if patch == "missing_ref":
        data["source_refs"]["round1_end"] = ""
    elif patch == "duplicated_ref":
        data["source_refs"]["round1_end"] = data["source_refs"]["round2_prefire"]
    elif patch == "wrong_stage":
        row["source_ref"] = "TEST_ONLY_R1"
    elif patch == "future_r2":
        data["context"]["r2_snapshot_is_prefire"] = False
    elif patch == "bad_tender":
        data["context"]["tender_count"] = 2
    elif patch == "unknown_forge":
        data["context"]["defender_forge_level"] = None
    elif patch == "wrong_attacker_forge":
        data["context"]["attacker_forge_level"] = 5
    elif patch == "wrong_battlefield":
        data["context"]["battlefield_id"] = "naval-small"
    elif patch == "wrong_initial_fleet":
        data["context"]["defender_units"]["ram_ship"] += 1
    elif patch == "wrong_ram_workshop":
        data["context"]["ram_ship_attack_upgrade"] += 1
    elif patch == "wrong_steam_attack_upgrade":
        data["context"]["steam_ram_attack_upgrade"] += 1
    elif patch == "wrong_steam_armor_upgrade":
        data["context"]["steam_ram_armor_upgrade"] += 1
    elif patch == "missing_steam_upgrade":
        data["context"]["steam_ram_attack_upgrade"] = None
    elif patch == "unknown_workshop":
        data["context"]["workshop_details_captured"] = False
    elif patch == "reinforcements":
        data["context"]["reinforcements_between_snapshots"] = "present"
    elif patch == "unasserted_equivalence":
        data["model_fleet_equivalence"] = intake.EQUIVALENCE_UNKNOWN
    elif patch == "wrong_source":
        data["record_kind"] = intake.TEMPLATE
    elif patch == "duplicate_slot":
        data["r2_prefire_bars"].append(deepcopy(row))
    elif patch == "negative_bar":
        row["visible_percent"] = -1
    elif patch == "boolean_bar":
        row["visible_percent"] = True
    elif patch == "wrong_slot_population":
        row["units_alive"] += 1
    elif patch == "invented_slot":
        row["model_damage_position"] = 99999
    elif patch == "foreign_wave":
        row["wave_id"] = "not-in-synthetic-fleet"
    elif patch == "hidden_address_with_unmapped_mode":
        data["mapping_mode"] = intake.UNMAPPED
    else:
        row["official_game_mechanism_verified"] = True
    report = intake.evaluate_capture(data)
    assert report["status"] in {"NOT_COMPARABLE", "INVALID"}
    assert report["conditional_model_comparison"] is None
    assert report["official_game_mechanism_verified"] is False
    assert report["original_game_observations_independently_verified"] == 0


def test_extra_metadata_cannot_claim_official_verification():
    data = _synthetic_test_record()
    data["officially_validated_by_gameforge"] = True
    result = intake.evaluate_capture(data)
    assert result["status"] == "INVALID"
    assert result["official_game_mechanism_verified"] is False


def test_all_observed_bars_outside_all_model_ranges_is_not_a_false_official_result():
    data = _synthetic_test_record()
    for row in data["r2_prefire_bars"]:
        row["visible_percent"] = 0
    out = intake.evaluate_capture(data)
    assert out["status"] == "CONDITIONAL_SCREEN_ONLY"
    assert out["conditional_model_comparison"]["all_inconsistent"] is True
    assert out["conditional_model_comparison"]["model_hypotheses_consistent_with_supplied_bars"] == []
    assert out["official_game_mechanism_verified"] is False


def test_supplied_counterfeit_model_comparison_is_rejected():
    from copy import deepcopy
    p = deepcopy(model.build_report())
    p["source"]["source_game_observations"] = 1
    with pytest.raises(ValueError, match="differs"):
        intake.evaluate_capture(_synthetic_test_record(), p)



def test_steam_ram_workshop_must_be_explicit_even_when_captured_flag_true():
    data = _synthetic_test_record()
    assert intake._expected_control_setup()["steam_ram_attack_upgrade"] == 0
    assert intake._expected_control_setup()["steam_ram_armor_upgrade"] == 0
    for field, value in (("steam_ram_attack_upgrade", 1),
                         ("steam_ram_armor_upgrade", 5),
                         ("steam_ram_attack_upgrade", None),
                         ("steam_ram_armor_upgrade", True)):
        corrupted = deepcopy(data)
        corrupted["context"][field] = value
        got = intake.evaluate_capture(corrupted)
        assert got["status"] == "NOT_COMPARABLE"
        assert any(field in msg for msg in got["input_requirements_missing_or_invalid"])
        assert got["conditional_model_comparison"] is None


def test_unmapped_impossible_population_fails_even_with_matching_hp_bars():
    data = _synthetic_test_record(mapping=intake.UNMAPPED)
    data["r2_prefire_bars"][0]["units_alive"] = 999
    out = intake.evaluate_capture(data)
    assert out["status"] == "NOT_COMPARABLE"
    assert out["conditional_model_comparison"] is None
    assert "injective" in " ".join(out["input_requirements_missing_or_invalid"])


def test_unmapped_actual_population_preserved_and_bars_conditionally_match():
    data = _synthetic_test_record(mapping=intake.UNMAPPED)
    model_data = model.build_report()
    for idx, ch in enumerate(model_data["channels"]):
        data["r2_prefire_bars"][idx]["units_alive"] = ch["simulated_slot_population"]
    res = intake.evaluate_capture(data)
    assert res["status"] == "CONDITIONAL_SCREEN_ONLY"
    baseline = model_data["case_order"][0]
    assert baseline in res["conditional_model_comparison"][
        "model_hypotheses_consistent_with_supplied_bars"]


def test_unmapped_assignment_is_one_to_one_even_if_each_row_has_a_match():
    channels = {
        "a": {"simulated_slot_population": 5},
        "b": {"simulated_slot_population": 1},
    }
    rows = [
        {"units_alive": 5, "visible_percent": 80},
        {"units_alive": 5, "visible_percent": 90},
    ]
    assert not intake._unmapped_wave_assignment(rows, ["a", "b"], channels)
    rows[1]["units_alive"] = 1
    assert intake._unmapped_wave_assignment(rows, ["a", "b"], channels)
    predicted = {"a": {"floor": 80}, "b": {"floor": 90}}
    assert intake._unmapped_wave_assignment(rows, ["a", "b"], channels, predicted, "floor")
    rows[1]["visible_percent"] = 80
    assert not intake._unmapped_wave_assignment(rows, ["a", "b"], channels, predicted, "floor")


def test_unmapped_percent_without_units_still_supports_partial_slot_subset():
    record = _synthetic_test_record(mapping=intake.UNMAPPED)
    original = record["r2_prefire_bars"][-1]
    record["r2_prefire_bars"] = [original]
    assert original["units_alive"] is None
    result = intake.evaluate_capture(record)
    assert result["status"] == "CONDITIONAL_SCREEN_ONLY"
