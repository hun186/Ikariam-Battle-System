from __future__ import annotations

from dataclasses import dataclass


EXPERIMENTAL_ACCURACY_MODEL_ID = "EXP-ACCURACY-CONCENTRATION-001"
NAVAL_FAST_CARRIER_FOCUS_ID = "EXP-NAVAL-FAST-CARRIER-74PCT-001"
NAVAL_FAST_CARRIER_FOCUS_THRESHOLD = 74


@dataclass(frozen=True)
class AccuracyDecision:
    target_index: int
    mode: str
    accuracy: int
    focus_remaining_hp_percent: float | None
    focus_threshold_percent: float | None = None


def select_accuracy_target(
    damage_queue: list[int],
    unit_hp: int,
    hit_damage: int,
    accuracy: int,
    *,
    experimental_focus_threshold: int | None = None,
) -> AccuracyDecision:
    """Select one individual target inside an already-addressed slot.

    Experimental concentration-v1 hypothesis:
    - Accuracy is not a Bernoulli hit/miss chance.
    - If one hit can kill a full-health target, do not manufacture misses.
    - Otherwise, keep spreading damage to the healthiest survivor until the
      most-damaged survivor's remaining HP percentage is <= weapon Accuracy.
      Once that threshold is crossed, focus the most-damaged survivor.

    `experimental_focus_threshold` supports explicitly guarded, fixture-fitted
    source/target cases. It is NOT the official weapon Accuracy and does not
    change the reported weapon Accuracy. The caller must record the alternate
    experiment ID whenever it supplies this override.

    The function is deterministic and intentionally limited to within-slot
    individual selection. It does not alter Attacking Matrix slot addressing,
    formation target priority, damage amount, ammunition, or firing chronology.
    """
    if not damage_queue:
        raise ValueError("damage_queue must contain at least one survivor")
    if unit_hp <= 0:
        raise ValueError("unit_hp must be positive")
    if hit_damage < 0:
        raise ValueError("hit_damage must be non-negative")
    if not 0 <= accuracy <= 100:
        raise ValueError("accuracy must be 0..100")

    if experimental_focus_threshold is not None and not 0 <= experimental_focus_threshold <= 100:
        raise ValueError("experimental_focus_threshold must be 0..100")
    threshold = accuracy if experimental_focus_threshold is None else experimental_focus_threshold

    focus_damage = max(damage_queue)
    focus_index = damage_queue.index(focus_damage)

    # User-observed one-shot battles strongly argue against treating Accuracy
    # as an independent miss chance. Preserve one casualty-capable hit per shot.
    if hit_damage >= unit_hp:
        remaining_percent = max(0.0, (unit_hp - focus_damage) * 100.0 / unit_hp)
        return AccuracyDecision(
            focus_index, "one_shot_bypass", accuracy, remaining_percent, threshold
        )

    if focus_damage > 0:
        remaining_numerator = unit_hp - focus_damage
        remaining_percent = max(0.0, remaining_numerator * 100.0 / unit_hp)
        if remaining_numerator * 100 <= unit_hp * threshold:
            return AccuracyDecision(
                focus_index,
                "focus_below_accuracy_threshold",
                accuracy,
                remaining_percent,
                threshold,
            )
    else:
        remaining_percent = None

    # Prefer a fresh target; after every survivor has damage this means the
    # healthiest survivor. Choose the last equal candidate deterministically.
    least_damage = min(damage_queue)
    spread_index = max(
        index for index, damage in enumerate(damage_queue) if damage == least_damage
    )
    return AccuracyDecision(
        spread_index,
        "spread_above_accuracy_threshold",
        accuracy,
        remaining_percent,
        threshold,
    )
