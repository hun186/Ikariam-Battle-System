"""Bounded EXPERIMENTAL naval focus allocation; not an official kill rule.

A two-part research-only model with carefully constrained callers:
* deckwrecker six shots vs six fresh Rams: concentrate a rational fraction
  of the target-slot gross damage budget on one hull, spread the remainder.
  Real game individual shot splitting is UNKNOWN. Here the fraction belongs
  to a slot-level *damage pool*, NOT a per-projectile hit/miss probability.
* reciprocal Ram six shots vs Deckwrecker: retain D-kill discarded overkill
  as surviving damage in the historically reported ATT20/Forge5 subset.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


NAVAL_RAM_SHARE_RULE_ID = "EXP-NAVAL-RAM-FOCUS-SHARE-001"
NAVAL_DECK_OVERKILL_RULE_ID = "EXP-NAVAL-DECK-OVERKILL-RETAIN-001"


@dataclass(frozen=True)
class NavalFocusAllocation:
    survivors_damage: tuple[int, ...]
    deaths: int
    discarded_overkill: int
    initial_focus_damage: int
    share: Fraction


def empirical_focus_fraction(accuracy: int, units: int) -> Fraction:
    """Candidate F(A,N), never an alleged Gameforge Accuracy definition."""
    if not 0 <= accuracy <= 100 or units <= 0:
        raise ValueError("accuracy must be 0..100 and units positive")
    scaled = Fraction(max(0, min(accuracy - 60, 60)), 60)
    return Fraction(1, units) + (1 - Fraction(1, units)) * scaled


def _even(total: int, n: int) -> tuple[int, ...]:
    if n == 0:
        return ()
    base, remainder = divmod(total, n)
    return tuple([base + 1] * remainder + [base] * (n - remainder))


def six_ram_hull_share_candidate(
    *,
    initial_units: int, hp: int, shots: int, hit_damage: int, accuracy: int,
) -> NavalFocusAllocation | None:
    """Slot-budget witness for six fresh hulls, six effective primary hits.

    The focal damage and residual are *pooled*: fractional values are floored
    to whole HP, not split into actual shots. No arbitrary kill-count lookup.
    Only return allocations with 0/1 focal deaths and no residual ship dying.
    """
    if initial_units != 6 or shots != 6 or hp <= 0 or hit_damage <= 0:
        return None
    share = empirical_focus_fraction(accuracy, initial_units)
    total = shots * hit_damage
    focal = (total * share.numerator) // share.denominator
    other = total - focal
    if focal >= hp:
        damages = _even(other, initial_units - 1)
        if any(d >= hp for d in damages):
            return None
        return NavalFocusAllocation(
            survivors_damage=damages, deaths=1,
            discarded_overkill=focal-hp, initial_focus_damage=focal,
            share=share,
        )
    damages = (focal,) + _even(other, initial_units - 1)
    if any(d >= hp for d in damages):
        return None
    return NavalFocusAllocation(
        survivors_damage=tuple(sorted(damages, reverse=True)), deaths=0,
        discarded_overkill=0, initial_focus_damage=focal, share=share,
    )


def recover_baseline_dkill_overkill(
    surviving_damage: list[int], overkill: int, hp: int
) -> tuple[int, ...] | None:
    """Bounded exploratory P/IR: spread lost D-overkill into living hull HP."""
    if not surviving_damage or overkill <= 0 or hp <= 0:
        return None
    additions = _even(overkill, len(surviving_damage))
    new = sorted((d + a for d, a in zip(sorted(surviving_damage, reverse=True), additions)),
                 reverse=True)
    if any(x >= hp or x < 0 for x in new):
        return None
    return tuple(new)
