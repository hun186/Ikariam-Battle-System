from ikariam_battle.kill_calibration import (
    IKILL_RULE_ID,
    MKILL_RULE_ID,
    swordsman_flank_kill_adjustment,
)


def test_even_reduced_am_columns_keep_direct_kill_baseline():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=36 * 258,
        prior_damage=0,
        baseline_casualties=18,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=18 * (2 * 258 - 360),
        source_column_hits={position: 6 for position in range(1, 7)},
    )
    assert result is not None
    assert result.mode == "d_kill_even_columns"
    assert (result.casualties, result.persistent_damage) == (18, 0)


def test_historical_divisible_odd_columns_select_indirect_kill():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=18,
        incoming_damage=42 * 15,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 15 - 18),
        source_column_hits={position: 7 for position in range(1, 7)},
    )
    assert result is not None
    assert result.mode == "i_kill_exact_division"
    assert (result.casualties, result.persistent_damage) == (35, 0)


def test_current_strong_swordsman_case_recovers_one_third_overkill():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits={position: 7 for position in range(1, 7)},
    )
    assert result is not None
    assert result.mode == "m_kill_overkill_third"
    assert result.recovered_overkill == 1092
    assert result.extra_casualties == 3
    assert (result.casualties, result.persistent_damage) == (24, 12)


def test_current_weak_swordsman_case_keeps_small_recovered_damage_persistent():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 183,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 183 - 360),
        source_column_hits={position: 7 for position in range(1, 7)},
    )
    assert result is not None
    assert result.mode == "m_kill_overkill_third"
    assert result.recovered_overkill == 42
    assert result.extra_casualties == 0
    assert (result.casualties, result.persistent_damage) == (21, 42)


def test_existing_persistent_damage_participates_in_next_mkill_pool():
    result = swordsman_flank_kill_adjustment(
        initial_units=19,
        hit_points=360,
        incoming_damage=42 * 183,
        prior_damage=42,
        baseline_casualties=18,
        baseline_persistent_damage=100,
        baseline_overkill_discarded=180,
        source_column_hits={position: 7 for position in range(1, 7)},
    )
    assert result is not None
    assert result.mode == "m_kill_overkill_third"
    assert result.recovered_overkill == 60
    assert result.persistent_damage == 160


def test_mixed_column_parity_stays_outside_the_hypothesis():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=1000,
        prior_damage=0,
        baseline_casualties=2,
        baseline_persistent_damage=100,
        baseline_overkill_discarded=180,
        source_column_hits={1: 7, 2: 7, 3: 7, 4: 6, 5: 6, 6: 6},
    )
    assert result is None


def test_rule_ids_are_explicit_experimental_hypotheses():
    assert IKILL_RULE_ID == "EXP-SWORDSMAN-FLANK-IKILL-DIVISIBLE-001"
    assert MKILL_RULE_ID == "EXP-SWORDSMAN-FLANK-MKILL-OVERKILL-THIRD-001"
