"""Reject one-size-one-hit accounting; keep wall and ammo hypotheses explicit."""
from tools.research.land_round80_89_two_class_am_probe import report, weapon_profiles


def test_derived_weapon_profile_would_one_shot_knifeman_but_two_shot_axe():
    p=weapon_profiles()
    assert p["land_workshop_attack_increase_per_level"] == 5
    k=p["barbarian_targets"]["barbarian_knifeman"]
    a=p["barbarian_targets"]["barbarian_axe_swinger"]
    assert k["target_hp"]==360 and a["target_hp"]==1120
    assert k["shot_damage"] == 635 and k["shots_to_kill_full"]==1
    assert a["shot_damage"] == 615 and a["shots_to_kill_full"]==2
    assert p["source_primary_ammunition_pool_per_unit_battle"]==3
    assert p["attacker_forge_level_is_UNVERIFIED"]==0


def test_81_to_83_per_slot_deaths_exactly_match_two_class_gun_plus_each_wall():
    data=report()
    for row in data["rounds"]:
        if row["round"] not in (81,82,83):
            continue
        assert list(row["modeled_84_musket_AM_by_slot"].values())==[7,14,14,14,14,14,7]
        assert list(row["hypothetical_seven_direct_wall_kills_by_slot"].values())==[1]*7
        assert list(row["observed_deaths_by_occupied_slot"].values())==[8,15,15,8,15,15,8]
        assert row["ordinary_knife_gun_shots_implied_if_one_shot_kill_each"]==70
        assert row["gun_shots_left_for_center_axe_AFTER_knife_kills"]==14
        assert row["axe_gun_kills_required"]==7
        assert row["minimum_near_lethal_wounded_axes_at_round_start"]==0


def test_84_to_87_seven_extra_leftmost_deaths_imply_one_7_shot_AM_row_diversion():
    data=report()
    expected={84:(5,1),85:(5,1),86:(6,3),87:(5,1)}
    for row in data["rounds"]:
        if row["round"] not in expected:continue
        assert row["conditional_exact_one_AM_row_shift_center_to_leftmost"]
        assert row["gun_ordinary_minus_unmodified_AM"]=={
            "1":7,"2":0,"3":0,"5":0,"6":0,"7":0
        }
        assert row["ordinary_knife_gun_shots_implied_if_one_shot_kill_each"]==77
        assert row["gun_shots_left_for_center_axe_AFTER_knife_kills"]==7
        assert row["center_axe_user_reported_deaths"]==expected[row["round"]][0]
        assert row["minimum_near_lethal_wounded_axes_at_round_start"]==expected[row["round"]][1]
        assert row["minimum_initial_carryover_axe_damage_to_support_one_row_shift"]==505*expected[row["round"]][1]


def test_live_survivor_average_bar_raises_discriminating_counterexample():
    # Source UI bar algorithm UNKNOWN. Conditional check only:
    # minimum preexisting wounds for one-row shift exceed compatible
    # prior bar 99% at R83 and 92% at R85, if the bar is the live average.
    r={x["round"]:x for x in report()["rounds"]}
    assert r[84]["previous_round_observed_center_hp_bar_percent"]==99
    assert r[84]["previous_round_center_survivors_from_screenshot"]==21
    assert r[84]["incompatible_IF_bar_floors_average_of_survivor_HP"]
    assert r[86]["previous_round_observed_center_hp_bar_percent"]==92
    assert r[86]["previous_round_center_survivors_from_screenshot"]==11
    assert r[86]["incompatible_IF_bar_floors_average_of_survivor_HP"]
    assert r[87]["previous_round_observed_center_hp_bar_percent"]==96
    assert r[87]["incompatible_IF_bar_floors_average_of_survivor_HP"]
    assert not r[85]["incompatible_IF_bar_floors_average_of_survivor_HP"]


def test_88_and_89_both_exactly_decompose_with_leftmost_wall_fallback():
    d={x["round"]:x for x in report()["rounds"]}
    assert d[88]["modeled_84_musket_AM_by_slot"]=={
        "1":14,"2":14,"3":14,"4":14,"5":14,"6":14
    }
    assert d[88]["hypothetical_seven_direct_wall_kills_by_slot"]=={
        "1":2,"2":1,"3":1,"4":1,"5":1,"6":1
    }
    assert d[88]["observed_deaths_by_occupied_slot"]=={
        "1":16,"2":15,"3":15,"4":15,"5":15,"6":15
    }
    assert d[89]["modeled_84_musket_AM_by_slot"]=={
        "2":21,"3":21,"4":21,"5":21
    }
    assert d[89]["hypothetical_seven_direct_wall_kills_by_slot"]=={
        "2":4,"3":1,"4":1,"5":1
    }
    assert d[89]["observed_deaths_by_occupied_slot"]=={
        "2":25,"3":22,"4":22,"5":22
    }
    assert not d[88]["conditional_exact_one_AM_row_shift_center_to_leftmost"]
    assert d[88]["axe_gun_kills_required"]==0
    assert d[89]["axe_gun_kills_required"]==0


def test_model_no_fabricated_wall_game_trace_or_forge_claims():
    data=report()
    assert data["evidence_class"].startswith("RESEARCH_ONLY")
    assert data["source"]["screenshot_binary_present_in_repository"] is False
    assert data["user_confirmed_wall"][
        "user_confirmed_each_effective_wall_hit_kills_one_barbarian"
    ]
    assert "84 source musketeers" in data["conditional_assumptions"][1]
    assert any("ammunition" in x.lower() for x in data["falsification_guide"])
    assert data["rounds"][0]["excluded_from_wall_controls"]
