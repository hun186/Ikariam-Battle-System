"""Exact arithmetic regressions for user-reported center-unit HP and deaths."""
from tools.research.land_round80_89_hp_state_probe import (
    floor_survivor_hp_bar_damage_interval as interval,
    r85_to_r86_no_healing_survivor_selection_witness,
    report,
)

def test_integer_damage_ranges_under_conditional_floor_mean_bar():
    assert interval(11,1120,92)==(863,985)
    assert interval(5,1120,96)==(169,224)
    assert interval(21,1120,99)==(1,235)
    assert interval(5,1120,100)==(0,0)

def test_nonmonotonic_bar_can_arise_from_survivor_selection_without_healing():
    witness=r85_to_r86_no_healing_survivor_selection_witness()
    assert not witness["healing_used"]
    assert sum(witness["end_r85_wounds_of_all_eleven_axe_survivors"])==900
    assert sum(witness["end_r86_wounds_of_five_survivors"])==200
    assert witness["actual_game_kill_source_fits_this_witness"]=="UNTESTED"
    observations={x["round"]:x for x in report()["rounds"]}
    assert (observations[85]["survivors"],observations[85]["displayed_HP_bar"])==(11,92)
    assert (observations[86]["survivors"],observations[86]["displayed_HP_bar"])==(5,96)

def test_fourteen_gun_addresses_not_guaranteed_seven_axe_kills():
    for damage in (615,713):
        # Every hit on a distinct healthy Axe => 14 survivors at remaining HP.
        assert sum(w>=1120 for w in [damage]*14)==0
        # Pairing those same 14 hits on seven fresh axes => 7 kills.
        assert sum(w>=1120 for w in [2*damage]*7)==7
