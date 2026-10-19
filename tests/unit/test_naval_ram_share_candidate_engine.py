"""Real experimental engine gates for bounded six-Ram focus and pooled wounds.

Owner observations: six slots with 1 player Ram sunk (DEF3..14), zero
(DEF15..18), and DEF19 survivor bar63%; reverse Ram ATT20 3 Deckwreckers
sunk per slot and 88% bar. Synthetic front fillers are NOT owner-observed.
"""
from ikariam_battle.naval_focus import (
    NAVAL_DECK_OVERKILL_RULE_ID, NAVAL_RAM_SHARE_RULE_ID,
    empirical_focus_fraction, recover_baseline_dkill_overkill,
    six_ram_hull_share_candidate,
)
from tools.research.naval_ram_empirical_probe import model_one_controlled_round


def test_accuracy80_six_ram_share_is_rational_four_ninths_not_weapon_hit_miss():
    fraction=empirical_focus_fraction(80, 6)
    assert fraction.numerator==4 and fraction.denominator==9
    assert empirical_focus_fraction(95,3).numerator==13
    assert empirical_focus_fraction(95,3).denominator==18


def test_ram_share_crosses_defense14_vs15_while_both_need_three_full_hits():
    for hit,expected_deaths,focus in (
        (1160,1,3093),(1150,0,3066),(1110,0,2960),
    ):
        z=six_ram_hull_share_candidate(
            initial_units=6, hp=3080, shots=6,
            hit_damage=hit, accuracy=80,
        )
        assert z is not None
        assert z.initial_focus_damage==focus
        assert z.deaths==expected_deaths
        assert len(z.survivors_damage)==6-expected_deaths
        assert all(0<=d<3080 for d in z.survivors_damage)
        assert sum(z.survivors_damage)+z.deaths*3080+z.discarded_overkill==6*hit


def test_ram_engine_six_flank_slots_match_observed_defense14_to19_cliff():
    for level,deaths in ((14,6),(15,0),(19,0)):
        r=model_one_controlled_round(level,fill_front=True)
        assert r["synthetic_front_filled"]
        assert r["defender_player_deaths"]==deaths
        slots=r["round1_unit_slots_all_lines"]["defender"]
        assert len(slots)==6
        assert {s["line"] for s in slots}=={"flank"}
        assert [s["casualties"] for s in slots]==[deaths//6]*6
        if level==19:
            assert all(int(100*(s["units"]*3080-s["damage"])
                               /(s["units"]*3080))==63 for s in slots)
        events=[e for e in [e for e in r["round1_events"] if e["type"]=="damage"]
                if e["details"]["source_unit_id"]=="barbarian_deckwrecker"
                and e["details"]["target_unit_id"]=="ram_ship"]
        assert events
        assert all(e["details"]["resolution"]=="naval_bounded_empirical_focus_pool"
                   and NAVAL_RAM_SHARE_RULE_ID in e["details"]["assumption_ids"]
                   and e["details"]["focus_share_fraction"]=="4/9"
                   for e in events)


def test_reverse_ram_overkill_recovery_fits_3_deck_losses_88percent_survivors():
    r=model_one_controlled_round(19,attack_upgrade=20,fill_front=True)
    assert r["attacker_barbarian_deaths"]==18
    slots=r["round1_unit_slots_all_lines"]["attacker"]
    assert len(slots)==6
    assert all(s["casualties"]==3 and s["units"]==3 for s in slots)
    assert all(s["damage"]==1050 for s in slots)
    assert all(int(100*(s["units"]*3080-s["damage"])
                       /(s["units"]*3080))==88 for s in slots)
    events=[e for e in r["model_source_damage_events"]
            if e["details"]["source_unit_id"]=="ram_ship"
            and e["details"]["target_unit_id"]=="barbarian_deckwrecker"]
    assert events and all(
        NAVAL_DECK_OVERKILL_RULE_ID in e["details"]["assumption_ids"]
        and e["details"]["retained_baseline_overkill_HP"]==1050
        for e in events
    )


def test_reverse_overkill_allocator_never_revives_dead_or_kills_from_extra_hp():
    assert recover_baseline_dkill_overkill([0,0,0],1050,3080)==(350,350,350)
    assert recover_baseline_dkill_overkill([3050],100,3080) is None
    assert six_ram_hull_share_candidate(initial_units=5,hp=3080,shots=6,
                                       hit_damage=1160,accuracy=80) is None
