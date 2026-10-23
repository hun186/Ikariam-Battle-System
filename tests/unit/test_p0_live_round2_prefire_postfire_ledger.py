"""R1/R2 real-fire casualty and surviving-HP invariants, entirely synthetic."""
from copy import deepcopy

import pytest

from tools.research import p0_live_round2_prefire_postfire_ledger as audit


@pytest.mark.parametrize("domain", audit.DOMAINS)
@pytest.mark.parametrize("supporters", audit.SUPPORT_COUNTS)
def test_actual_round2_combat_preserves_prewave_alive_and_hp_audit(domain, supporters):
    case = audit.live_audit(domain, supporters)
    assert case["evidence_class"] == audit.PROVENANCE
    assert case["game_observation"] is False
    assert case["independent_holdout"] is False
    assert case["actual_round2_firing"] is True
    assert case["rounds_completed"] == 2
    assert case["round1_patient_wounds"] > 0
    assert case["round2_prefire_patient_reserve"] > 0
    assert case["patient_round2_firing_units"] > 0
    assert case["round2_patient_firing_event_count"] > 0
    for side in ("attacker", "defender"):
        states = case["witness"][side]
        assert states["round1_end"]["total"] <= states["initial"]["total"]
        assert states["round2_prefire"]["total"] == states["round1_end"]["total"]
        assert states["round2_end"]["total"] <= states["round2_prefire"]["total"]
        assert (states["round1_end"]["total"] - states["round2_end"]["total"]
                == sum(states["round_2_deaths_per_wave"].values()))
        assert all(v >= 0 for v in states["round_1_deaths_per_wave"].values())
        assert all(v >= 0 for v in states["round_2_deaths_per_wave"].values())
    if supporters:
        assert case["round2_prefire_patient_wounds"] == 0
        assert any(x["type"] == "healing" for x in case["round2_support_events"])
    else:
        assert (case["round2_prefire_patient_wounds"]
                == case["round1_patient_wounds"])
        assert not any(x["type"] == "healing" for x in case["round2_support_events"])


@pytest.mark.parametrize("domain", audit.DOMAINS)
def test_support_is_first_applied_after_round1_but_before_second_volley(domain):
    without = audit.live_audit(domain, 0)
    with_full = audit.live_audit(domain, 50)
    patient = with_full["patient"]
    for side in ("attacker", "defender"):
        # Adding only support units must not change R1 combat Wave identities,
        # living totals, Reserve, ammo or HP. Compare both sides and exclude
        # only the newly introduced support unit on the treated defender.
        support_id = "doctor" if domain == "land_doctor" else "tender"
        for phase in ("round1_prefire", "round1_end"):
            baseline = without["witness"][side][phase]
            treated = with_full["witness"][side][phase]
            def combat_waves(state):
                return {
                    (w["unit_id"], w["wave_id"]): w
                    for w in state["waves"] if w["unit_id"] != support_id
                }
            def combat_slots(state):
                return {
                    (s["unit_id"], s["wave_id"], s["slot_id"]): s
                    for s in state["slots"] if s["unit_id"] != support_id
                }
            assert combat_waves(baseline) == combat_waves(treated)
            assert combat_slots(baseline) == combat_slots(treated)
        assert (without["witness"][side]["round_1_deaths_per_wave"]
                == with_full["witness"][side]["round_1_deaths_per_wave"])
    for label in ("round1_end", "round1_prefire"):
        def wounded(case):
            state = case["witness"]["defender"][label]
            return sum(s["damage"] for s in state["slots"] if s["unit_id"] == patient) + sum(
                w["reserve_damage"] for w in state["waves"] if w["unit_id"] == patient
            )
        assert wounded(without) == wounded(with_full)
    assert without["round2_prefire_patient_wounds"] > 0
    assert with_full["round2_prefire_patient_wounds"] == 0
    assert with_full["patient_round2_firing_units"] > 0


def test_report_has_reproducible_source_tagged_ledger_without_game_holdouts():
    first = audit.report()
    second = audit.report()
    assert first == second
    assert first["summary"] == {
        "controlled_cases": 4, "actual_round2_engine_shot_cases": 4,
        "new_game_observations": 0, "independent_holdouts": 0,
        "with_full_support": 2,
    }
    csv = audit.csv_rows(first)
    assert len(csv) == 4
    assert all(x["actual_round2_firing"] and not x["new_game_observation"]
               and not x["independent_holdout"] for x in csv)


def test_mutated_second_round_alive_count_is_detected_even_with_unchanged_events(monkeypatch):
    original = audit.engine._snapshot

    def alter_snapshot(waves, registry, profile, *args, **kwargs):
        state = original(waves, registry, profile, *args, **kwargs)
        # Snapshot-only corruption: +1 to the actual living Wave count in
        # the pre-volley view while keeping casualties/events unchanged.
        if any(wave.unit.unit_id == "ram_ship" for wave in waves):
            state = deepcopy(state)
            target = next(w for w in state["waves"] if w["unit_id"] == "ram_ship")
            target["alive"] += 1
        return state

    monkeypatch.setattr(audit.engine, "_snapshot", alter_snapshot)
    with pytest.raises(AssertionError):
        audit.live_audit("naval_tender", 0)


def test_scenario_only_allows_explicit_controlled_domains_and_support_counts():
    for domain, amount in (("other", 0), ("land_doctor", 1), ("naval_tender", -1)):
        with pytest.raises(ValueError):
            audit.scenario(domain, amount)
