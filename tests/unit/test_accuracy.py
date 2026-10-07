import pytest

from ikariam_battle.accuracy import (
    EXPERIMENTAL_ACCURACY_MODEL_ID,
    select_accuracy_target,
)


def test_low_accuracy_one_shot_does_not_create_a_miss():
    decision = select_accuracy_target([0, 0, 0], unit_hp=1120, hit_damage=5400, accuracy=10)
    assert decision.mode == "one_shot_bypass"
    assert decision.target_index == 0
    assert decision.accuracy == 10


def test_non_one_shot_spreads_while_most_damaged_target_is_above_accuracy_threshold():
    decision = select_accuracy_target([300, 0, 0], unit_hp=3680, hit_damage=300, accuracy=90)
    assert decision.mode == "spread_above_accuracy_threshold"
    assert decision.target_index == 2
    assert decision.focus_remaining_hp_percent == pytest.approx(91.84782608695652)


def test_non_one_shot_focuses_when_remaining_hp_percent_crosses_accuracy_threshold():
    decision = select_accuracy_target([600, 300, 300], unit_hp=3680, hit_damage=300, accuracy=90)
    assert decision.mode == "focus_below_accuracy_threshold"
    assert decision.target_index == 0
    assert decision.focus_remaining_hp_percent == pytest.approx(83.69565217391305)


def test_accuracy_model_id_is_stable():
    assert EXPERIMENTAL_ACCURACY_MODEL_ID == "EXP-ACCURACY-CONCENTRATION-001"


@pytest.mark.parametrize("accuracy", [-1, 101])
def test_accuracy_range_is_validated(accuracy):
    with pytest.raises(ValueError, match="accuracy must be 0..100"):
        select_accuracy_target([0], unit_hp=100, hit_damage=10, accuracy=accuracy)
