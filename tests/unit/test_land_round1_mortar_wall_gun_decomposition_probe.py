"""Verify one exact multi-source numerical fit, not an actual Gameforge trace."""
from tools.research.land_round1_mortar_wall_gun_decomposition_probe import report


def test_mortar_AM_five_mortars_in_six_source_rows_hit_first_six_target_slots():
    data=report()
    assert data["source_artillery_screenshot_counts"] == [6]*5
    assert data["source_AM_address_counts_by_physical"]["mortar"] == [5,5,5,5,5,5,0]
    assert data["source_AM_address_counts_by_physical"]["gun"] == [7,14,14,14,14,14,7]
    assert data["mortar_registry_primary_base_damage"] > data["source_axe_hp"]
    assert data["source_gun_damage_to_axe_F5"] == 710
    assert data["owner_confirmed_forge"] == 5


def test_seven_slot_casualty_total_source_and_mixed_model_exact():
    data=report()
    rows=data["rows"]
    assert data["source_total_axe_deaths"] == data["predicted_total_axe_deaths"] == 80
    assert [r["predicted_deaths"] for r in rows] == [10,13,13,13,13,13,5]
    assert [r["predicted_survivors"] for r in rows] == [40,37,37,37,37,37,45]
    assert [r["predicted_HP_pct_IF_floor_survivor_mean"] for r in rows] == [98,100,100,100,100,100,99]
    assert data["all_seven_slots_match"]
    assert all(r["matches_all_source_dimensions"] for r in rows)


def test_central_pairwise_gun_14_hits_yield_seven_clean_kills_before_other_sources():
    middle=report()["rows"][1:6]
    assert all(row["gun_AM_addresses_CONDITIONAL"]==14 for row in middle)
    assert all(row["gun_kill_type_HYPOTHESIS"]=="HYPOTHETICAL_PAIRWISE_D_KILL" for row in middle)
    assert all(row["gun_kills_if_every_address_fires_full"]==7 for row in middle)
    assert all(row["mortar_AM_addresses_CONDITIONAL"]==5 for row in middle)
    assert all(row["wall_1kill_per_slot_CONDITIONAL"]==1 for row in middle)
    assert all(row["gun_surviving_slot_wounds"]==0 for row in middle)
    assert all(row["gun_overkill_discarded_in_D_control"]==2100 for row in middle)


def test_edges_same_exact_gun_residue_but_different_percent_due_to_population():
    left, right=report()["rows"][0], report()["rows"][-1]
    for edge in (left,right):
        assert edge["gun_AM_addresses_CONDITIONAL"]==7
        assert edge["gun_kill_type_HYPOTHESIS"]=="HYPOTHETICAL_AGGREGATE_DAMAGE_WITH_REMAINDER"
        assert edge["gun_kills_if_every_address_fires_full"]==4
        assert edge["gun_wounds_AFTER_GUN_BEFORE_WALL"]==490
    assert (left["mortar_AM_addresses_CONDITIONAL"],right["mortar_AM_addresses_CONDITIONAL"])==(5,0)
    assert (left["after_mortar_axe_count"],right["after_mortar_axe_count"])==(45,50)
    assert (left["after_guns_before_wall_axe_count"],right["after_guns_before_wall_axe_count"])==(41,46)
    assert (left["wall_victim_preexisting_gun_wounds"],right["wall_victim_preexisting_gun_wounds"])==(11,10)
    assert (left["gun_surviving_slot_wounds"],right["gun_surviving_slot_wounds"])==(479,480)
    assert (left["predicted_survivors"],right["predicted_survivors"])==(40,45)
    assert (left["predicted_HP_pct_IF_floor_survivor_mean"],right["predicted_HP_pct_IF_floor_survivor_mean"])==(98,99)


def test_conditional_success_does_not_recover_game_rules():
    data=report()
    a=data["assumptions_NOT_OBSERVED"]
    assert a["every_mortar_source_attack_is_effective_and_kills_one_Axe"]
    assert a["wall_each_active_physical_slot_exactly_one_lethal_hit"]
    assert a["seven_gun_addresses_use_pooled_damage_and_retain_mod_HP"]
    assert a["fourteen_gun_addresses_use_pairwise_D_Kill_and_waste_overkill"]
    assert a["floor_of_total_surviving_HP_bar_semantics"]
    assert a["other_visible_battle_units_add_no_deaths_to_this_Axe_front_in_round1"]
    assert data["scope"].startswith("Independent new first-round")

def test_wall_is_last_and_gun_residual_is_not_unchanged_after_wall():
    data=report()
    assert data["hypothetical_source_phase_order"]==["mortar","musket","wall"]
    a=data["assumptions_NOT_OBSERVED"]
    assert a["mortar_before_gun_then_wall_owner_phase_order"]
    assert a["wall_victim_removes_their_previous_gun_wounds"]
    assert a["wall_damage_not_added_to_gun_pool"]
    assert a["wall_victim_exact_wound_share_UNVERIFIED"]
    left,right=data["rows"][0],data["rows"][-1]
    assert left["gun_wounds_AFTER_GUN_BEFORE_WALL"]==right["gun_wounds_AFTER_GUN_BEFORE_WALL"]==490
    assert left["gun_surviving_slot_wounds"]==479
    assert right["gun_surviving_slot_wounds"]==480
    assert left["gun_surviving_slot_wounds"]<490
    assert right["gun_surviving_slot_wounds"]<490
