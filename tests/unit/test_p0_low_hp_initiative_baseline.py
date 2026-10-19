"""P0 real-engine timing guards for low-HP land unit casualties.

These are SYNTHETIC controlled formations, NOT owner-observed game reports.
Help-derived line ordering and phase-start eligibility are known. Within-slot
Accuracy / special kill mode are still EXPERIMENTAL and not calibrated by these tests.
"""
from ikariam_battle import simulate
from ikariam_battle.kill_calibration import swordsman_flank_kill_adjustment


def _case(attacker, defender, *, rounds=1):
    return simulate({
        "policy": "experimental",
        "battlefield": "land-max",
        "max_rounds": rounds,
        "attacker": {"forge_level": 0, "units": attacker},
        "defender": {"forge_level": 0, "units": defender},
    })


def _unit(unit, quantity, **kwargs):
    return {"unit_id": unit, "quantity": quantity, **kwargs}


def _attacks(result, unit):
    return [
        event for event in result["events"]
        if event["type"] == "damage"
        and event["details"].get("source_unit_id") == unit
    ]


def test_gyrocopter_mirror_both_sides_fire_anti_balloon_same_phase():
    """A same-class opponent may NOT cancel snapshotted reciprocal fire."""
    left = [_unit("hoplite", 350), _unit("gyrocopter", 30)]
    right = [_unit("hoplite", 350), _unit("gyrocopter", 30)]
    result = _case(left, right)
    attacks = _attacks(result, "gyrocopter")
    assert {event["side"] for event in attacks} == {"attacker", "defender"}
    assert {event["details"]["firing_phase"] for event in attacks} == {"anti-balloon"}
    assert all(event["details"]["target_class"] == "anti-balloon" for event in attacks)
    a = result["casualties"]["attacker"].get("gyrocopter", 0)
    d = result["casualties"]["defender"].get("gyrocopter", 0)
    assert a == d and a > 0
    assert result["rounds_completed"] == 1


def test_gyrocopter_early_phase_kill_prevents_later_balloon_fire():
    """Anti-Balloon before Balloon is TRUE prior-phase first strike."""
    attacker = [_unit("hoplite", 350), _unit("gyrocopter", 30)]
    defender = [_unit("hoplite", 350), _unit("bombardier", 1)]
    result = _case(attacker, defender)
    gyro = _attacks(result, "gyrocopter")
    assert gyro
    assert {event["details"]["firing_phase"] for event in gyro} == {"anti-balloon"}
    assert result["casualties"]["defender"].get("bombardier", 0) == 1
    assert not _attacks(result, "bombardier")
    phases = [event["details"]["firing_phase"] for event in result["events"]
              if event["type"] == "formation_fire_phase"]
    assert phases.index("anti-balloon") < phases.index("balloon")


def test_without_gyrocopter_bombardier_still_fires_when_alive():
    """Controls the earlier-stage suppression against an alive Balloon."""
    attacker = [_unit("hoplite", 350)]
    defender = [_unit("hoplite", 350), _unit("bombardier", 1)]
    result = _case(attacker, defender)
    events = _attacks(result, "bombardier")
    assert events
    assert {event["side"] for event in events} == {"defender"}
    assert {event["details"]["firing_phase"] for event in events} == {"balloon"}


def test_swordsman_mirror_same_phase_simultaneity():
    attackers = [_unit("hoplite", 350), _unit("swordsman", 240, attack_upgrade=24,
                                                     armor_upgrade=26)]
    defenders = [_unit("hoplite", 350), _unit("swordsman", 240, attack_upgrade=18,
                                                     armor_upgrade=18)]
    result = simulate({
        "policy": "experimental", "battlefield": "land-max", "max_rounds": 1,
        "attacker": {"forge_level": 5, "units": attackers},
        "defender": {"forge_level": 5, "units": defenders},
    })
    swords = _attacks(result, "swordsman")
    assert {event["side"] for event in swords} == {"attacker", "defender"}
    assert {event["details"]["firing_phase"] for event in swords} == {"flank"}
    assert result["casualties"]["attacker"].get("swordsman", 0) > 0
    assert result["casualties"]["defender"].get("swordsman", 0) > 0
    # Historical same-formation symmetric two-hit special mode is a
    # bounded research model, not a general Accuracy/kill selector.
    ids = {item["id"] for item in result["assumptions"]}
    assert "EXP-SWORDSMAN-SYMMETRIC-2HIT-ROW-PM-MKILL-001" in ids


def test_unequal_two_hit_three_hit_swordsman_mkill_stays_unverified():
    """A 2-hit / reciprocal 3-hit duel must not inherit symmetric M-pool."""
    columns = {index: 7 for index in range(1, 7)}
    counts = {index: 40 for index in range(1, 7)}
    v = swordsman_flank_kill_adjustment(
        initial_units=40, hit_points=360,
        incoming_damage=42 * 259, prior_damage=0,
        baseline_casualties=21, baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 259 - 360),
        source_column_hits=columns, source_slot_units=counts,
        reciprocal_hit_damage=172,
    )
    assert v is None


def test_existing_support_model_must_not_assert_unvalidated_kill_accuracy():
    """Land special low-HP phases are not an officially calibrated kill model."""
    result = _case(
        [_unit("hoplite", 350), _unit("gyrocopter", 30)],
        [_unit("hoplite", 350), _unit("gyrocopter", 30)],
    )
    ids = {item["id"] for item in result["assumptions"]}
    assert "EXP-ACCURACY-CONCENTRATION-001" in ids
    assert "EXP-D-KILL-SEQUENTIAL-001" in ids
