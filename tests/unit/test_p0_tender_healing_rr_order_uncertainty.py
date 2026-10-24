"""Counterfactual healing order vs localization; NEVER official Gameforge evidence."""
from copy import deepcopy
import json

import pytest

from ikariam_battle.units import UnitRegistry
from tools.research import p0_tender_healing_rr_order_uncertainty as audit
from tools.research import p0_tender_partial_heal_allocation_envelope as prior


def _known_rr_state():
    """Hand-calculated 300 wounds across 3+3 Slots and 4 Reserve units."""
    registry = UnitRegistry.load(include_barbarians=True)
    hp = registry.get("ram_ship").hit_points
    state = {
        "waves": [{
            "unit_id": "ram_ship", "wave_id": "wave-1",
            "alive": 10, "reserve": 4, "reserve_damage": 120,
        }],
        "slots": [
            {
                "unit_id": "ram_ship", "wave_id": "wave-1",
                "slot_id": f"flank-{position}", "damage_position": position,
                "units": 3, "damage": 90,
                "hit_points_percent": round(100 * (3 * hp - 90) / (3 * hp), 2),
            }
            for position in (1, 2)
        ],
    }
    row = {
        "unit_id": "ram_ship", "wave_id": "wave-1",
        "eligible": True, "alive": 10,
        "wounds_r1_end": 300, "model_wounds_r2_prefire": 300,
    }
    return state, row, registry


def test_hand_computed_location_difference_no_added_casualties():
    state, row, registry = _known_rr_state()
    base = prior._rr_counterfactual(state, row, 0, registry)
    assert [s["remaining_wounds"] for s in base["slots"]] == [90, 90]
    assert base["reserve_wounds"] == 120
    before = prior._rr_counterfactual(state, row, 100, registry)
    slot_first = audit.rr_then_local_heal(
        state, row, 100, registry, reserve_first=False
    )
    reserve_first = audit.rr_then_local_heal(
        state, row, 100, registry, reserve_first=True
    )
    assert [s["remaining_wounds"] for s in before["slots"]] == [60, 60]
    assert before["reserve_wounds"] == 80
    assert [s["remaining_wounds"] for s in slot_first["slots"]] == [0, 80]
    assert slot_first["reserve_wounds"] == 120
    assert [s["remaining_wounds"] for s in reserve_first["slots"]] == [90, 90]
    assert reserve_first["reserve_wounds"] == 20
    assert len({
        (tuple(x["remaining_wounds"] for x in scenario["slots"]),
         scenario["reserve_wounds"])
        for scenario in (before, slot_first, reserve_first)
    }) == 3
    for case in (base, before, slot_first, reserve_first):
        assert case["alive"] == 10 and case["reserve"] == 4
        assert (sum(s["remaining_wounds"] for s in case["slots"])
                + case["reserve_wounds"]
                + case["hypothetical_healed_hp"] == 300)
        assert all(0 <= s["percent_current_model_format"] <= 100
                   for s in case["slots"])


@pytest.mark.parametrize("grant", [-1, True, 301, 300.5])
def test_rejects_noninteger_or_above_surviving_wounds(grant):
    state, row, registry = _known_rr_state()
    with pytest.raises(ValueError):
        audit.rr_then_local_heal(
            state, row, grant, registry, reserve_first=False
        )


def test_ineligible_wave_cannot_be_healed():
    state, row, registry = _known_rr_state()
    row["eligible"] = False
    with pytest.raises(ValueError, match="eligible"):
        audit.rr_then_local_heal(state, row, 1, registry, reserve_first=True)


def test_rejects_duplicate_physical_address_and_corrupt_baseline():
    state, row, registry = _known_rr_state()
    state["slots"].append(deepcopy(state["slots"][0]))
    with pytest.raises(AssertionError):
        audit.rr_then_local_heal(state, row, 40, registry, reserve_first=False)
    state, row, registry = _known_rr_state()
    state["slots"][0]["damage"] += 1
    with pytest.raises(AssertionError, match="original live R2 prefire HP"):
        audit.rr_then_local_heal(state, row, 40, registry, reserve_first=True)


def test_full_real_synthetic_reference_and_every_counterfactual():
    report = audit.build_report()
    assert report["classification"] == audit.PROVENANCE
    assert report["source"]["source_run_rounds"] == 2
    assert report["source"]["model_reference_capacity_hp"] == 4000
    assert report["source"]["original_model_partial_healing_applied_hp"] == 0
    assert report["summary"] == {
        "comparisons": 10, "hypothetical_comparisons": 9,
        "novel_game_observations": 0, "independent_holdouts": 0,
        "game_mechanic_verified": False,
    }
    assert len({case["case_id"] for case in report["cases"]}) == 10
    assert {x["policy"] for x in report["cases"][1:]} == set(audit.PRIORITIES)
    assert {x["ordering_hypothesis"] for x in report["cases"][1:]} == set(audit.ORDERS)
    base = report["cases"][0]
    assert base["total_hypothetical_heal_hp"] == 0
    for case in report["cases"]:
        assert case["game_mechanic_verified"] is False
        assert case["actual_changed_R2_combat_executed"] is False
        assert case["total_hypothetical_heal_hp"] == (
            0 if case is base else 4000
        )
        waves = case["wave_hp"]
        assert len(set((x["unit_id"], x["wave_id"]) for x in waves)) == len(waves)
        for row in waves:
            assert (row["hypothetical_remaining_wounds"] +
                    row["hypothetical_healed_hp"] ==
                    row["original_wounds_r1"])
            assert (row["hypothetical_remaining_wounds"] ==
                    sum(x["remaining_wounds"] for x in row["slots"]) +
                    row["reserve_wounds"])
            assert row["reserve"] + sum(x["units"] for x in row["slots"]) == row["alive"]
            if case is base:
                assert row["reserve_wounds"] == row["original_model_reserve_wounds"]
                assert all(s["remaining_wounds"] == s["original_model_wounds"]
                           for s in row["slots"])
            if case["ordering_hypothesis"].startswith("hypothetical_experimental_rr_then"):
                assert sum(x["healing_hp"] for x in row["localized_healing_evidence"]) == row["hypothetical_healed_hp"]
    assert report == audit.build_report()


def test_csv_is_case_qualified_and_preserves_provenance():
    report = audit.build_report()
    rows = audit.csv_rows(report)
    assert len(rows) >= 10
    assert len({(x["case_id"], x["unit_id"], x["wave_id"]) for x in rows}) == len(rows)
    assert {x["ordering_hypothesis"] for x in rows} == set(audit.ORDERS) | {
        "original_engine_fallback"
    }
    assert all(not x["game_mechanic_verified"] and
               not x["alternate_R2_combat_executed"] and
               x["new_game_observations"] == x["independent_holdouts"] == 0
               and isinstance(json.loads(x["slots_json"]), list)
               and isinstance(json.loads(x["localized_allocation_json"]), list)
               for x in rows)


def test_mutated_original_prefire_slot_rejected_not_treated_as_actual(monkeypatch):
    case = prior.source()

    def fake_source():
        modified = deepcopy(case)
        slot = next(s for s in modified["transitions"]["defender"]["before_r2"]["slots"]
                    if s["unit_id"] == "ram_ship" and s["units"])
        slot["damage"] += 1
        return modified

    monkeypatch.setattr(prior, "source", fake_source)
    with pytest.raises(AssertionError, match="not conserved"):
        audit.build_report()


def test_duplicate_csv_projection_is_rejected():
    report = audit.build_report()
    report["cases"][1]["wave_hp"].append(
        deepcopy(report["cases"][1]["wave_hp"][0])
    )
    with pytest.raises(AssertionError, match="case-qualified Wave"):
        audit.csv_rows(report)
