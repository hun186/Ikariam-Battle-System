"""Research-only HP-bar aggregate constraints, not recovered attack traces."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json"


def floor_survivor_hp_bar_damage_interval(survivors: int, unit_hp: int, percent: int) -> tuple[int, int]:
    """Inclusive integer total surviving-unit damage, IF displayed bar=floor(100*mean HP fraction)."""
    if survivors <= 0 or unit_hp <= 0 or not 0 <= percent <= 100:
        raise ValueError("survivors, HP must be positive; bar must be 0..100")
    capacity = survivors * unit_hp
    if percent == 100:
        return 0, 0
    return ((99-percent)*capacity//100+1, (100-percent)*capacity//100)


def r85_to_r86_no_healing_survivor_selection_witness() -> dict:
    """Existential state satisfying both percentage labels, not a mechanism for six kills."""
    # 11 live axes at 92% mean 900 total wounds; 5 at 96% mean 200.
    # Six of the earlier injured axes can later die; the 5 survivors
    # preserve their existing 40 damage each. No healing is needed.
    surviving_damage = [40]*5
    later_dead_damage_at_r85 = [116, 116, 117, 117, 117, 117]
    before = surviving_damage + later_dead_damage_at_r85
    assert sum(before) == 900 and sum(surviving_damage) == 200
    lo85,hi85=floor_survivor_hp_bar_damage_interval(11,1120,92)
    lo86,hi86=floor_survivor_hp_bar_damage_interval(5,1120,96)
    assert lo85 <= sum(before) <= hi85 and lo86 <= sum(surviving_damage) <= hi86
    return {
        "end_r85_wounds_of_all_eleven_axe_survivors": before,
        "end_r86_wounds_of_five_survivors": surviving_damage,
        "damage_to_finish_each_of_six_doomed_at_r85": [1120-x for x in later_dead_damage_at_r85],
        "healing_used": False,
        "actual_game_kill_source_fits_this_witness": "UNTESTED",
    }


def report() -> dict:
    evidence=json.loads(FIXTURE.read_text(encoding="utf-8"))
    result=[]
    for item in evidence["observations"][:8]:
        n=item["central_position_4_axe_bearer_remaining_units"]
        p=item["attacker_main_line_front_survivor_hp_percent_left_to_right"][3]
        result.append({
            "round":item["round"],"survivors":n,
            "round_deaths":item["central_position_4_axe_bearer_deaths"],
            "displayed_HP_bar":p,
            "possible_total_wounds_IF_floor_live_survivor_average": (
                list(floor_survivor_hp_bar_damage_interval(n,1120,p)) if n>0 else None
            ),
        })
    return {
        "kind":"RESEARCH_ONLY_AGGREGATE_HP_STATE_FEASIBILITY",
        "candidate_HP_bar_rule":"floor(100*(1-total survivor wounds/(survivor count*unit HP)))",
        "rule_verified_in_actual_game":False,
        "unit_HP_from_packaged_registry":1120,
        "rounds":result,
        "r85_r86_no_healing_witness":r85_to_r86_no_healing_survivor_selection_witness(),
        "limits":["No individual wounds observed","RR/SR/IR and end-round timing are unknown",
                  "This witness only proves that higher displayed HP after deaths is possible without healing",
                  "The combat shot/damage budget needed to kill the six selected axes remains unproven"],
    }


if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
