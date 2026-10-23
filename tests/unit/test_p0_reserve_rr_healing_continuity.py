"""Synthetic Round2 same-Wave Reserve refill / Doctor-Tender healing-RR tests."""
import pytest

from tools.research import p0_reserve_rr_healing_continuity as probe


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
@pytest.mark.parametrize("support_count,injury,outcome,expected_wounds", [
    (0, 5000, probe.NO_HEAL, 5000),
    (1, 5000, probe.UNKNOWN, 5000),
    (1, 5001, probe.UNKNOWN, 5001),
    (2, 5000, probe.FULL, 0),
    (1, 4000, probe.FULL, 0),
])
def test_real_round2_repack_heal_and_rr_conserve_prior_deaths_and_hp(
    domain, support_count, injury, outcome, expected_wounds,
):
    case = probe.audit(domain, support_count, injury)
    assert case["outcome"] == outcome
    assert case["initial_wounds"] == injury
    assert case["after"]["total_wounds"] == expected_wounds
    assert case["before"]["historical_dead"] == case["after"]["historical_dead"] == 1
    assert case["before"]["alive"] == case["after"]["alive"]
    assert case["before"]["reserve"] > case["after"]["reserve"] > 0
    assert case["after"]["reserve"] + sum(
        s["units"] for s in case["after"]["slots"]
    ) == case["before"]["alive"]
    assert len(case["round2_snapshot"]["slots"]) == 2
    assert case["evidence_class"] == probe.PROVENANCE
    assert case["original_game_observation"] is False
    assert case["independent_game_holdout"] is False
    assert case["fired_round2_shots"] is False
    events = case["events"]
    repacks = [e for e in events if e["type"] == "slot_repacked"]
    assert len(repacks) == 1
    assert repacks[0]["details"]["damage_position"] == 2
    assert repacks[0]["details"]["previous_units"] < repacks[0]["details"]["units"]
    heal_events = [e for e in events if e["type"] == "healing"]
    rr = [e for e in events if e["type"] == "redistribution"
          and e["details"].get("rule") == "RR"]
    if outcome == probe.FULL:
        assert len(heal_events) == 1
        assert not rr
        assert case["after"]["reserve_damage"] == 0
        assert [s["damage"] for s in case["after"]["slots"]] == [0, 0]
        assert events.index(repacks[0]) < events.index(heal_events[0])
    else:
        assert not heal_events
        assert len(rr) == 1
        assert events.index(repacks[0]) < events.index(rr[0])
        if outcome == probe.UNKNOWN:
            warning = next(e for e in events
                           if e["type"] == "healing_allocation_unresolved")
            assert events.index(repacks[0]) < events.index(warning) < events.index(rr[0])


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
def test_reserve_state_matches_without_support_or_with_unknown_partial(domain):
    absent = probe.audit(domain, 0, 5000)
    partial = probe.audit(domain, 1, 5000)
    # Unvalidated partial allocation must not silently create a different
    # actual HP answer than the current explicit no-partial simulation model.
    assert absent["after"] == partial["after"]
    assert absent["round2_snapshot"]["slots"] == partial["round2_snapshot"]["slots"]
    assert absent["round2_snapshot"]["wave"] == partial["round2_snapshot"]["wave"]
    assert not any(e["type"] == "healing" for e in partial["events"])
    assert any(e["type"] == "healing_allocation_unresolved"
               for e in partial["events"])


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
def test_odd_damage_retains_the_extra_hp_in_reserve(domain):
    even = probe.audit(domain, 1, 5000)
    odd = probe.audit(domain, 1, 5001)
    assert [s["damage"] for s in even["after"]["slots"]] == [1250, 1250]
    assert [s["damage"] for s in odd["after"]["slots"]] == [1250, 1250]
    assert odd["after"]["reserve_damage"] == even["after"]["reserve_damage"] + 1
    assert even["after"]["reserve_damage"] == 2500
    assert odd["after"]["total_wounds"] == even["after"]["total_wounds"] + 1


def test_cross_domain_report_is_deterministic_and_never_claims_holdouts():
    a, b = probe.report(), probe.report()
    assert a == b
    assert a["summary"] == {
        "controlled_cases": 10,
        "game_observations": 0,
        "independent_holdouts": 0,
        "full_clear": 4,
        "partial_unknown": 4,
        "no_support": 2,
    }
    assert len(probe.csv_rows(a)) == 10
    for case in a["cases"]:
        assert case["before"]["reserve"] > case["after"]["reserve"]
        assert case["after"]["historical_dead"] == 1
        assert "Actual Gameforge partial Doctor/Tender allocation" in case["unknown_game_mechanics"]
    assert all(row["independent_game_holdout"] is False
               for row in probe.csv_rows(a))


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
def test_support_and_wound_inputs_reject_invalid_seeds(domain):
    for support_count, injury in ((-1, 5000), (1, -1), (1, 5002)):
        with pytest.raises(ValueError):
            probe._make_case(domain, support_count, injury)


def test_ghost_round2_reserve_hp_repair_is_caught_even_if_rr_event_is_correct(
    monkeypatch,
):
    original = probe._prepare_round_start

    def tamper(waves, events, number, side, applied, **kwargs):
        blocked = original(waves, events, number, side, applied, **kwargs)
        # The RR event remains unchanged. Damage was silently inserted into
        # Reserve after it ran; the independent before/after conservation
        # requirement must catch that corrupt real state.
        waves[0].reserve_damage += 1
        return blocked

    monkeypatch.setattr(probe, "_prepare_round_start", tamper)
    with pytest.raises(AssertionError, match="persistent wounds"):
        probe.audit("land_doctor", 0, 5000)


def test_ghost_round2_resurrection_is_caught_with_unchanged_events(monkeypatch):
    original = probe._prepare_round_start

    def tamper(waves, events, number, side, applied, **kwargs):
        blocked = original(waves, events, number, side, applied, **kwargs)
        waves[0].reserve += 1
        return blocked

    monkeypatch.setattr(probe, "_prepare_round_start", tamper)
    with pytest.raises(AssertionError, match="prior casualty"):
        probe.audit("naval_tender", 2, 5000)
