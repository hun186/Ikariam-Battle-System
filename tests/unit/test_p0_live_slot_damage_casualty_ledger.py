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



def test_missing_independent_unit_round_death_counts_is_not_accepted():
    before, after, events, totals, registry = _state_and_events()
    assert any(totals.values())
    # Counts cannot silently be treated as optional, including empty {}.
    with pytest.raises(AssertionError, match="required independent round unit"):
        audit.reconcile_round("defender", 1, before, after, events, registry)
    after["_round_casualties"] = {}
    with pytest.raises(AssertionError, match="per-slot deaths disagree"):
        audit.reconcile_round("defender", 1, before, after, events, registry)


def test_nonsequential_model_label_never_claims_sequential_hp_truth():
    before, after, events, totals, registry = _state_and_events()
    # Turn one event into a model-specific *label only*. Even when the
    # arithmetic residual remains zero, its provenance is not sequential.
    target = next(event for event in events if event["round"] == 1
                  and event["type"] == "damage"
                  and event["details"].get("target_side") == "defender")
    target["details"]["resolution"] = "bounded_experimental_focus_hypothesis"
    after["_round_casualties"] = totals
    rows = audit.reconcile_round("defender", 1, before, after, events, registry)
    row = next(row for row in rows if (
        row["unit_id"], row["wave_id"], row["slot_id"]
    ) == audit._key_from_hit(target))
    assert row["balance_status"] == audit.EXPERIMENTAL_EXEMPT
    assert "bounded_experimental_focus_hypothesis" in row["resolutions"]




def test_grouped_hit_assumptions_and_pooled_diagnostics_survive_json_evidence():
    import json

    evidence = audit.report()
    naval = [case for case in evidence["cases"] if case["domain"] == "naval_tender"]
    assert len(naval) == 2
    found_experiment_ids = set()
    for case in evidence["cases"]:
        for row in case["rows"]:
            source_events = row["grouped_damage_events"]
            assert len(source_events) == row["grouped_event_count"]
            expected_ids = sorted({
                assumption
                for event in source_events
                for assumption in event["details"].get("assumption_ids", [])
            })
            assert row["assumption_ids"] == expected_ids
            for event in source_events:
                detail = event["details"]
                assert detail["target_side"] == row["side"]
                assert detail["target_unit_id"] == row["unit_id"]
                assert detail["target_wave"] == row["wave_id"]
                assert detail["target_slot"] == row["slot_id"]
                assert detail["target_damage_position"] == row["damage_position"]
            if case["domain"] == "naval_tender":
                found_experiment_ids.update(expected_ids)
    # The two naval sub-hypotheses share a resolution label; the evidence
    # must retain their *different* specific IDs for downstream audit.
    assert "EXP-NAVAL-RAM-FOCUS-SHARE-001" in found_experiment_ids
    assert "EXP-NAVAL-DECK-OVERKILL-RETAIN-001" in found_experiment_ids


def test_csv_rows_carry_case_support_settings_and_full_event_provenance():
    import json

    evidence = audit.report()
    flattened = audit.csv_rows(evidence)
    assert len(flattened) == evidence["summary"]["slot_rounds"]
    assert len({row["case_id"] for row in flattened}) == 4
    assert {row["domain"] for row in flattened} == {"land_doctor", "naval_tender"}
    assert {row["supporters"] for row in flattened} == {0, 50}
    assert all(row["provenance"] == audit.PROVENANCE
               and row["real_game_observations"] == 0
               and row["independent_game_holdouts"] == 0
               for row in flattened)
    keys = [
        (row["case_id"], row["side"], row["round"],
         row["unit_id"], row["wave_id"], row["slot_id"])
        for row in flattened
    ]
    assert len(keys) == len(set(keys))
    # Real same-side, same-wave, same-slot keys recur across two experiments,
    # but full scenario-qualified keys must never collide.
    unqualified = [key[1:] for key in keys]
    assert len(set(unqualified)) < len(unqualified)
    case_map = {case["case_id"]: case for case in evidence["cases"]}
    for row in flattened:
        parent = case_map[row["case_id"]]
        assert row["domain"] == parent["domain"]
        assert row["supporters"] == parent["supporters"]
        matching = next(slot for slot in parent["rows"]
                        if (slot["side"], slot["round"], slot["unit_id"],
                            slot["wave_id"], slot["slot_id"]) ==
                        (row["side"], row["round"], row["unit_id"],
                         row["wave_id"], row["slot_id"]))
        assert json.loads(row["grouped_damage_events_json"]) == json.loads(
            json.dumps(matching["grouped_damage_events"])
        )
        assert json.loads(row["assumption_ids_json"]) == matching["assumption_ids"]
        assert json.loads(row["resolutions_json"]) == matching["resolutions"]


def test_export_rejects_duplicate_scenario_slot_rows():
    data = audit.report()
    data["cases"].append(deepcopy(data["cases"][0]))
    with pytest.raises(AssertionError, match="duplicate scenario-specific Slot"):
        audit.csv_rows(data)


def test_invalid_side_or_round_is_rejected():
    registry = UnitRegistry.load(include_barbarians=True)
    with pytest.raises(ValueError):
        audit.reconcile_round("unknown", 1, {"slots": []}, {"slots": []}, [], registry)
    with pytest.raises(ValueError):
        audit.reconcile_round("defender", 3, {"slots": []}, {"slots": []}, [], registry)
