from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .models import Army, ScenarioError, Wave
from .units import UnitRegistry


@dataclass(frozen=True)
class LineGeometry:
    name: str
    physical_order: tuple[int, ...]  # left-to-right damage-position labels
    slot_space: int

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
# Town Hall 1–4 geometry is current community-reference data; damage-position
# labels remain sourced from the empirical mechanics profile.
LAND_MINI = Battlefield("land-mini", "land", {
    "first": LineGeometry("first", (2, 1, 3), 30),
    "second": LineGeometry("second", (2, 1, 3), 30),
    "third": LineGeometry("third", (1,), 30),
    "anti-balloon": LineGeometry("anti-balloon", (1,), 10),
    "balloon": LineGeometry("balloon", (1,), 10),
}, "REVIEWER_WEB_VERIFIED_COMMUNITY_REFERENCE_TOWN_HALL_1_TO_4")


def battlefield(name: str) -> Battlefield:
    if name == "land-mini": return LAND_MINI
    raise ScenarioError(f"{name} is reserved but its geometry is unsupported")


def deploy(army: Army, registry: UnitRegistry, field: Battlefield,
           formation_profile: str = "formation-land") -> list[Wave]:
    from .formation import FormationRules, build_initial_formation
    for item in army.units:
        unit = registry.get(item.unit_id)
        if unit.domain != field.domain:
            raise ScenarioError(f"{unit.id} is {unit.domain} and cannot enter {field.id}")
        if unit.role != "support" and not unit.numerically_supported:
            raise ScenarioError(f"{unit.id} has unverified numerical fields and cannot be simulated")
    return build_initial_formation(army, registry, field, FormationRules.load(formation_profile))
