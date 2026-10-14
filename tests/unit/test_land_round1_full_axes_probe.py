"""Same-battle R1 snapshot, earlier than R80–89: conditional AM controls."""
from tools.research.land_round1_full_axes_probe import report


def test_round1_source_facts_are_from_same_battle_as_r80_89():
    data=report()
    assert data["fixture"]=="land_barbarian_same_battle_round1_all_seven_axes_20261014"
    assert data["battle_identity"]["owner_explicitly_confirmed_round1_and_round80_89_are_same_battle"]
    assert data["chronology"]=="R1 and R80-R89 are SAME battle, R2-R79 not supplied"
    assert data["owner_confirmed_forge"]==5
    assert data["damage_into_axe_in_current_profile"]==710
    assert data["axe_full_hp_in_current_profile"]==1120
    assert data["AM_addresses_left_to_right"]==[7,14,14,14,14,14,7]
    assert data["observed_deaths"]==[10,13,13,13,13,13,5]
    assert data["observed_end_HP_percent"]==[98,100,100,100,100,100,99]
    assert data["observed_total_Axe_deaths"]==80


def test_the_five_middle_13_deaths_CANNOT_be_14_guns_plus_one_wall_simple_D():
    rows=report()["rows"]
    assert [x["D_pairwise_gun_deaths"] for x in rows]==[3,7,7,7,7,7,3]
    assert [x["D_with_one_wall_deaths"] for x in rows]==[4,8,8,8,8,8,4]
    assert [x["D_deaths_shortfall_against_source"] for x in rows]==[6,5,5,5,5,5,1]
    assert all(x["D_with_one_wall_end_HP_pct_IF_floormean"]==100 for x in rows[1:6])
    assert data_has_missing_damage_sources(report())


def data_has_missing_damage_sources(result: dict)->bool:
    return result["unmodeled_artillery_and_side_sources_in_screenshot"]


def test_rightmost_seven_guns_plus_wall_aggregate_matches_5_deaths_and_99bar():
    rows=report()["rows"]
    assert [x["pool_with_one_wall_deaths"] for x in rows]==[5,9,9,9,9,9,5]
    assert [x["pool_deaths_shortfall_against_source"] for x in rows]==[5,4,4,4,4,4,0]
    assert report()["total_gap_vs_pairwise_D_plus_seven_walls"]==32
    assert report()["total_gap_vs_conserved_pool_plus_seven_walls"]==25
    right=rows[-1]
    assert right["pool_gun_deaths"]==4
    assert right["pool_end_wounds_after_wall"]==480
    assert right["pool_with_one_wall_end_HP_pct_IF_floormean"]==99
    assert right["pool_matches_both_count_and_HP"]
    assert not rows[0]["pool_matches_both_count_and_HP"]
    assert not any(x["pool_matches_both_count_and_HP"] for x in rows[1:6])


def test_first_round_outer_residual_wounds_do_not_require_small_slot_population():
    rows=report()["rows"]
    assert all(x["observed_end_units"]+x["observed_deaths"]==50 for x in rows)
    assert rows[0]["observed_display_HP_pct"]==98
    assert rows[-1]["observed_display_HP_pct"]==99
    assert rows[0]["CURRENT_ENGINE_AM_model_address_count"]==7
    assert rows[-1]["CURRENT_ENGINE_AM_model_address_count"]==7
