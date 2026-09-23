from ikariam_battle.redistribution import reserve_redistribution


def test_rr_formula_and_damage_preservation():
    # PDF pp. 19-20 (§4.3.1): ds = D/N*s; integer remainder follows standard order.
    result = reserve_redistribution(2, 30, [(2, 10), (1, 10), (3, 10)])
    assert result == {2: 1, 1: 1, 3: 0}
    assert sum(result.values()) == 2


def test_rr_keeps_reserve_share_out_of_deployed_slots():
    result = reserve_redistribution(20, 100, [(2, 30), (1, 30), (3, 30)])
    assert sum(result.values()) == 18
