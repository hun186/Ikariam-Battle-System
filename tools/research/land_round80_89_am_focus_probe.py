"""LAND (not NAVAL) fire-address and target shrinkage research, read-only.

Compare the main engine's AM row-addressing histogram against user-confirmed
visible round deaths. This is NOT a kill predictor: shots != casualties.
Separate unsupported 7x12 full source-fire and all one-kill-per-shot controls
from user observations. Other sources (e.g. wall) remain unverified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.engine import _shot_rows

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json"


def model_am_addressed_shots_by_physical_slot(
    physical_slots: list[int], source_firing_counts: list[int]
) -> dict[int, int]:
    """Current implementation: AM target index=(source row-1)%frozen target count."""
    geo = LAND_BATTLEFIELDS["land-max"].lines["first"]
    valid = {i + 1 for i in range(len(geo.physical_order))}
    if not physical_slots or len(set(physical_slots)) != len(physical_slots):
        raise ValueError("Need nonempty distinct target physical positions")
    if not set(physical_slots) <= valid or any(count < 0 for count in source_firing_counts):
        raise ValueError("Bad geometry or firing count")
    # Damage addresses sort by current geometry damage positions, not physical L/R.
    target_addresses = sorted(
        (geo.physical_order[physical - 1], physical)
        for physical in physical_slots
    )
    histogram = {physical: 0 for physical in sorted(physical_slots)}
    for row in _shot_rows(source_firing_counts):
        _, physical = target_addresses[(row - 1) % len(target_addresses)]
        histogram[physical] += 1
    return histogram


def build_report() -> dict:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    controls = [12] * 7
    cases = []
    for game in source["observations"]:
        occupied = [
            i + 1 for i, deaths in enumerate(
                game["attacker_barbarian_main_line_deaths_left_to_right"]
            ) if deaths is not None
        ]
        predicted = model_am_addressed_shots_by_physical_slot(occupied, controls)
        loss_by_position = {
            i + 1: game["attacker_barbarian_main_line_deaths_left_to_right"][i]
            for i in range(7)
            if i + 1 in occupied
        }
        residual = {
            physical: loss_by_position[physical] - predicted[physical]
            for physical in occupied
        }
        cases.append({
            "round": game["round"],
            "user_verified_visible_deaths_by_physical_position": loss_by_position,
            "user_verified_total_deaths": game[
                "attacker_barbarian_main_line_total_round_deaths"
            ],
            "modeled_full_fire_source_7x12_unverified": True,
            "modeled_target_first_line_occupied_physical_positions": occupied,
            "modeled_AM_addressed_shots_by_physical_position": predicted,
            "modeled_total_shots": sum(predicted.values()),
            "observed_deaths_minus_modeled_AM_addressed_shots_NOT_EXTRA_ATTACK_COUNT": residual,
            "observed_total_deaths_minus_84_shots_NOT_PROOF_OF_OTHER_WEAPON": (
                sum(loss_by_position.values()) - sum(predicted.values())
            ),
            "barrier_context": game["barrier_context_image_inference"],
            "source_provenance_warning": (
                "AM is a controlled current-engine comparison; each shot is not "
                "necessarily one kill and the original complete attacking "
                "sources, actual ammo, wall attack and turn-phase chronology "
                "are unverified. Do not interpret differences as proven "
                "extra wall hits or accuracy events."
            ),
        })
    return {
        "schema_version": 1,
        "evidence_class": "USER_VERIFIED_ROUND_DEATHS_VS_CONDITIONAL_MODEL_AM_ADDRESSING",
        "source": source["source"],
        "controls": {
            "domain": "LAND",
            "assumed_shooter": "player_sulphur_carabineer_second_line",
            "assumed_seven_source_cells_of_twelve": True,
            "assumed_one_current_weapon_attack_per_source_unit": True,
            "source_ammunition_sufficiency_unverified": True,
            "other_sources_and_wall_attack_unverified": True,
            "model": "_shot_rows() and target_index=(row_number-1)%active_frozen_address_book_count",
            "comparison_is_hit_addresses_vs_casualties_not_equivalent": True,
            "round80_open_field_not_identical_to_wall_round81_89": True,
        },
        "game_round_comparisons": cases,
        "candidate_explanations_not_established": [
            {
                "name": "target re-addressing as active positions shrink",
                "reason": "Model predicts 14 shots/slot for six targets and 21 shots/slot for four targets from unchanged 84 hypothetical source shots; real game shows nonuniform death profiles at 91 total",
                "status": "unconfirmed",
            },
            {
                "name": "seven additional damaging events from seven wall sections or other source",
                "reason": "Observed 91 deaths is exactly 84+7 at rounds88 and89; image shows seven defended wall sections but their attack behavior and per-attack kill budget not independently verified",
                "status": "arithmetic_coincidence_not_proof",
            },
            {
                "name": "different hit-to-kill rates across target unit types / group HP",
                "reason": "Round81-83 main slot deaths deviate from AM address counts by +1 in six physical positions and -6 in central different-unit position; hit count and kills cannot be equated",
                "status": "plausible_without_verified_individual_shots",
            },
        ],
    }


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    result = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for case in result["game_round_comparisons"]:
        if case["round"] in (81, 83, 84, 87, 88, 89):
            print(
                f"round={case['round']} "
                f"addresses={list(case['modeled_AM_addressed_shots_by_physical_position'].values())} "
                f"user_deaths={list(case['user_verified_visible_deaths_by_physical_position'].values())} "
                f"casualty_minus_address={list(case['observed_deaths_minus_modeled_AM_addressed_shots_NOT_EXTRA_ATTACK_COUNT'].values())}"
            )
    print("CAUTION: addresses are model shots, not observed Gameforge kill events")


if __name__ == "__main__":
    main()
