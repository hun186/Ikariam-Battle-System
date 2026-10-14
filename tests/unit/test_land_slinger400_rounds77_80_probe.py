"""Owner's 400-Slinger Lv24 four consecutive round source, research-only.

Only tested arithmetical bounds and conservation; NO official Gameforge
damage formula, actual 350 successful primary hits, Forge selection, phase
routing or UI-bar aggregate rule asserted.
"""
from tools.research.land_slinger400_rounds77_80_probe import (
    floored_mean_hp_total_interval, report,
)
import pytest


def test_four_source_rounds_and_slot_compaction_total_are_preserved():
    d=report()
    assert d["user_slinger_workshop_attack_level"]==24
    assert d["user_slinger_total"]==400
    assert d["seven_visible_active_firing_cells"]==[50]*7
    assert d["reserve"]==50
    t=d["by_round"]
    assert [t[str(i)]["front_deaths"] for i in range(77,81)]==[61,123,40,114]
    assert [t[str(i)]["axe_end"] for i in range(77,81)]==[165,154,114,0]
    assert [t[str(i)]["knife_end"] for i in (77,78)]==[93,0]
    assert t["78"]["knife_deaths"]==112
    assert t["79"]["rear_thrower_end"]==217
    assert t["80"]["rear_thrower_end"]==188
    assert t["80"]["rear_thrower_deaths"]==29
    assert all(d["three_count_conservation_checks"].values())


def test_project_seven_50_slinger_slots_AM_addresses_change_on_target_collapse():
    d=report()
    a=d["project_AM_7x50_control_by_occupied_physical_targets"]
    assert [x["total_addresses_if_350_fully_fire"] for x in a]==[350]*3
    assert a[0]["AM_base_addresses_by_physical"]=={
        "1":49,"2":49,"3":49,"4":56,"5":49,"6":49,"7":49,
    }
    assert a[1]["AM_base_addresses_by_physical"]=={
        "2":84,"3":91,"4":91,"5":84,
    }
    assert a[2]["AM_base_addresses_by_physical"]=={
        "3":119,"4":119,"5":112,
    }


def test_HP_budget_intervals_if_and_only_if_floor_mean_bar_and_no_unobserved_HP_input():
    d=report()
    p=d["conditional_floor_surviving_total_HP_ranges"]
    assert p["R78_end_154_living_axe"]==[104431,106151]
    assert p["R79_end_114_living_axe"]==[37029,38301]
    assert p["R78_to_R79_all_axe_HP_removed_range_NO_ADDED_HP"]==[66130,69122]
    assert p["R80_end_188_living_thrower"]==[37825,38422]
    assert p["R80_thrower_HP_removed_range_IF_R79_REAR_FULL_HP"]==[31018,31615]
    assert p["R80_joint_axe_plus_thrower_HP_removed_IF_R79_REAR_FULL_HP"]==[68047,69916]
    assert d["real_hp_bar_floor_mean_rule_VERIFIED"] is False
    assert d["owner_R77_front_start_full_100pct_NOT_CONFIRMED"]


def test_forge0_and5_damage_primary_only_no_game_F5_assertion():
    d=report()
    p={x["slinger_forge_control_NOT_CONFIRMED"]:x for x in d[
        "per_hit_forge_comparison_PRIMARY_only"
    ]}
    assert (p[0]["per_full_primary_hit_to_Axe"],
            p[0]["per_full_primary_hit_to_Knife"],
            p[0]["per_full_primary_hit_to_AxeThrower"])==(160,180,180)
    assert (p[5]["per_full_primary_hit_to_Axe"],
            p[5]["per_full_primary_hit_to_Knife"],
            p[5]["per_full_primary_hit_to_AxeThrower"])==(187,207,207)
    assert p[0]["fresh_full_Axe_hits_to_kill"]==7
    assert p[5]["fresh_full_Axe_hits_to_kill"]==6
    assert p[0]["max_350_primary_full_hit_damage_all_to_Axe"]==56000
    assert p[5]["max_350_primary_full_hit_damage_all_to_Axe"]==65450
    assert p[0]["R78_R79_possible_with_extreme_UP_TO_7_full_hp_wall_Axe_kills"] is False
    assert p[5]["R78_R79_possible_with_extreme_UP_TO_7_full_hp_wall_Axe_kills"] is True
    assert p[0]["R80_best_case_full_primary_shots_needed_if_wall_has_ZERO_attacks_front"]==405
    assert p[5]["R80_front_full_primary_shots_min_if_no_other_attack"]==199
    assert p[5]["R80_rear_full_primary_shots_min_if_no_other_attack"]==150
    assert p[5]["R80_best_case_full_primary_shots_needed_if_wall_has_ZERO_attacks_front"]==349
    assert p[5]["R80_no_wall_full_hit_feasibility_if_at_most350"]
    assert d["actual_forge_active_level_UNKNOWN"]


def test_hp_percentage_as_interval_rejects_invalid_or_missing_units():
    assert floored_mean_hp_total_interval(49,1120,81)==(44453,45001)
    assert floored_mean_hp_total_interval(0,1120,0)==(0,0)
    assert floored_mean_hp_total_interval(1,1120,100)==(1120,1120)
    with pytest.raises(ValueError):
        floored_mean_hp_total_interval(0,1120,81)
    with pytest.raises(ValueError):
        floored_mean_hp_total_interval(-1,1120,81)
