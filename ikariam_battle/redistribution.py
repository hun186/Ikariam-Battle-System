from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class SlotShare:
    damage_position: int
    deployed_units: int


def reserve_redistribution(total_damage: int, alive_wave_units: int, deployed: list[SlotShare]) -> tuple[dict[int, int], int]:
    """Apply ds=D/N*s; allocate integer remainder by damage position."""
    if total_damage < 0 or alive_wave_units <= 0:
        raise ValueError("damage must be non-negative and alive units positive")
    ordered = sorted(deployed, key=lambda share: share.damage_position)
    exact = {s.damage_position: Fraction(total_damage * s.deployed_units, alive_wave_units) for s in ordered}
    allocated = {position: int(value) for position, value in exact.items()}
    deployed_target = min(total_damage, round(sum(exact.values())))
    index = 0
    while sum(allocated.values()) < deployed_target and ordered:
        allocated[ordered[index % len(ordered)].damage_position] += 1
        index += 1
    reserve_damage = total_damage - sum(allocated.values())
    assert sum(allocated.values()) + reserve_damage == total_damage
    return allocated, reserve_damage
