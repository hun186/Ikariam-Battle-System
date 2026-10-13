"""Observable-first naval Accuracy inverse candidates, research ONLY.

Evaluates executable selectors against held-out casualty / surviving HP bars.
In-game per-ship hits are NOT visible. One shot per initially deployed source
ship, full AM 16/14 addressed hits and chosen synthetic target slot populations
are CONDITIONAL experimental inputs, not historical ship-by-ship telemetry.
No production Accuracy, damage, AM, Forge or overkill function is changed.
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path

from tools.research.naval_ram_empirical_probe import _damage_trace, net_damage_math

ROOT = Path(__file__).resolve().parents[2]
AIR_FIXTURE = ROOT / "tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json"
PVP_FIXTURE = ROOT / "tests/fixtures/reverse_engineering/naval_pvp_fast_boat_carrier_20261013.json"
RAM_FIXTURE = ROOT / "tests/fixtures/reverse_engineering/naval_ram_deckwrecker_20261013.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_target(damages: list[int], hp: int, hit: int, threshold: float | None) -> int:
    """Independent within-slot selector following a testable generic pattern.

    threshold=None -> always distribute to healthiest.
    threshold=100 -> always focus wounded.
    Other threshold -> focus when most wounded survivor's remaining HP percent
    is <= threshold. This is NOT an approved or inferred game mechanic.
    """
    if not damages:
        raise ValueError("Cannot select from an empty target slot")
    if hit < 0 or hp <= 0:
        raise ValueError("Invalid HP/hit damage")
    top = max(damages)
    if hit >= hp:
        return damages.index(top)
    if threshold is not None and top > 0 and (hp - top) * 100 <= hp * threshold:
        return damages.index(top)
    smallest = min(damages)
    return max(i for i, damage in enumerate(damages) if damage == smallest)


def simulate_slot(
    hp: int, initial_units: int, successful_hits: int, hit_damage: int,
    threshold: float | None,
) -> dict:
    """Individual, integer, successful hits; discard lethal overflow.

    Callers MUST distinguish model-chosen hits from actual observed game hits.
    Reuses none of the observed casualties to choose the next target.
    """
    if not 0 <= successful_hits or not 0 < initial_units or hp <= 0 or hit_damage < 0:
        raise ValueError("Invalid slot parameters")
    damages = [0] * initial_units
    deaths = lost_overkill = 0
    for _ in range(successful_hits):
        if not damages:
            break
        position = select_target(damages, hp, hit_damage, threshold)
        next_damage = damages[position] + hit_damage
        if next_damage >= hp:
            deaths += 1
            lost_overkill += next_damage - hp
            damages.pop(position)
        else:
            damages[position] = next_damage
    remaining = len(damages)
    survived_damage = sum(damages)
    bar = (
        (remaining * hp - survived_damage) * 100 / (remaining * hp)
        if remaining else None
    )
    # Counterfactual alternative: allocate the overkill discarded by the above
    # simulation back into the remaining slot. Not a complete target allocator.
    retained_bar = (
        (remaining * hp - survived_damage - lost_overkill) * 100 / (remaining * hp)
        if remaining else None
    )
    return {
        "deaths": deaths,
        "remaining_units": remaining,
        "per_survivor_damage": sorted(damages),
        "overkill_discarded": lost_overkill,
        "surviving_hp_percent_no_carry": bar,
        "hypothetical_hp_percent_overkill_retained": retained_bar,
        "hypothetical_retention_valid_nonnegative": (
            retained_bar is not None and retained_bar >= 0
        ),
    }


def _air_cases() -> list[dict]:
    air, pvp = _read(AIR_FIXTURE), _read(PVP_FIXTURE)
    result = []
    for case in air["observed"]:
        if case["case"].startswith("player_fast_"):
            # Retain reverse case as a bar/overkill validation, not a seven
            # case death-count fit for an identical target type.
            continue
        attacker, target, damage = _damage_trace(
            case["attacker"], case["target"],
            armor_upgrade=case["player_defense_upgrade"],
            target_forge=case["player_forge_level"],
        )
        result.append({
            "id": case["case"], "group": "barbarian_fast_to_player_carrier",
            "observed_total_deaths": case["reported_player_total_deaths"],
            "observed_bars": case.get("reported_occupied_slot_bars_percent"),
            "hp": target.hit_points, "weapon_accuracy": attacker.primary_weapon.accuracy,
            "effective_hit": damage.final_damage,
            "initial_units_per_target_slot": case["target_units_per_position"],
            "modeled_successful_hits_per_slot": [16, 14],
            "assumptions": "full 30-shot AM and 2x3 target slots; no shot misses or other fleets",
            "source": "USER_CHAT",
        })
    for case in air["additional_observations"]:
        if not case.get("attacker_and_target_counts_verified_for_this_case"):
            raise ValueError("Additional air fleet counts are not independently confirmed")
        if case.get("observed_round_number") != 1:
            raise ValueError("Additional air source round must be confirmed")
        attacker, target, damage = _damage_trace(
            "barbarian_dirigible_igniter", "balloon_carrier",
            armor_upgrade=case["observed_player_defense_upgrade"],
            target_forge=case["observed_player_forge_level"],
        )
        result.append({
            "id": case["case"], "group": "barbarian_fast_to_player_carrier",
            "observed_total_deaths": case["observed_total_player_carrier_deaths"],
            "observed_bars": case["observed_bars_percent"],
            "hp": target.hit_points, "weapon_accuracy": attacker.primary_weapon.accuracy,
            "effective_hit": damage.final_damage,
            "initial_units_per_target_slot": case["confirmed_target_slot_counts"][0],
            "modeled_successful_hits_per_slot": [16, 14],
            "assumptions": "round1 and 30v6 confirmed; hit allocation and per-slot deaths NOT observed",
            "source": "USER_CHAT",
        })
    for case in pvp["observed"]:
        if not case["both_forge5_confirmed_by_user"] or case["observed_round_number"] != 1:
            raise ValueError("Must not fit source with unconfirmed Forge/Round")
        attacker, target, damage = _damage_trace(
            case["attacker_unit_id"], case["defender_unit_id"],
            attack_upgrade=case["attacker_attack_upgrade"],
            armor_upgrade=case["defender_armor_upgrade"],
            attacker_forge=case["attacker_forge_level"],
            target_forge=case["defender_forge_level"],
        )
        result.append({
            "id": case["case"], "group": "player_fast_to_player_carrier",
            "observed_total_deaths": case["reported_carrier_total_deaths"],
            "observed_bars": None,
            "hp": target.hit_points, "weapon_accuracy": attacker.primary_weapon.accuracy,
            "effective_hit": damage.final_damage,
            "initial_units_per_target_slot": 3,
            "modeled_successful_hits_per_slot": [16, 14],
            "assumptions": "both Forge5 and round1 confirmed, but true per-slot kills and other fleet unknown",
            "source": "USER_CHAT",
        })
    return result


def predicted(case: dict, threshold: float | None) -> dict:
    slots = [
        simulate_slot(
            case["hp"], case["initial_units_per_target_slot"], hits,
            case["effective_hit"], threshold,
        )
        for hits in case["modeled_successful_hits_per_slot"]
    ]
    return {
        "case_id": case["id"], "threshold": threshold,
        "source": case["source"],
        "observed_total_deaths": case["observed_total_deaths"],
        "candidate_deaths": sum(s["deaths"] for s in slots),
        "matches_reported_total": (
            sum(s["deaths"] for s in slots) == case["observed_total_deaths"]
        ),
        "model_slot_results": slots,
        "observed_bars": case["observed_bars"],
        "modelled_successful_hit_counts_not_game_trace": case["modeled_successful_hits_per_slot"],
    }


def _ram_holdout(threshold: float | None) -> list[dict]:
    workbook = _read(RAM_FIXTURE)
    source = workbook["observed"]["player_deaths_total_by_defense_upgrade"]
    result = []
    for level in (14, 15, 19):
        math = net_damage_math(level)
        calc = simulate_slot(
            math["player_hp"], 6, 6, math["barbarian_net_hit"], threshold,
        )
        observed_per_slot = (
            workbook["observed"]["direct_chat_position_claims"][
                "defense_upgrades_3_to_14_each_slot_deaths"
            ] if level == 14 else
            workbook["observed"]["direct_chat_position_claims"]["defense_15_each_slot_deaths"]
            if level == 15 else 0
        )
        # Defense19 game result is a separate chat case, not a workbook row.
        result.append({
            "case_id": f"ram_defense_{level}",
            "source": "WORKBOOK_TOTAL_PLUS_SEPARATE_CHAT_SLOT_CLAIM" if level != 19 else "CHAT_ONLY_DEF19",
            "observed_player_deaths_per_reported_slot": observed_per_slot,
            "synthetic_six_hit_model_deaths": calc["deaths"],
            "matches_observed": calc["deaths"] == observed_per_slot,
            "conditional_net_hit": math["barbarian_net_hit"],
            "model_slot": calc,
            "warnings": "Six synthetic shots/slot are NOT observed per-ship hit data",
        })
    return result


def _reverse_bars(threshold: float | None) -> dict:
    air = _read(AIR_FIXTURE)
    case = next(x for x in air["observed"] if x["case"].startswith("player_fast_"))
    attacker, target, damage = _damage_trace(
        case["attacker"], case["target"],
        attack_upgrade=case["player_attack_upgrade"],
        attacker_forge=case["player_forge_level"],
    )
    slots = [
        simulate_slot(target.hit_points, case["target_units_per_position"], hits,
                      damage.final_damage, threshold)
        for hits in (16, 14)
    ]
    return {
        "source": "USER_CHAT_ROUND1_30v6",
        "attacker_accuracy": attacker.primary_weapon.accuracy,
        "net_hit": damage.final_damage,
        "observed_deaths_per_slot": case["reported_barbarian_deaths_per_position"],
        "observed_hp_bars": case["reported_survivor_slot_bars_percent"],
        "model_deaths_per_slot": [s["deaths"] for s in slots],
        "model_bars_discard_overkill": [
            int(s["surviving_hp_percent_no_carry"]) for s in slots
        ],
        "counterfactual_bars_if_discarded_overkill_reallocated": [
            int(s["hypothetical_hp_percent_overkill_retained"]) for s in slots
        ],
        "lost_overkill_by_slot": [s["overkill_discarded"] for s in slots],
        "warnings": "A hypothetical conserved-damage bar is NOT proof that Gameforge redistributes lethal overkill",
    }


@lru_cache(maxsize=1)
def report() -> dict:
    cases = _air_cases()
    by_t = []
    # 0.01 percentage-point grid, including both endpoints. Identifies a
    # candidate interval on THESE seven fitting cases only; never calls
    # an observed casualty a computed input to the forward selector.
    for p in range(0, 10001):
        threshold = p / 100
        if all(predicted(c, threshold)["matches_reported_total"] for c in cases):
            by_t.append(p)
    best = [by_t[0] / 100, by_t[-1] / 100] if by_t else None
    baseline = [predicted(c, c["weapon_accuracy"]) for c in cases]
    t74 = [predicted(c, 74.0) for c in cases]
    bars = _reverse_bars(74.0)
    ram = _ram_holdout(74.0)
    return {
        "schema_version": 1,
        "evidence_class": "RESEARCH_ONLY_CANDIDATE_NOT_GAME_RULE",
        "conditional_inputs": {
            "successful_am_shots_by_target_slot": [16, 14],
            "assume_all_30_speedboats_fire_one_successful_hit": True,
            "assume_initial_full_hp_target_carriers": True,
            "selector":"focus most damaged survivor if remaining HP% <= threshold, otherwise spread healthiest survivor; integer lethal hits with excess discarded",
            "testing_threshold_against_all_7_air_casualty_cases_is_IN_SAMPLE_FIT": True,
            "forges":"read from current production profile and independently source-tagged user observations",
            "does_not_use_individual_actual_game_shot_sequences": True,
        },
        "seven_observed_air_cases": cases,
        "current_accuracy_percentage_used_as_focus_threshold": baseline,
        "candidate_74_percent_focus_threshold": t74,
        "fitting_percentage_point_interval_grid_0_01": best,
        "fitting_threshold_count_in_grid": len(by_t),
        "out_of_family_ram_six_hit_holdouts": ram,
        "reverse_player_fast_to_barbarian_carrier_bars": bars,
        "guardrails": [
            "7/7 matching is IN-SAMPLE, not evidence of official formula, independent hit success or correct mixed-fleet setup.",
            "Source Accuracy 90 and 95 are NOT proven to be percentages for focus.",
            "The same threshold is INVALID for Ram 14->15 drop; do not patch global accuracy.py.",
            "Reverse residual 53/65 bars cannot be explained by discarded-overkill at a candidate threshold.",
            "Do not silently transfer overkill into production until independent observations discriminate pooling vs transfer.",
            "Real game logs do not reveal individual hits; model traces are hypotheses only.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Candidate focus threshold window (0.01pp grid): "
          f"{data['fitting_percentage_point_interval_grid_0_01']}; "
          f"count={data['fitting_threshold_count_in_grid']}")
    for case in data["candidate_74_percent_focus_threshold"]:
        print(f"{case['case_id']}: user={case['observed_total_deaths']}, "
              f"candidate={case['candidate_deaths']}, "
              f"candidate_slot_deaths={[s['deaths'] for s in case['model_slot_results']]}")
    for case in data["out_of_family_ram_six_hit_holdouts"]:
        print(f"{case['case_id']}: user-per-slot="
              f"{case['observed_player_deaths_per_reported_slot']}, "
              f"candidate-per-slot={case['synthetic_six_hit_model_deaths']}")
    reverse = data["reverse_player_fast_to_barbarian_carrier_bars"]
    print(f"Reverse observed bars={reverse['observed_hp_bars']}; "
          f"model-discarded-overkill bars={reverse['model_bars_discard_overkill']}; "
          f"hypothetical-retained bars="
          f"{reverse['counterfactual_bars_if_discarded_overkill_reallocated']}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
