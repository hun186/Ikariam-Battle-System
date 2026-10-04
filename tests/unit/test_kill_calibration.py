from ikariam_battle.kill_calibration import (
    IKILL_RULE_ID,
    MKILL_RULE_ID,
    d_kill_backbone,
    swordsman_flank_kill_adjustment,
)


SIX_ODD_COLUMNS = {position: 7 for position in range(1, 7)}
SIX_EVEN_COLUMNS = {position: 6 for position in range(1, 7)}
FULL_SOURCE = {position: 40 for position in range(1, 7)}


def test_d_kill_backbone_exposes_n_hit_regimes_and_one_shot_boundary():
    three_hit = d_kill_backbone(360, 172, 42)
    assert (three_hit.hits_to_kill, three_hit.kills, three_hit.overkill_per_kill) == (
        3, 14, 156
    )
    two_hit = d_kill_backbone(360, 259, 42)
    assert (two_hit.hits_to_kill, two_hit.kills, two_hit.overkill_per_kill) == (
        2, 21, 158
    )
    one_shot = d_kill_backbone(360, 500, 36)
    assert (one_shot.hits_to_kill, one_shot.kills) == (1, 36)


def test_even_reduced_am_columns_keep_direct_kill_baseline():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=36 * 258,
        prior_damage=0,
        baseline_casualties=18,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=18 * (2 * 258 - 360),
        source_column_hits=SIX_EVEN_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=183,
    )
    assert result is not None
    assert result.mode == "d_kill_even_columns"
    assert (result.casualties, result.persistent_damage) == (18, 0)


def test_historical_divisible_six_odd_columns_select_indirect_kill():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=18,
        incoming_damage=42 * 15,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 15 - 18),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=15,
    )
    assert result is not None
    assert result.mode == "i_kill_exact_division"
    assert (result.casualties, result.persistent_damage) == (35, 0)


def test_exact_division_outside_six_odd_columns_stays_generic():
    columns = {1: 6, 2: 6, 3: 6, 4: 6, 5: 3}
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=sum(columns.values()) * 200,
        prior_damage=0,
        baseline_casualties=13,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=0,
        source_column_hits=columns,
        source_slot_units={1: 40, 2: 40, 3: 40, 4: 40, 5: 20},
        reciprocal_hit_damage=200,
    )
    assert result is None


def test_2026_06_25_strong_case_uses_symmetric_two_hit_row_pm_pool():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=183,
    )
    assert result is not None
    assert result.mode == "m_kill_symmetric_two_hit_row_pm"
    assert result.baseline_d_kills == 21
    assert result.retained_overkill_events == 7
    assert result.recovered_overkill == 1092
    assert result.hits_to_kill == result.reciprocal_hits_to_kill == 2
    assert (result.casualties, result.persistent_damage) == (24, 12)


def test_phase_start_rr_damage_is_added_to_bounded_row_pm_pool():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=1,
        baseline_casualties=21,
        baseline_persistent_damage=1,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=183,
    )
    assert result is not None
    assert (result.casualties, result.persistent_damage) == (24, 13)


def test_2026_06_25_weak_case_predicts_21_deaths_and_42_damage():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 183,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 183 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=258,
    )
    assert result is not None
    assert result.mode == "m_kill_symmetric_two_hit_row_pm"
    assert result.baseline_d_kills == 21
    assert result.retained_overkill_events == 7
    assert result.recovered_overkill == 42
    assert (result.casualties, result.persistent_damage) == (21, 42)


def test_incomplete_source_formation_does_not_select_full_formation_mkill():
    source = dict(FULL_SOURCE)
    source[6] = 37
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=source,
        reciprocal_hit_damage=183,
    )
    assert result is None


def test_2026_10_02_asymmetric_two_hit_three_hit_duel_does_not_reuse_old_mkill():
    strong = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 259,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 259 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=172,
    )
    weak = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 172,
        prior_damage=0,
        baseline_casualties=14,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=14 * (3 * 172 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=259,
    )
    assert strong is None
    assert weak is None


def test_other_odd_or_mixed_column_shapes_stay_on_generic_baseline():
    columns = {1: 7, 2: 7, 3: 7, 4: 6, 5: 6, 6: 6}
    total_hits = sum(columns.values())
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=total_hits * 183,
        prior_damage=0,
        baseline_casualties=total_hits // 2,
        baseline_persistent_damage=183,
        baseline_overkill_discarded=0,
        source_column_hits=columns,
        source_slot_units=FULL_SOURCE,
        reciprocal_hit_damage=258,
    )
    assert result is None


def test_rule_ids_are_explicit_experimental_hypotheses():
    assert IKILL_RULE_ID == "EXP-SWORDSMAN-FLANK-IKILL-EXACT-DIVISION-001"
    assert MKILL_RULE_ID == "EXP-SWORDSMAN-SYMMETRIC-2HIT-ROW-PM-MKILL-001"
