from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


IKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-IKILL-EXACT-DIVISION-001"
MKILL_RULE_ID = "EXP-SWORDSMAN-FLANK-ODD-COLUMN-PM-RECOUNT-001"


@dataclass(frozen=True)
class SwordsmanKillAdjustment:
    mode: str
    casualties: int
    persistent_damage: int
    discarded_overkill: int
    recovered_overkill: int
    hit_damage: int
    baseline_d_kills: int
    odd_column_count: int
    odd_tail_damage: int
    p_m_recount_per_odd_column: int
    phase_start_damage: int


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
) -> SwordsmanKillAdjustment | None:
    """Column-aware Experimental hypothesis for Swordsman-vs-Swordsman flank.

    This is intentionally a hypothesis rather than an asserted game formula.

    Evidence-backed parts:
    - the reduced Attacking Matrix is column-structured;
    - historical Swordsman tests show all-even non-zero counts per source
      column follow D-kill;
    - the full 40x6 formation has six 7-hit columns against the central four
      target slots and six 6-hit columns against the two outer slots;
    - exact aggregate division historically produced an I-kill case.

    Candidate M-kill path for odd columns in the current two-hit regime:
    1. pair hits inside each reduced column as D-kills;
    2. keep one unpaired tail hit from each odd column in a slot pool;
    3. allow one P/M-style recount per odd column, capped by the smaller of
       (a) the lethal pair's overkill and
       (b) the HP remaining after the first hit;
    4. add phase-start persistent damage (the prior RR result) to the pool;
    5. convert that pool into extra casualties and residual slot damage.

    Accuracy is deliberately *not* converted into a made-up multiplier here.
    The empirical paper specifically lists Accuracy as a possible selector for
    IR / D-kill-column behavior but says the relationship was not solved.
    """
    if (
        initial_units <= 0
        or hit_points <= 0
        or incoming_damage < 0
        or prior_damage < 0
        or not source_column_hits
    ):
        return None

    hits_by_column = tuple(
        int(source_column_hits[key]) for key in sorted(source_column_hits)
    )
    if any(hits < 0 for hits in hits_by_column):
        return None
    total_hits = sum(hits_by_column)
    if total_hits <= 0 or incoming_damage % total_hits:
        return None
    hit_damage = incoming_damage // total_hits

    # Only model the observed two-hit Swordsman regime. One-shot and 3+-hit
    # regimes need separate fixtures/selectors.
    if not (0 < hit_damage < hit_points and 2 * hit_damage >= hit_points):
        return None

    if all(hits % 2 == 0 for hits in hits_by_column):
        return SwordsmanKillAdjustment(
            "d_kill_even_columns",
            baseline_casualties,
            baseline_persistent_damage,
            baseline_overkill_discarded,
            0,
            hit_damage,
            sum(hits // 2 for hits in hits_by_column),
            0,
            0,
            0,
            prior_damage,
        )

    aggregate_damage = prior_damage + incoming_damage
    if prior_damage == 0 and aggregate_damage % hit_points == 0:
        casualties, persistent = divmod(aggregate_damage, hit_points)
        casualties = min(initial_units, casualties)
        if casualties == initial_units:
            persistent = 0
        # I-kill is aggregate damage accounting, not D-overkill recovery.
        return SwordsmanKillAdjustment(
            "i_kill_exact_division",
            casualties,
            persistent,
            0,
            0,
            hit_damage,
            sum(hits // 2 for hits in hits_by_column),
            sum(hits % 2 for hits in hits_by_column),
            0,
            0,
            prior_damage,
        )

    baseline_d_kills = sum(hits // 2 for hits in hits_by_column)
    odd_column_count = sum(hits % 2 for hits in hits_by_column)
    odd_tail_damage = odd_column_count * hit_damage

    remaining_after_first = hit_points - hit_damage
    pair_overkill = max(0, 2 * hit_damage - hit_points)
    p_m_recount_per_odd_column = min(pair_overkill, remaining_after_first)
    recovered_overkill = odd_column_count * p_m_recount_per_odd_column

    pool = prior_damage + odd_tail_damage + recovered_overkill
    extra_kills, persistent_damage = divmod(pool, hit_points)
    casualties = min(initial_units, baseline_d_kills + extra_kills)
    if casualties == initial_units:
        persistent_damage = 0

    # Keep the hypothesis monotone relative to the already-applied generic
    # sequential baseline. Restoring units killed by the generic resolver would
    # require a separate phase-state rewind model.
    if casualties < baseline_casualties:
        return None

    column_pair_overkill = baseline_d_kills * pair_overkill
    discarded_overkill = max(0, column_pair_overkill - recovered_overkill)

    return SwordsmanKillAdjustment(
        "m_kill_odd_column_p_m_recount",
        casualties,
        persistent_damage,
        discarded_overkill,
        recovered_overkill,
        hit_damage,
        baseline_d_kills,
        odd_column_count,
        odd_tail_damage,
        p_m_recount_per_odd_column,
        prior_damage,
    )
