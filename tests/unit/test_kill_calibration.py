from ikariam_battle.kill_calibration import (
    IKILL_RULE_ID,
    MKILL_RULE_ID,
    swordsman_flank_kill_adjustment,
)


SIX_ODD_COLUMNS = {position: 7 for position in range(1, 7)}
SIX_EVEN_COLUMNS = {position: 6 for position in range(1, 7)}


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
        source_column_hits=SIX_ODD_COLUMNS,
    )
    assert result is not None
    assert result.mode == "i_kill_exact_division"
    assert (result.casualties, result.persistent_damage) == (35, 0)


def test_current_strong_case_uses_odd_tail_plus_capped_pm_recount():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
    )
    assert result is not None
    assert result.mode == "m_kill_odd_column_p_m_recount"
    assert result.baseline_d_kills == 18
    assert result.odd_column_count == 6
    assert result.odd_tail_damage == 1548
    assert result.p_m_recount_per_odd_column == 102
    assert result.recovered_overkill == 612
    assert (result.casualties, result.persistent_damage) == (24, 0)


def test_one_point_prior_rr_damage_makes_strong_case_report_99_percent_compatible():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 258,
        prior_damage=1,
        baseline_casualties=21,
        baseline_persistent_damage=1,
        baseline_overkill_discarded=21 * (2 * 258 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
    )
    assert result is not None
    assert (result.casualties, result.persistent_damage) == (24, 1)
    # 16 survivors -> 5760 HP; 1 point is within the old report model's
    # 1%-damage interval, hence compatible with a displayed 99% life value.


def test_current_weak_case_predicts_21_deaths_and_54_damage():
    result = swordsman_flank_kill_adjustment(
        initial_units=40,
        hit_points=360,
        incoming_damage=42 * 183,
        prior_damage=0,
        baseline_casualties=21,
        baseline_persistent_damage=0,
        baseline_overkill_discarded=21 * (2 * 183 - 360),
        source_column_hits=SIX_ODD_COLUMNS,
    )
    assert result is not None
    assert result.mode == "m_kill_odd_column_p_m_recount"
    assert result.baseline_d_kills == 18
    assert result.odd_tail_damage == 1098
    assert result.p_m_recount_per_odd_column == 6
    assert result.recovered_overkill == 36
    assert (result.casualties, result.persistent_damage) == (21, 54)
    assert 1 <= result.persistent_damage <= 68


def test_mixed_column_parity_uses_same_odd_column_accounting_not_fixture_lookup():
    # The hypothesis is intentionally column-derived; it is not tied to the
    # exact 6x7 user fixture. This synthetic shape verifies the calculation is
    # driven by the reduced-AM column counts.
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
    )
    assert result is not None
    assert result.mode == "m_kill_odd_column_p_m_recount"
    assert result.odd_column_count == 3


def test_rule_ids_are_explicit_experimental_hypotheses():
    assert IKILL_RULE_ID == "EXP-SWORDSMAN-FLANK-IKILL-EXACT-DIVISION-001"
    assert MKILL_RULE_ID == "EXP-SWORDSMAN-FLANK-ODD-COLUMN-PM-RECOUNT-001"
