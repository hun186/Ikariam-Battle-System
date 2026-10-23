"""Round-boundary synthetic Doctor/Tender full-clear-vs-unknown safety tests."""
from copy import deepcopy

import pytest

from tools.research import p0_healing_capacity_boundary_audit as audit


@pytest.mark.parametrize("domain", ("land_doctor", "naval_tender"))
@pytest.mark.parametrize("injury,count,expected", [
    (0, 1, audit.NONE),
    (3999, 1, audit.FULL),
    (4000, 1, audit.FULL),
    (4001, 1, audit.PARTIAL_UNKNOWN),
    (4001, 2, audit.FULL),
])
def test_real_engine_round2_heal_boundary_preserves_dead_and_surviving_hp(
    domain, injury, count, expected,
):
    result = audit.probe(domain, injury, count)
    assert result["execution"] == expected
    assert result["derived_capacity"] == count * 4000
    assert result["seeded_eligible_damage"] == injury
    assert result["evidence_class"] == audit.PROVENANCE
    assert result["actual_game_battle_record"] is False
    assert result["game_healing_allocation_verified"] is False
    assert result["round"] == 2

    before, after = result["before"], result["after"]
    assert before.keys() == after.keys()
    assert len(before) == (3 if domain == "land_doctor" else 2)
    for key in before:
        assert before[key]["historical_dead"] == 1
        assert after[key]["historical_dead"] == 1
        assert before[key]["alive"] == after[key]["alive"]
        assert before[key]["reserve"] == after[key]["reserve"] == 0
    if expected == audit.FULL:
        assert any(e["type"] == "healing" for e in result["events"])
        assert not any(e["type"] == "healing_allocation_unresolved" for e in result["events"])
    elif expected == audit.PARTIAL_UNKNOWN:
        assert not any(e["type"] == "healing" for e in result["events"])
        assert any(e["type"] == "healing_allocation_unresolved" for e in result["events"])
        assert any("HEAL-NONE" in x for x in result["applied_assumption_ids"])
    else:
        assert not any(e["type"] in ("healing", "healing_allocation_unresolved")
                       for e in result["events"])


def test_doctors_never_heal_machine_even_when_humans_fully_healed():
    result = audit.probe("land_doctor", 4001, 2)
    r = result["after"]
    assert r["machines-with-one-death"]["persistent_damage"] == 340
    assert r["machines-with-one-death"]["alive"] == 2
    assert r["swords-with-one-death"]["persistent_damage"] == 0
    assert r["hoplites-with-one-death"]["persistent_damage"] == 0
    assert result["before"]["machines-with-one-death"]["persistent_damage"] == 340
    detail = [e["details"] for e in result["events"] if e["type"] == "healing"][0]
    assert "gyrocopter" not in detail["affected_units"]
    assert set(detail["affected_units"]) == {"swordsman", "hoplite"}
    assert sum(detail["affected_units"].values()) == 4001


def test_tender_repairs_two_distinct_naval_class_waves_at_full_clear():
    result = audit.probe("naval_tender", 4000, 1)
    assert result["before"]["rams-with-one-death"]["persistent_damage"] == 2000
    assert result["before"]["carriers-with-one-death"]["persistent_damage"] == 2000
    assert result["after"]["rams-with-one-death"]["persistent_damage"] == 0
    assert result["after"]["carriers-with-one-death"]["persistent_damage"] == 0
    detail = [e["details"] for e in result["events"] if e["type"] == "healing"][0]
    assert detail["affected_units"] == {"ram_ship": 2000, "balloon_carrier": 2000}
    assert detail["unused_capacity"] == 0


@pytest.mark.parametrize("domain,rule,assumption", [
    ("land_doctor", "UNKNOWN-HEALING-ALLOCATION", "EXP-HEAL-NONE-001"),
    ("naval_tender", "UNKNOWN-TENDER-HEALING-ALLOCATION", "EXP-TENDER-HEAL-NONE-001"),
])
def test_one_hp_over_capacity_fails_closed_without_fictional_partial_repair(
    domain, rule, assumption,
):
    result = audit.probe(domain, 4001, 1)
    warnings = [e for e in result["events"] if e["type"] == "healing_allocation_unresolved"]
    assert len(warnings) == 1
    details = warnings[0]["details"]
    assert details["capacity"] == 4000
    assert details["eligible_damage"] == details["unresolved_damage"] == 4001
    assert details["rule_id"] == rule
    assert details["action"] == "no_partial_healing_applied"
    assert assumption in result["applied_assumption_ids"]
    for key, before in result["before"].items():
        assert result["after"][key]["persistent_damage"] == before["persistent_damage"]


def test_report_determinism_no_historical_holdout_and_exported_state():
    first = audit.build_report()
    second = audit.build_report()
    assert first == second
    assert first["summary"] == {
        "synthetic_boundary_cases": 10,
        "game_observed_cases": 0,
        "independent_holdouts": 0,
        "full_clear": 6,
        "partial_allocation_unknown": 2,
        "zero_eligible_damage": 2,
    }
    assert [x["execution"] for x in first["cases"][:5]] == [
        audit.NONE, audit.FULL, audit.FULL, audit.PARTIAL_UNKNOWN, audit.FULL,
    ]
    flat = audit.csv_rows(first)
    assert len(flat) == 10
    assert all(x["independent_holdout"] is False for x in flat)
    assert all(x["original_deaths_protected"] for x in flat)
    assert all("before_hp_by_wave" in x and "after_hp_by_wave" in x for x in flat)
    for item in first["cases"]:
        assert len(item["round2_snapshot"]["slots"]) == (
            3 if item["domain"] == "land_doctor" else 2
        )


@pytest.mark.parametrize("domain", ["land_doctor", "naval_tender"])
def test_invalid_seeded_wounds_and_support_counts_are_rejected(domain):
    with pytest.raises(ValueError, match="supporters"):
        audit._seeded_waves(domain, 4001, 0)
    with pytest.raises(ValueError, match="nonnegative"):
        audit._seeded_waves(domain, -1, 1)
    with pytest.raises(ValueError, match="exceed surviving"):
        audit._seeded_waves(domain, 12000, 1)


def test_negative_mutation_of_real_healing_state_is_detected(monkeypatch):
    real = audit._prepare_round_start

    def fake_round_start(waves, events, number, side, applied, **kwargs):
        value = real(waves, events, number, side, applied, **kwargs)
        # Simulate a bug: record a correct healing event but leave a patient's
        # living HP damaged. Our state assertion must catch this independent
        # of the event-ledger's self-reported healing quantity.
        waves[0].slots[0].damage += 1
        return value

    monkeypatch.setattr(audit, "_prepare_round_start", fake_round_start)
    with pytest.raises(ValueError, match="surviving HP changed unexpectedly"):
        audit.probe("naval_tender", 4000, 1)
