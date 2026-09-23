from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatrixTrace:
    rows: int
    columns: tuple[int, ...]
    target_slots: tuple[int, ...]
    hits: dict[int, int]

    def as_dict(self) -> dict:
        return {"rows": self.rows, "columns": list(self.columns), "target_slots": list(self.target_slots), "hits": self.hits}


def distribute(row_counts: list[int], target_slots: list[int]) -> MatrixTrace:
    """Apply PDF §2.1 row-index modulo target slot count.

    ``row_counts[i]`` is the number of firing columns populated in one-based
    matrix row ``i + 1``.  Physical target slots are supplied in damage order.
    """
    if not target_slots:
        return MatrixTrace(len(row_counts), tuple(row_counts), (), {})
    hits = {slot: 0 for slot in target_slots}
    q = len(target_slots)
    for index, firing_units in enumerate(row_counts, 1):
        hits[target_slots[(index - 1) % q]] += firing_units
    return MatrixTrace(len(row_counts), tuple(row_counts), tuple(target_slots), hits)


def from_slots(slot_unit_counts: list[int], target_slots: list[int]) -> MatrixTrace:
    rows = max(slot_unit_counts, default=0)
    return distribute([sum(count >= row for count in slot_unit_counts) for row in range(1, rows + 1)], target_slots)
