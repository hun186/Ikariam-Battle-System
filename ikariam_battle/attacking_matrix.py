from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatrixTrace:
    row_populations: tuple[int, ...]
    target_damage_positions: tuple[int, ...]
    hits_by_damage_position: dict[int, int]

    def physical_vector(self, physical_order: tuple[int, ...]) -> list[int]:
        return [self.hits_by_damage_position.get(position, 0) for position in physical_order]

    def as_dict(self) -> dict:
        return {"row_populations": list(self.row_populations),
                "target_damage_positions": list(self.target_damage_positions),
                "hits_by_damage_position": self.hits_by_damage_position}


def distribute(row_populations: list[int], target_damage_positions: list[int]) -> MatrixTrace:
    """Map one-based Am row numbers to ascending damage positions modulo q."""
    positions = tuple(sorted(target_damage_positions))
    hits = {position: 0 for position in positions}
    if positions:
        for row_number, population in enumerate(row_populations, 1):
            hits[positions[(row_number - 1) % len(positions)]] += population
    return MatrixTrace(tuple(row_populations), positions, hits)


def from_slot_counts(slot_unit_counts: list[int], target_damage_positions: list[int]) -> MatrixTrace:
    rows = max(slot_unit_counts, default=0)
    populations = [sum(count >= row for count in slot_unit_counts) for row in range(1, rows + 1)]
    return distribute(populations, target_damage_positions)
