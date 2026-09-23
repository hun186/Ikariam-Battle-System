from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .models import Army, ScenarioError, Slot, Wave
from .units import UnitRegistry


@dataclass(frozen=True)
class LineGeometry:
    name: str
    physical_order: tuple[int, ...]  # left-to-right damage-position labels
    capacity: int

    @property
    def damage_priority(self) -> tuple[int, ...]:
        return tuple(sorted(self.physical_order))

    def physical_position(self, damage_position: int) -> int:
        return self.physical_order.index(damage_position) + 1


@dataclass(frozen=True)
class Battlefield:
    id: str
    domain: str
    lines: dict[str, LineGeometry]
    provenance: str


def _mechanics_physical() -> dict[str, tuple[int, ...]]:
    raw = json.loads(files("ikariam_battle.data.mechanics").joinpath("battle-system-paper-2020.json").read_text())
    return {key: tuple(value) for key, value in raw["physical_order"].items()}


_PHYSICAL = _mechanics_physical()
# Only first-line three-slot geometry is directly discussed by the paper. Other
# small-field line counts/capacities remain calibration geometry, not mechanics truth.
SMALL_LAND = Battlefield("small-land", "land", {
    "first": LineGeometry("first", (2, 1, 3), 30),
    "second": LineGeometry("second", (2, 1, 3), 14),
    "third": LineGeometry("third", (3, 1, 2), 5),
    "flank": LineGeometry("flank", (2, 1, 3), 40),
    "anti-balloon": LineGeometry("anti-balloon", (2, 1), 30),
    "balloon": LineGeometry("balloon", (1, 2), 15),
}, "EMPIRICAL_PAPER_FIRST_LINE_PLUS_REVIEW_SUPPLIED_CALIBRATION_GEOMETRY")


def battlefield(name: str) -> Battlefield:
    if name == "small-land": return SMALL_LAND
    raise ScenarioError("small-naval is reserved but its geometry is unsupported")


def deploy(army: Army, registry: UnitRegistry, field: Battlefield) -> list[Wave]:
    waves: list[Wave] = []
    occupied: dict[str, set[int]] = {}
    for item in army.units:
        unit = registry.get(item.unit_id)
        if unit.domain != field.domain:
            raise ScenarioError(f"{unit.id} is {unit.domain} and cannot enter {field.id}")
        if unit.role == "support":
            waves.append(Wave(item, item.quantity, [], 0, None))
            continue
        if not unit.numerically_supported:
            raise ScenarioError(f"{unit.id} has unverified numerical fields and cannot be simulated")
        line_name = "flank" if unit.battlefield_class.startswith("flank") else unit.battlefield_class
        if line_name not in field.lines:
            raise ScenarioError(f"{field.id} does not support line {line_name}")
        geometry = field.lines[line_name]
        remaining, slots = item.quantity, []
        used = occupied.setdefault(line_name, set())
        # Deployment follows damage priority, never physical left-to-right order.
        for damage_position in geometry.damage_priority:
            if damage_position in used or remaining == 0: continue
            count = min(remaining, geometry.capacity)
            slots.append(Slot(f"{line_name}-{damage_position}", line_name,
                              geometry.physical_position(damage_position), damage_position,
                              item.unit_id, item.wave_id, count, geometry.capacity))
            used.add(damage_position); remaining -= count
        ammo = unit.primary_weapon.ammunition
        waves.append(Wave(item, remaining, slots, 0, ammo))
    return waves
