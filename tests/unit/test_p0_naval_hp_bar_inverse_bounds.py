"""Exact integer bar-inversion tests; no new official Gameforge observations."""
from copy import deepcopy

import pytest

from tools.research import p0_naval_hp_bar_inverse_bounds as audit
from tools.research import p0_naval_slot_hp_falsification as historical


@pytest.mark.parametrize("bar,cap,mode,expected", [
    (53, 5600, "floor", (2577, 2632)),
    (65, 5600, "floor", (1905, 1960)),
    (53, 5600, "nearest_half_up", (2605, 2660)),
    (53, 5600, "ceil", (2632, 2687)),
    (100, 5600, "floor", (0, 0)),
    (0, 5600, "ceil", (5600, 5600)),
])
def test_exact_integer_wound_windows(bar, cap, mode, expected):
    got = audit.percent_window(bar, cap, mode)
    assert got == expected
    for wound in (got[0], got[1]):
        assert audit.display_percent(cap - wound, cap, mode) == bar
    if got[0] > 0:
        assert audit.display_percent(cap - (got[0] - 1), cap, mode) != bar
    if got[1] < cap:
        assert audit.display_percent(cap - (got[1] + 1), cap, mode) != bar


@pytest.mark.parametrize("bar,cap,mode", [
    (-1, 5600, "floor"),
    (101, 5600, "floor"),
    (53, 0, "floor"),
    (53, 5600, "unknown"),
    (True, 5600, "floor"),
    (53, True, "floor"),
])
def test_bad_display_input_fails_closed(bar, cap, mode):
    with pytest.raises(ValueError):
        audit.percent_window(bar, cap, mode)


def test_source_backed_reverse_att14_floor_overkill_is_only_conditional():
    report = audit.build_report()
    reverse = next(case for case in report["cases"]
                   if case["case_id"] == "player_fast_att14_vs_barbarian_carrier")
    assert reverse["observed_source"] == "USER_CHAT"
    assert reverse["observed_round"] == 1
    assert reverse["observed_slot_deaths"] == [1, 1]
    assert reverse["observed_bars_unmapped"] == [53, 65]
    assert reverse["independent_game_holdout"] is False
    assert reverse["ui_hp_bar_rule_verified"] is False
    slots = reverse["model_slots"]
    assert [x["reported_engine_floor_bar"] for x in slots] == [57, 69]
    assert [x["discarded_overkill_model"] for x in slots] == [233, 233]
    assert [x["survivor_hp_capacity"] for x in slots] == [5600, 5600]
    assert [x["survivor_wounds_model"] for x in slots] == [2359, 1685]
    for slot in slots:
        assert slot["nominal_incoming_damage_model"] == (
            slot["survivor_wounds_model"] + 2800
            + slot["discarded_overkill_model"]
        )
        assert slot["assumption_ids_model"]
        assert slot["grouped_model_events"]

    opts = reverse["conditional_mappings"]
    viable = [x for x in opts if x["all_slots_overkill_budget_feasible"]]
    assert len(viable) == 1
    assert viable[0]["ui_rounding_hypothesis"] == "floor"
    assert [x["assigned_original_percent_unverified_mapping"] for x in viable[0]["slots"]] == [53, 65]
    assert [x["feasible_recovered_overkill_min"] for x in viable[0]["slots"]] == [218, 220]
    assert [x["feasible_recovered_overkill_max"] for x in viable[0]["slots"]] == [233, 233]
    assert [x["full_recovery_display_bar"] for x in viable[0]["slots"]] == [53, 65]
    # No one has supplied an original numbered bar→physical-slot mapping.
    assert all(x["original_bar_mapping_status"] == "unmapped_permutation_hypothesis"
               for x in opts)


def test_def14_no_losses_control_requires_no_discarded_overkill_for_floor():
    report = audit.build_report()
    control = next(case for case in report["cases"]
                   if case["case_id"] == "barbarian_fast_vs_player_carrier_def14")
    assert control["observed_bars_unmapped"] == [65, 70]
    assert control["observed_round"] is None  # original round not established
    assert control["observed_slot_deaths"] is None
    assert [x["discarded_overkill_model"] for x in control["model_slots"]] == [0, 0]
    good = [x for x in control["conditional_mappings"]
            if x["all_slots_overkill_budget_feasible"]]
    assert len(good) == 1 and good[0]["ui_rounding_hypothesis"] == "floor"
    assert [x["feasible_recovered_overkill_min"] for x in good[0]["slots"]] == [0, 0]
    assert [x["feasible_recovered_overkill_max"] for x in good[0]["slots"]] == [0, 0]


def test_all_other_historical_cases_remain_not_assessable():
    report = audit.build_report()
    assert report["summary"] == {
        "historical_cases": 5,
        "cases_with_reported_original_bars": 2,
        "new_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanic_verified": False,
        "feasible_mapping_counts_by_rounding": {
            "floor": 2, "nearest_half_up": 0, "ceil": 0,
        },
    }
    assert sum(x["status"] == audit.STATUS_UNKNOWN for x in report["cases"]) == 3
    assert all(x["conditional_mappings"] == [] for x in report["cases"]
               if x["observed_bars_unmapped"] is None)
    assert all(x["official_game_mechanic_verified"] is False
               and x["independent_game_holdout"] is False for x in report["cases"])
    flat = audit.csv_rows(report)
    assert len(flat) == 24
    assert {x["case_id"] for x in flat} == {
        "player_fast_att14_vs_barbarian_carrier",
        "barbarian_fast_vs_player_carrier_def14",
    }
    assert len(set((x["case_id"], x["rounding_hypothesis"],
                    x["model_damage_position"], x["assigned_original_percent_unverified_mapping"])
                   for x in flat)) == len(flat)
    assert all(not x["game_mechanic_verified"] and not x["independent_holdout"]
               for x in flat)
    assert report == audit.build_report()


def test_mutated_event_overkill_budget_refuses_false_arithmetic():
    raw = historical.build_report()
    reverse = deepcopy(next(c for c in raw["cases"] if
                            c["case_id"] == "player_fast_att14_vs_barbarian_carrier"))
    reverse["model"]["target_damage_events"][0]["details"]["overkill_discarded"] += 1
    with pytest.raises(ValueError, match="budget does not reconcile"):
        audit.analyze_case(reverse)


def test_model_missing_target_event_and_forged_holdout_fail_closed():
    raw = historical.build_report()
    reverse = deepcopy(next(c for c in raw["cases"] if
                            c["case_id"] == "player_fast_att14_vs_barbarian_carrier"))
    reverse["model"]["target_damage_events"].pop()
    with pytest.raises(ValueError, match="fail to cover"):
        audit.analyze_case(reverse)
    reverse = deepcopy(next(c for c in raw["cases"] if
                            c["case_id"] == "player_fast_att14_vs_barbarian_carrier"))
    reverse["independent_holdout"] = True
    with pytest.raises(ValueError, match="may not claim holdout"):
        audit.analyze_case(reverse)


def test_unknown_ui_semantics_cannot_be_silently_marked_verified():
    raw = historical.build_report()
    reverse = deepcopy(next(c for c in raw["cases"] if
                            c["case_id"] == "player_fast_att14_vs_barbarian_carrier"))
    reverse["diagnostics"]["hp_bar_semantics"] = "officially_verified_floor"
    with pytest.raises(ValueError, match="no longer marked unknown"):
        audit.analyze_case(reverse)
