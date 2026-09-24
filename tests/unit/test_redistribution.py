from ikariam_battle.redistribution import SlotShare, reserve_redistribution


def test_rr_formula_remainder_uses_damage_priority_and_conserves():
    deployed, reserve = reserve_redistribution(2, 30, [SlotShare(2,10),SlotShare(1,10),SlotShare(3,10)])
    assert deployed == {1:1,2:1,3:0}
    assert sum(deployed.values()) + reserve == 2


def test_rr_reserve_share_and_wave_calls_are_isolated():
    first = reserve_redistribution(20,100,[SlotShare(1,30),SlotShare(2,30),SlotShare(3,30)])
    second = reserve_redistribution(5,50,[SlotShare(1,30)])
    assert first == ({1:6,2:6,3:6},2)
    assert second == ({1:3},2)


def test_rr_half_tie_is_explicit_half_up_not_python_ties_even():
    assert reserve_redistribution(1,2,[SlotShare(1,1)]) == ({1:1},0)
