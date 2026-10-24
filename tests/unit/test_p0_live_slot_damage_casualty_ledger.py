"""Per-slot live R1/R2 damage/death conservation for synthetic engine fights."""
from copy import deepcopy

import pytest

from ikariam_battle.units import UnitRegistry
from tools.research import p0_live_slot_damage_casualty_ledger as audit
from tools.research.p0_live_round2_prefire_postfire_ledger import live_audit


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
@pytest.mark.parametrize("supporters", (0, 50))
def test_real_two_round_slot_casualties_and_damage_events_conserve(
    domain, supporters,
):
    case = audit.slot_case(domain, supporters)
    rows = case["rows"]
    assert case["provenance"] == audit.PROVENANCE
    assert not case["real_game_observations"]
    assert not case["independent_game_holdouts"]
    assert {row["round"] for row in rows} == {1, 2}
    assert {row["side"] for row in rows} == {"attacker", "defender"}
    assert any(row["round"] == 2 and row["dead"] > 0 for row in rows)
    assert all(
        row["dead"] == row["snapshot_casualties"] == row["event_casualties"]
        for row in rows
    )
    assert all(row["balance_status"] in (
        audit.EXACT, audit.EXPERIMENTAL_EXEMPT
    ) for row in rows)
    assert all(row["hp_balance_residual"] == 0
               for row in rows if row["balance_status"] == audit.EXACT)
    assert all(row["independent_game_holdout"] is False for row in rows)


def _state_and_events():
    core = live_audit("land_doctor", 0)
    witness = core["witness"]["defender"]
    return (
        deepcopy(witness["round1_prefire"]),
        deepcopy(witness["round1_end"]),
        deepcopy(core["round_damage_events"]),
        core["round_casualties"]["1"]["defender"],
        UnitRegistry.load(include_barbarians=True),
    )


def test_mutated_recorded_slot_death_is_caught_not_trusted():
    before, after, events, totals, registry = _state_and_events()
    victim = next(s for s in after["slots"] if s["casualties"] > 0)
    victim["casualties"] += 1
    after["_round_casualties"] = totals
    with pytest.raises(AssertionError, match="slot casualties"):
        audit.reconcile_round("defender", 1, before, after, events, registry)


def test_mutated_grouped_hit_death_is_caught_by_live_slot_count():
    before, after, events, totals, registry = _state_and_events()
    target_key = next(
        (s["unit_id"], s["wave_id"], s["slot_id"])
        for s in after["slots"] if s["casualties"] > 0
    )
    hit = next(e for e in events if e["type"] == "damage"
               and e["round"] == 1 and e["details"]["target_side"] == "defender"
               and audit._key_from_hit(e) == target_key and e["details"]["casualties"])
    hit["details"]["casualties"] += 1
    after["_round_casualties"] = totals
    with pytest.raises(AssertionError, match="per-slot grouped-event deaths"):
        audit.reconcile_round("defender", 1, before, after, events, registry)


def test_mutated_sequential_incoming_hit_hp_is_caught():
    before, after, events, totals, registry = _state_and_events()
    hit = next(e for e in events if e["round"] == 1
               and e["type"] == "damage"
               and e["details"].get("target_side") == "defender"
               and e["details"].get("resolution") == audit.BASELINE_RESOLUTION)
    hit["details"]["damage"] += 1
    after["_round_casualties"] = totals
    with pytest.raises(AssertionError, match="sequential HP balance mismatch"):
        audit.reconcile_round("defender", 1, before, after, events, registry)


def test_event_targeting_a_missing_slot_is_rejected():
    before, after, events, totals, registry = _state_and_events()
    hit = next(e for e in events if e["round"] == 1
               and e["type"] == "damage"
               and e["details"].get("target_side") == "defender")
    hit["details"]["target_slot"] = "does-not-exist"
    after["_round_casualties"] = totals
    with pytest.raises(AssertionError, match="missing pre-volley slot"):
        audit.reconcile_round("defender", 1, before, after, events, registry)


def test_report_is_reproducible_and_never_claims_game_observations():
    first = audit.report()
    second = audit.report()
    assert first == second
    assert first["summary"]["synthetic_cases"] == 4
    assert first["summary"]["game_observations"] == 0
    assert first["summary"]["independent_holdouts"] == 0
    assert first["summary"]["slot_rounds"] > 0
    assert first["summary"]["slot_deaths"] > 0


def test_invalid_side_or_round_is_rejected():
    registry = UnitRegistry.load(include_barbarians=True)
    with pytest.raises(ValueError):
        audit.reconcile_round("unknown", 1, {"slots": []}, {"slots": []}, [], registry)
    with pytest.raises(ValueError):
        audit.reconcile_round("defender", 3, {"slots": []}, {"slots": []}, [], registry)
