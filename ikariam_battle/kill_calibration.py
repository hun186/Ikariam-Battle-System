from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


MKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-MKILL-OVERKILL-THIRD-001"
IKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-IKILL-DIVISIBLE-001"
OVERKILL_RECOVERY_NUMERATOR = 1
OVERKILL_RECOVERY_DENOMINATOR = 3


@dataclass(frozen=True)
class KillAdjustment:
    mode: str
    casualties: int
    persistent_damage: int
    extra_casualties: int
    recovered_overkill: int
    discarded_overkill: int


def swordsman_flank_kill_adjustment(
    *,
    initial_units: int,
    hit_points: int,
    incoming_damage: int,
    prior_damage: int,
    baseline_casualties: int,
    baseline_persistent_damage: int,
    baseline_overkill_discarded: int,
    source_column_hits: Mapping[int, int],
) -> KillAdjustment | None:
    """Apply a bounded empirical Swordsman-flank kill-selector hypothesis.

    Evidence-backed selector pieces:
    - the empirical paper found full Swordsman flank target slots whose reduced
      AM columns all contain an even number of non-zero entries resolve as
      D-kill;
    - when the odd-column aggregate damage divides target HP exactly, the paper
      identifies I-kill in the historical full-formation case.

    New current-version hypothesis:
    - for six odd Swordsman source columns where aggregate damage is not exactly
      divisible, start from the observed D-kill baseline and recover one third
      of discarded overkill into a slot-level redistribution pool;
    - that recovered pool can cause additional casualties and leaves its
      remainder as persistent slot damage.

    The one-third factor is a calibration hypothesis, not an official rule. It
    is selected because the current 6x40 Swordsman observation constrains the
    strong-side recovery to ~33.0..34.7% and exactly 1/3 simultaneously predicts
    the weak-side 99%-display-compatible residual. Accuracy is deliberately not
    inserted into this formula: Swordsman Accuracy is constant in the available
    observation, so its possible higher-level selector role is not identifiable.
    """
    if (
        initial_units <= 0
        or hit_points <= 0
        or incoming_damage < 0
        or prior_damage < 0
        or baseline_casualties < 0
        or baseline_persistent_damage < 0
        or baseline_overkill_discarded < 0
    ):
        raise ValueError("invalid kill-adjustment state")

    counts = tuple(source_column_hits[position] for position in sorted(source_column_hits))
    if len(counts) != 6 or any(count <= 0 for count in counts):
        return None

    # Paper-backed D selector: all reduced-AM columns have even non-zero count.
    if all(count % 2 == 0 for count in counts):
        return KillAdjustment(
            "d_kill_even_columns",
            baseline_casualties,
            baseline_persistent_damage,
            0,
            0,
            baseline_overkill_discarded,
        )

    # Do not generalize mixed odd/even reduced matrices yet.
    if not all(count % 2 == 1 for count in counts):
        return None

    total_pool = prior_damage + incoming_damage
    if total_pool % hit_points == 0:
        casualties = min(initial_units, total_pool // hit_points)
        persistent = total_pool - casualties * hit_points
        return KillAdjustment(
            "i_kill_exact_division",
            casualties,
            persistent,
            casualties - baseline_casualties,
            max(0, total_pool - (
                baseline_casualties * hit_points + baseline_persistent_damage
            )),
            0,
        )

    recovered = (
        baseline_overkill_discarded * OVERKILL_RECOVERY_NUMERATOR
        // OVERKILL_RECOVERY_DENOMINATOR
    )
    redistributed = baseline_persistent_damage + recovered
    survivors_after_baseline = max(0, initial_units - baseline_casualties)
    extra = min(survivors_after_baseline, redistributed // hit_points)
    persistent = redistributed - extra * hit_points
    casualties = baseline_casualties + extra

    return KillAdjustment(
        "m_kill_overkill_third",
        casualties,
        persistent,
        extra,
        recovered,
        baseline_overkill_discarded - recovered,
    )
