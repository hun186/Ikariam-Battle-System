"""User-source-calibrated but still CONDITIONAL experimental naval focus policy.

Invented naval First-line filler is NOT historical evidence. Calibrates only
Round1 two 15-fastboat columns versus two full 3-carrier target slots.
"""
import json

from ikariam_battle.accuracy import (
    NAVAL_FAST_CARRIER_FOCUS_ID,
    NAVAL_FAST_CARRIER_FOCUS_THRESHOLD,
    select_accuracy_target,
)
from tools.research.naval_pvp_fast_carrier_probe import FIXTURE, control_case


def test_explicit_74pct_override_keeps_real_weapon_accuracy():
    base = select_accuracy_target([750, 0, 0], 2800, 250, 95)
    candidate = select_accuracy_target(
        [750, 0, 0], 2800, 250, 95, experimental_focus_threshold=74
    )
    assert base.accuracy == candidate.accuracy == 95
    assert base.focus_threshold_percent == 95
    assert candidate.focus_threshold_percent == 74
    assert candidate.mode == "focus_below_accuracy_threshold"
    assert base.target_index == candidate.target_index == 0
    assert NAVAL_FAST_CARRIER_FOCUS_THRESHOLD == 74


def test_seven_case_74pct_model_not_claimed_held_out_proof():
    # These THREE game death totals are user-reported, but the First-line
    # ship fillers and 16/14 actual effective hit allocation are synthetic.
    data=json.loads(FIXTURE.read_text(encoding="utf-8"))
    predictions=[]
    for case in data["observed"]:
        result=control_case(
            case, attacker_forge=case["attacker_forge_level"],
            defender_forge=case["defender_forge_level"],
        )
        assert result["model_round_matches_confirmed_game_round"]
        assert result["model_am_hit_slots"]==[16, 14]
        assert result["matches_user_confirmed_forge_scope"]
        predictions.append((result["model_total_carrier_deaths"],
                            case["reported_carrier_total_deaths"]))
    assert predictions==[(2,2),(2,2),(1,1)]


def test_engine_event_marks_candidate_separate_from_actual_weapon_accuracy():
    data=json.loads(FIXTURE.read_text(encoding="utf-8"))
    case=data["observed"][2]
    from ikariam_battle import simulate
    scenario={
        "policy":"experimental", "battlefield":"naval-max", "max_rounds":1,
        "attacker":{"forge_level":5,"units":[
            {"unit_id":"steam_ram","quantity":35},
            {"unit_id":"paddle_speedboat","quantity":30,"attack_upgrade":17},
        ]},
        "defender":{"forge_level":5,"units":[
            {"unit_id":"steam_ram","quantity":35},
            {"unit_id":"balloon_carrier","quantity":6,"armor_upgrade":18},
        ]},
    }
    result=simulate(scenario)
    assert result["casualties"]["defender"].get("balloon_carrier")==1
    events=[e for e in result["events"] if e["type"]=="damage"
            and e["details"].get("source_unit_id")=="paddle_speedboat"
            and e["details"].get("target_unit_id")=="balloon_carrier"]
    assert len(events)==2
    assert {e["details"]["accuracy_model"] for e in events}=={
        NAVAL_FAST_CARRIER_FOCUS_ID
    }
    assert {e["details"]["focus_threshold_percent"] for e in events}=={74}
    assert {e["details"]["weapon_accuracy"] for e in events}=={90}
    assert all(NAVAL_FAST_CARRIER_FOCUS_ID in e["details"]["assumption_ids"]
               for e in events)
    assert NAVAL_FAST_CARRIER_FOCUS_ID in {
        assumption["id"] for assumption in result["assumptions"]
    }


def test_unscoped_source_does_not_apply_fitted_74pct_rule():
    from ikariam_battle import simulate
    result=simulate({
        "policy":"experimental", "battlefield":"naval-max", "max_rounds":1,
        "attacker":{"units":[{"unit_id":"steam_ram","quantity":35},
                             {"unit_id":"paddle_speedboat","quantity":29,
                              "attack_upgrade":17}]},
        "defender":{"units":[{"unit_id":"steam_ram","quantity":35},
                             {"unit_id":"balloon_carrier","quantity":6,
                              "armor_upgrade":18}]},
    })
    assert NAVAL_FAST_CARRIER_FOCUS_ID not in {
        assumption["id"] for assumption in result["assumptions"]
    }
