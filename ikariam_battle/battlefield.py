from __future__ import annotations

from dataclasses import dataclass

from .models import Army, Slot, Wave
from .units import UnitRegistry


STANDARD_RENUMBERING = {
    "first": (6, 4, 2, 1, 3, 5, 7), "second": (6, 4, 2, 1, 3, 5, 7),
    "third": (5, 3, 1, 2, 4), "flank-left": (6, 4, 2), "flank-right": (1, 3, 5),
    "balloon": (1, 2), "anti-balloon": (2, 1),
}


@dataclass(frozen=True)
class FormationRule:
    slot_counts: dict[str, int]

    def order(self, line: str) -> tuple[int, ...]:
        count = self.slot_counts[line]
        canonical = STANDARD_RENUMBERING[line]
        # Small fields use the central portion of the canonical physical slots.
        if line in {"first", "second"} and count == 3:
            return (2, 1, 3)
        return canonical[:count]


SMALL_LAND = FormationRule({"first": 3, "second": 3, "third": 3, "flank-left": 3, "flank-right": 3})


def deploy(army: Army, registry: UnitRegistry, rule: FormationRule = SMALL_LAND) -> list[Wave]:
    waves: list[Wave] = []
    occupied: dict[str, set[int]] = {}
    for item in army.units:
        definition = registry.get(item.unit_id)
        line = definition.battlefield_class
        if line not in rule.slot_counts:
            raise ValueError(f"battlefield does not support line {line}")
        remaining = item.quantity
        slots: list[Slot] = []
        used = occupied.setdefault(line, set())
        for number in rule.order(line):
            if number in used or remaining == 0:
                continue
            count = min(remaining, definition.slot_capacity)
            slots.append(Slot(number, item.unit_id, item.wave_id, count, definition.slot_capacity))
            used.add(number)
            remaining -= count
        waves.append(Wave(item, remaining, slots))
    return waves
