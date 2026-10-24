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
        # The treated trace includes an extra zero-loss Doctor/Tender Wave;
        # compare only the same real combat waves, not that new support key.
        without_losses = without["witness"][side]["round_1_deaths_per_wave"]
        treated_losses = {
            key: value
            for key, value in with_full["witness"][side]["round_1_deaths_per_wave"].items()
            if key.split("|", 1)[0] != support_id
        }
        assert without_losses == treated_losses
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




@pytest.mark.parametrize("domain,unit_id", (
    ("land_doctor", "gyrocopter"),  # Doctor-ineligible Machine
    ("land_doctor", "swordsman"),   # Doctor-eligible Human
    ("naval_tender", "steam_ram"),  # Tender-eligible second ship type
))
def test_round2_cross_wave_wounds_detect_valid_but_corrupted_other_unit(
    domain, unit_id,
):
    from ikariam_battle.units import UnitRegistry

    case = audit.live_audit(domain, 50)
    before = case["witness"]["defender"]["round1_end"]
    after = deepcopy(case["witness"]["defender"]["round2_prefire"])
    registry = UnitRegistry.load(include_barbarians=True)

    target = next(slot for slot in after["slots"]
                  if slot["unit_id"] == unit_id and slot["units"] > 0)
    hp = registry.get(unit_id).hit_points
    old_damage = target["damage"]
    # A locally valid mutation: change wound by one HP and *correctly*
    # recompute the exported percentage so the independent snapshot validator
    # does not catch it. Only full per-Wave cross-boundary accounting can.
    target["damage"] = old_damage + 1 if old_damage + 1 < hp * target["units"] else old_damage - 1
    assert target["damage"] >= 0 and target["damage"] != old_damage
    target["hit_points_percent"] = round(
        100 * (target["units"] * hp - target["damage"])
        / (target["units"] * hp), 2
    )
    audit._validate_snapshot(after, registry, "locally-valid-corruption")
    with pytest.raises(AssertionError, match="wave wound continuity"):
        audit._round2_wound_continuity(before, after, registry, domain, "defender", 50)


@pytest.mark.parametrize("domain", audit.DOMAINS)
def test_reserve_wound_drift_detected_when_percent_is_updated(domain):
    from ikariam_battle.units import UnitRegistry

    case = audit.live_audit(domain, 0)
    before = case["witness"]["defender"]["round1_end"]
    after = deepcopy(case["witness"]["defender"]["round2_prefire"])
    registry = UnitRegistry.load(include_barbarians=True)
    reserve = next(wave for wave in after["waves"]
                   if wave["unit_id"] == case["patient"] and wave["reserve"] > 0)
    hp = registry.get(case["patient"]).hit_points
    original = reserve["reserve_damage"]
    reserve["reserve_damage"] = (original + 1
                                if original + 1 < reserve["reserve"] * hp
                                else original - 1)
    assert reserve["reserve_damage"] >= 0 and reserve["reserve_damage"] != original
    reserve["reserve_hit_points_percent"] = round(
        100 * (reserve["reserve"] * hp - reserve["reserve_damage"])
        / (reserve["reserve"] * hp), 2
    )
    audit._validate_snapshot(after, registry, "locally-valid-reserve-corruption")
    with pytest.raises(AssertionError, match="wave wound continuity"):
        audit._round2_wound_continuity(before, after, registry, domain, "defender", 0)


@pytest.mark.parametrize("domain", audit.DOMAINS)
def test_stale_slot_hp_percent_fails_even_when_within_0_to_100(domain):
    from ikariam_battle.units import UnitRegistry

    case = audit.live_audit(domain, 0)
    corrupted = deepcopy(case["witness"]["defender"]["round2_prefire"])
    slot = next(s for s in corrupted["slots"] if s["unit_id"] == case["patient"])
    slot["hit_points_percent"] = (
        91.23 if slot["hit_points_percent"] != 91.23 else 83.21
    )
    with pytest.raises(AssertionError, match="stale slot HP percentage"):
        audit._validate_snapshot(corrupted, UnitRegistry.load(include_barbarians=True),
                                 "corrupted-slot-percentage")


@pytest.mark.parametrize("domain", audit.DOMAINS)
def test_stale_reserve_percent_and_empty_reserve_percent_fail(domain):
    from ikariam_battle.units import UnitRegistry

    case = audit.live_audit(domain, 0)
    state = case["witness"]["defender"]["round2_prefire"]
    registry = UnitRegistry.load(include_barbarians=True)
    corrupted = deepcopy(state)
    patient = next(w for w in corrupted["waves"] if w["unit_id"] == case["patient"])
    assert patient["reserve"] > 0
    patient["reserve_hit_points_percent"] = (
        91.23 if patient["reserve_hit_points_percent"] != 91.23 else 83.21
    )
    with pytest.raises(AssertionError, match="stale Reserve HP percentage"):
        audit._validate_snapshot(corrupted, registry, "bad-reserve-percentage")

    corrupted = deepcopy(state)
    zero_reserve = next(w for w in corrupted["waves"] if w["reserve"] == 0)
    assert zero_reserve["reserve_hit_points_percent"] is None
    zero_reserve["reserve_hit_points_percent"] = 100
    with pytest.raises(AssertionError, match="stale Reserve HP percentage"):
        audit._validate_snapshot(corrupted, registry, "phantom-empty-reserve-percentage")


def test_scenario_only_allows_explicit_controlled_domains_and_support_counts():
    for domain, amount in (("other", 0), ("land_doctor", 1), ("naval_tender", -1)):
        with pytest.raises(ValueError):
            audit.scenario(domain, amount)
