"""Prospective Gameforge screenshot design from SYNTHETIC hypothesis HP bars."""
from copy import deepcopy
import json

import pytest

from tools.research import p0_naval_hp_bar_capture_discrimination as audit
from tools.research import p0_tender_healing_rr_order_uncertainty as prior


def _case(rounding_data):
    return {
        key: {"rounding_predictions": {
            "floor": a, "nearest_half_up": b, "ceil": c
        }} for key, (a, b, c) in rounding_data.items()
    }


def test_known_rounding_vs_unknown_does_not_turn_overlap_into_mechanic():
    cases = {
        "a": _case({"slot": (50, 51, 51)}),
        "b": _case({"slot": (51, 51, 52)}),
        "c": _case({"slot": (60, 60, 60)}),
    }
    ids = list(cases)
    floor = audit.distinguished_pairs(ids, cases, ["slot"], "floor")
    nearest = audit.distinguished_pairs(ids, cases, ["slot"], "nearest_half_up")
    unknown = audit.distinguished_pairs(ids, cases, ["slot"], audit.UNKNOWN_ROUNDING)
    assert ("a", "b") in floor
    assert ("a", "b") not in nearest
    assert ("a", "b") not in unknown
    assert ("a", "c") in unknown and ("b", "c") in unknown


def test_unknown_mode_one_shared_global_rounding_not_independent_per_slot():
    # Each hypothesis must use a SINGLE consistent display mode on all
    # observed Slots, rather than mixing e.g. A.floor with A.ceil per Slot.
    cases = {
        "a": _case({"first": (40, 41, 42), "second": (70, 71, 72)}),
        "b": _case({"first": (42, 43, 44), "second": (72, 73, 74)}),
    }
    # A ceil == B floor at BOTH slots: same visible two-bar vector (42,72).
    assert not audit.distinguished_pairs(
        list(cases), cases, ["first", "second"], audit.UNKNOWN_ROUNDING
    )
    # Change B's second floor to 73 so the full two-bar sets separate
    # despite overlap on 'first' alone.
    cases["b"]["second"]["rounding_predictions"]["floor"] = 73
    assert audit.distinguished_pairs(
        list(cases), cases, ["first", "second"], audit.UNKNOWN_ROUNDING
    ) == {("a", "b")}
    assert not audit.distinguished_pairs(
        list(cases), cases, ["first"], audit.UNKNOWN_ROUNDING
    )


def test_duplicated_slot_mapping_unmapped_multiset_erases_distinction():
    cases = {
        "a": _case({"s1": (70, 70, 70), "s2": (90, 90, 90)}),
        "b": _case({"s1": (90, 90, 90), "s2": (70, 70, 70)}),
    }
    for case in cases.values():
        case["s1"].update(unit_id="ram_ship", wave_id="w")
        case["s2"].update(unit_id="ram_ship", wave_id="w")
    keys = ["s1", "s2"]
    assert audit.distinguished_pairs(
        list(cases), cases, keys, "floor"
    ) == {("a", "b")}
    assert audit.distinguished_pairs(
        list(cases), cases, keys, "floor", unmapped=True
    ) == set()


def test_capture_greedy_handles_two_slot_joint_rounding_separation():
    cases = {
        "a": _case({"1": (40, 41, 42), "2": (70, 71, 72)}),
        "b": _case({"1": (42, 43, 44), "2": (73, 74, 75)}),
    }
    ids = list(cases)
    assert not audit.distinguished_pairs(
        ids, cases, ["1"], audit.UNKNOWN_ROUNDING
    )
    assert not audit.distinguished_pairs(
        ids, cases, ["2"], audit.UNKNOWN_ROUNDING
    )
    plan = audit.capture_plan(ids, cases, ["1", "2"], audit.UNKNOWN_ROUNDING)
    assert plan["recommended_order"] == ["1", "2"]
    assert plan["steps"][0]["newly_distinguishable_pairs"] == 0
    assert plan["steps"][1]["newly_distinguishable_pairs"] == 1
    assert plan["full_slot_distinguishable_pairs"] == 1
    assert plan["heuristic"] == "sequential_greedy_not_minimal_set_cover"


def test_reject_unknown_channels_and_mixed_claims():
    cases = {"a": _case({"s": (20, 21, 21)}),
             "b": _case({"s": (30, 31, 31)})}
    with pytest.raises(ValueError, match="duplicate"):
        audit.distinguished_pairs(list(cases), cases, ["s", "s"], "floor")
    with pytest.raises(ValueError, match="unknown model"):
        audit.distinguished_pairs(list(cases), cases, ["wrong"], "floor")
    with pytest.raises(ValueError, match="unknown game display"):
        audit.distinguished_pairs(list(cases), cases, ["s"], "round")
    with pytest.raises(ValueError, match="invalid"):
        audit._channel_id("ram_ship", "wave-1", True)


def test_full_report_four_rounding_modes_means_only_conditional():
    actual = audit.build_report()
    assert actual["summary"]["source_model_comparisons"] == 10
    assert actual["summary"]["physical_simulated_slot_channels"] > 0
    assert actual["summary"]["candidate_rounding_interpretations"] == 4
    assert actual["source"]["game_rounding_verified"] is False
    assert actual["source"]["game_to_model_slot_mapping_verified"] is False
    assert actual["source"]["true_healing_recipient_or_rr_order_verified"] is False
    assert actual["summary"]["new_game_observations"] == 0
    assert actual["summary"]["independent_holdouts"] == 0
    assert actual["summary"]["game_mechanic_verified"] is False
    assert len(actual["case_order"]) == 10
    assert len(set(actual["case_order"])) == 10
    assert set(audit.ROUNDING_MODES) | {audit.UNKNOWN_ROUNDING} == {
        x["assumed_game_bar_rounding"] for x in actual["rounding_analyses"]
    }
    ids = set(actual["predicted_integer_percent_bars"])
    assert ids == set(actual["case_order"])
    channel_ids = {x["channel_id"] for x in actual["channels"]}
    assert all(x["game_slot_address_verified"] is False
               and x["model_hp_denominator"] > 0 and x["simulated_slot_population"] > 0
               for x in actual["channels"])
    for case in actual["rounding_analyses"]:
        selected = case["capture_plan"]["recommended_order"]
        assert len(set(selected)) == len(selected)
        assert set(selected).issubset(channel_ids)
        assert case["without_game_slot_mapping_distinguishable_pairs"] <= (
            case["addressed_all_slot_distinguishable_pairs"]
        )
        assert case["capture_plan"]["full_slot_distinguishable_pairs"] == (
            case["addressed_all_slot_distinguishable_pairs"]
        )
        assert (len(case["ambiguous_pairs_even_with_all_slot_bars"]) +
                case["addressed_all_slot_distinguishable_pairs"] == 45)
    assert actual == audit.build_report()


def test_csv_capture_plan_order_is_deterministic_and_source_labeled():
    data = audit.build_report()
    records = audit.csv_rows(data)
    assert records
    assert len({(r["rounding_assumption"], r["channel_id"])
                for r in records}) == len(records)
    assert all(r["provenance"] == audit.PROVENANCE
               and r["new_game_observations"] == 0
               and r["independent_holdouts"] == 0
               and r["game_rounding_verified"] is False
               and r["game_slot_mapping_verified"] is False
               for r in records)
    by_mode = {}
    for record in records:
        by_mode.setdefault(record["rounding_assumption"], []).append(
            record["capture_order"]
        )
    assert all(orders == list(range(1, len(orders) + 1))
               for orders in by_mode.values())
    assert json.dumps(data, ensure_ascii=False)
    assert data["source"]["case_id"] == prior.build_report()["source"]["case_id"]


@pytest.mark.parametrize("mutation", ["forge_verified", "duplicate_case", "duplicate_slot",
                                       "healing_violates_hp", "population_changes",
                                       "game_observation_forged", "removed_case"])
def test_rejects_fabricated_source_evidence(mutation):
    report = prior.build_report()
    if mutation == "forge_verified":
        report["cases"][0]["game_mechanic_verified"] = True
    elif mutation == "duplicate_case":
        report["cases"][1]["case_id"] = report["cases"][0]["case_id"]
    elif mutation == "duplicate_slot":
        report["cases"][1]["wave_hp"][0]["slots"].append(
            deepcopy(report["cases"][1]["wave_hp"][0]["slots"][0])
        )
    elif mutation == "healing_violates_hp":
        report["cases"][1]["wave_hp"][0]["hypothetical_healed_hp"] += 1
    elif mutation == "population_changes":
        report["cases"][1]["wave_hp"][0]["slots"][0]["units"] += 1
    elif mutation == "game_observation_forged":
        report["summary"]["novel_game_observations"] = 1
    else:
        report["cases"].pop()
    with pytest.raises(AssertionError):
        audit.extract_predictions(report)
