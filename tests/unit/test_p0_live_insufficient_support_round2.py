"""R1/R2 live insufficient Doctor/Tender support evidence, never game observations."""
from copy import deepcopy
import json

import pytest

from ikariam_battle.units import UnitRegistry
from tools.research import p0_live_insufficient_support_round2 as audit


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
@pytest.mark.parametrize("supporters", (0, 1, 50))
def test_real_round2_fires_and_every_wave_keeps_deaths_and_hp(domain, supporters):
    case = audit.live_case(domain, supporters)
    assert case["provenance"] == audit.PROVENANCE
    assert case["game_observations"] == case["independent_holdouts"] == 0
    assert case["rounds_completed"] == 2
    assert case["round2_real_patient_firing"] is True
    assert case["round2_patient_grouped_damage_events"]
    assert case["round1_patient_wounds"] > 0
    for side in ("attacker", "defender"):
        track = case["transitions"][side]
        assert track["r1_deaths_per_wave"] is not None
        assert track["r2_deaths_per_wave"] is not None
        boundary = track["boundary"]
        assert all(w["alive_r1_end"] == w["alive_r2_prefire"]
                   for w in boundary["waves"])
        for w in boundary["waves"]:
            if boundary["outcome"] != audit.FULL or not w["eligible"]:
                assert w["wounds_r1_end"] == w["wounds_r2_prefire"]
            else:
                assert w["wounds_r2_prefire"] == 0


def test_naval_under_capacity_uses_explicit_unknown_not_fake_heal():
    domain = "naval_tender"
    expected_unknown_rule = "UNKNOWN-TENDER-HEALING-ALLOCATION"
    case = audit.live_case(domain, 1)
    boundary = case["transitions"]["defender"]["boundary"]
    assert boundary["outcome"] == audit.INSUFFICIENT
    assert boundary["capacity"] == 4000
    assert boundary["eligible_wounds_at_r1_end"] > boundary["capacity"]
    assert boundary["actual_applied_heal_hp"] == 0
    assert boundary["game_partial_allocation_verified"] is False
    events = boundary["support_events"]
    unknowns = [e for e in events if e["type"] == "healing_allocation_unresolved"]
    assert len(unknowns) == 1
    assert unknowns[0]["details"]["rule_id"] == expected_unknown_rule
    assert not any(e["type"] == "healing" for e in events)
    assert any(e["type"] == "damage" and e["round"] == 2
               for e in case["round2_patient_grouped_damage_events"])



def test_one_doctor_really_full_clears_land_round1_wounds():
    case = audit.live_case("land_doctor", 1)
    boundary = case["transitions"]["defender"]["boundary"]
    assert boundary["outcome"] == audit.FULL
    assert 0 < boundary["eligible_wounds_at_r1_end"] <= 4000
    assert boundary["actual_applied_heal_hp"] == boundary["eligible_wounds_at_r1_end"]
    assert case["round2_real_patient_firing"] is True
    assert case["round2_prefire_patient_wounds"] == 0
    assert any(e["type"] == "healing" for e in boundary["support_events"])
    assert not any(e["type"] == "healing_allocation_unresolved"
                   for e in boundary["support_events"])


def _boundary_case(domain="naval_tender"):
    case = audit.live_case(domain, 1)
    w = case["transitions"]["defender"]
    return (
        deepcopy(w["after_r1"]),
        deepcopy(w["before_r2"]),
        deepcopy(w["boundary"]["support_events"]),
        UnitRegistry.load(include_barbarians=True),
    )


def test_corrupted_wound_after_unknown_partial_support_is_rejected():
    before, after, events, registry = _boundary_case()
    eligible = next(w for w in after["waves"] if w["unit_id"] == "hoplite")
    eligible["reserve_damage"] += 1
    with pytest.raises(AssertionError, match="wound drift"):
        audit.reconcile_round_boundary(
            before, after, domain="naval_tender", side="defender",
            supporters=1, capacity_per_supporter=4000,
            events=events, registry=registry
        )


def test_false_success_healing_event_cannot_mask_unknown_boundary():
    before, after, events, registry = _boundary_case()
    forged = deepcopy(next(e for e in events if e["type"] == "healing_allocation_unresolved"))
    forged["type"] = "healing"
    events.append(forged)
    with pytest.raises(AssertionError, match="unknown partial heal was turned"):
        audit.reconcile_round_boundary(
            before, after, domain="naval_tender", side="defender",
            supporters=1, capacity_per_supporter=4000,
            events=events, registry=registry
        )


def test_unknown_support_event_must_match_independent_eligible_damage():
    before, after, events, registry = _boundary_case()
    unresolved = next(e for e in events if e["type"] == "healing_allocation_unresolved")
    unresolved["details"]["eligible_damage"] -= 1
    with pytest.raises(AssertionError, match="warning mismatches"):
        audit.reconcile_round_boundary(
            before, after, domain="naval_tender", side="defender",
            supporters=1, capacity_per_supporter=4000,
            events=events, registry=registry
        )


def test_support_cannot_restore_previous_dead_units_at_round_start():
    before, after, events, registry = _boundary_case()
    hoplite = next(w for w in after["waves"] if w["unit_id"] == "hoplite")
    hoplite["alive"] += 1
    with pytest.raises(AssertionError, match="illegally added/removed living"):
        audit.reconcile_round_boundary(
            before, after, domain="naval_tender", side="defender",
            supporters=1, capacity_per_supporter=4000,
            events=events, registry=registry
        )


def test_full_report_scenarios_have_provenance_and_mandatory_csv_case_identity():
    data = audit.report()
    assert data["summary"]["synthetic_cases"] == 6
    assert data["summary"]["with_R2_firing"] == 6
    assert data["summary"]["insufficient_support_cases"] == 1
    assert data["summary"]["full_clear_cases"] == 3
    assert data["summary"]["new_game_observations"] == 0
    assert data["summary"]["independent_game_holdouts"] == 0
    assert data == audit.report()
    rows = audit.csv_rows(data)
    assert len(rows) == 6
    assert len({r["case_id"] for r in rows}) == 6
    assert {r["supporters"] for r in rows} == {0, 1, 50}
    assert {r["domain"] for r in rows} == {"land_doctor", "naval_tender"}
    assert all(r["new_game_observations"] == 0
               and r["independent_game_holdouts"] == 0
               and r["game_partial_allocation_verified"] is False
               for r in rows)
    for row in rows:
        assert json.loads(row["r2_patient_grouped_shots_json"])
        assert json.loads(row["per_wave_round_boundary_json"])
        events = json.loads(row["support_event_evidence_json"])
        if row["supporters"] == 1 and row["domain"] == "naval_tender":
            assert any(e["type"] == "healing_allocation_unresolved"
                       for e in events)
        if row["supporters"] == 1 and row["domain"] == "land_doctor":
            assert any(e["type"] == "healing" for e in events)
