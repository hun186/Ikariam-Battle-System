from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from types import MappingProxyType
from typing import Mapping

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
    lines: Mapping[str, LineGeometry]
    provenance: str


def _mechanics_physical() -> dict[str, tuple[int, ...]]:
    raw = json.loads(files("ikariam_battle.data.mechanics").joinpath("battle-system-paper-2020.json").read_text())
    return {key: tuple(value) for key, value in raw["physical_order"].items()}


_PHYSICAL = _mechanics_physical()

# Slot counts and spaces are reviewer-web-verified community reference data
# hosted by Gameforge. Damage-position labels are centered subsets of the
# EMPIRICAL_PAPER layouts loaded above; the sources intentionally remain
# distinct rather than presenting community geometry as official source code.
_LAND_SPECS = {
    "land-mini": ("Land mini / Town Hall 1–4", {
        "first": ((2, 1, 3), 30), "second": ((2, 1, 3), 30),
        "third": ((1,), 30), "anti-balloon": ((1,), 10), "balloon": ((1,), 10)}),
    "land-small": ("Land small / Town Hall 5–9", {
        "first": ((4, 2, 1, 3, 5), 30), "second": ((4, 2, 1, 3, 5), 30),
        "flank": ((2, 1), 30), "third": ((1, 2), 30),
        "anti-balloon": ((1,), 20), "balloon": ((1,), 20)}),
    "land-medium": ("Land medium / Town Hall 10–16", {
        "first": (_PHYSICAL["first"], 30), "second": (_PHYSICAL["second"], 30),
        "flank": ((4, 2, 1, 3), 30), "third": ((3, 1, 2), 30),
        "anti-balloon": ((1,), 30), "balloon": ((1,), 30)}),
    "land-large": ("Land large / Town Hall 17–24", {
        "first": (_PHYSICAL["first"], 40), "second": (_PHYSICAL["second"], 40),
        "flank": ((6, 4, 2, 1, 3, 5), 30), "third": ((3, 1, 2, 4), 30),
        "anti-balloon": (_PHYSICAL["anti-balloon"], 20),
        "balloon": (_PHYSICAL["balloon"], 20)}),
    "land-max": ("Land max / Town Hall 25+", {
        "first": (_PHYSICAL["first"], 50), "second": (_PHYSICAL["second"], 50),
        "flank": ((6, 4, 2, 1, 3, 5), 40), "third": (_PHYSICAL["third"], 30),
        "anti-balloon": (_PHYSICAL["anti-balloon"], 30),
        "balloon": (_PHYSICAL["balloon"], 30)}),
}


def _land_battlefield(field_id: str, lines: dict[str, tuple[tuple[int, ...], int]]) -> Battlefield:
    geometry = {name: LineGeometry(name, physical_order, slot_space)
                for name, (physical_order, slot_space) in lines.items()}
    return Battlefield(field_id, "land", MappingProxyType(geometry),
                       "REVIEWER_WEB_VERIFIED_COMMUNITY_GEOMETRY_WITH_EMPIRICAL_PAPER_POSITIONS")


LAND_BATTLEFIELDS: Mapping[str, Battlefield] = MappingProxyType({
    field_id: _land_battlefield(field_id, lines)
    for field_id, (_, lines) in _LAND_SPECS.items()
})
LAND_MINI = LAND_BATTLEFIELDS["land-mini"]

# 2026 Gameforge-hosted community tutorial, max naval battlefield:
# 35 Steam Rams / 84 Fire Ships across 7 First slots -> 25 space each;
# 36 Ram Ships across 6 Flank slots -> 18 space each;
# 42 Mortar / 56 Catapult / 84 Ballista across 7 Second slots -> 24 space;
# 25 Diving Boats / 15 Rocket Ships across 5 Third slots -> 15 space;
# 6 Balloon Carriers / 30 Paddle Speedboats across 2 Air slots -> 15 space.
# Damage-position labels reuse the empirical AM geometry; only the max naval
# field is executable until smaller naval geometries are independently verified.
_NAVAL_SPECS = {
    "naval-max": ("Naval max / current community geometry", {
        "first": (_PHYSICAL["first"], 25),
        "second": (_PHYSICAL["second"], 24),
        "third": (_PHYSICAL["third"], 15),
        "flank": ((6, 4, 2, 1, 3, 5), 18),
        "anti-balloon": (_PHYSICAL["anti-balloon"], 15),
        "balloon": (_PHYSICAL["balloon"], 15),
    }),
}


def _naval_battlefield(
    field_id: str, lines: dict[str, tuple[tuple[int, ...], int]]
) -> Battlefield:
    geometry = {
        name: LineGeometry(name, physical_order, slot_space)
        for name, (physical_order, slot_space) in lines.items()
    }
    return Battlefield(
        field_id,
        "naval",
        MappingProxyType(geometry),
        "GAMEFORGE_FORUM_2026_MAX_NAVAL_GEOMETRY_WITH_EMPIRICAL_AM_POSITIONS",
    )


NAVAL_BATTLEFIELDS: Mapping[str, Battlefield] = MappingProxyType({
    field_id: _naval_battlefield(field_id, lines)
    for field_id, (_, lines) in _NAVAL_SPECS.items()
})


def battlefield_metadata() -> list[dict[str, object]]:
    """Return canonical public metadata grouped by battle domain."""
    result = [
        {
            "id": field_id,
            "display_name": display_name,
            "domain": "land",
            "supported": True,
            "lines": {
                name: {
                    "physical_order": list(line.physical_order),
                    "slot_space": line.slot_space,
                }
                for name, line in LAND_BATTLEFIELDS[field_id].lines.items()
            },
        }
        for field_id, (display_name, _) in _LAND_SPECS.items()
    ]
    result.extend(
        {
            "id": field_id,
            "display_name": display_name,
            "domain": "naval",
            "supported": True,
            "lines": {
                name: {
                    "physical_order": list(line.physical_order),
                    "slot_space": line.slot_space,
                }
                for name, line in NAVAL_BATTLEFIELDS[field_id].lines.items()
            },
        }
        for field_id, (display_name, _) in _NAVAL_SPECS.items()
    )
    result.append({
        "id": "naval-mini",
        "display_name": "Naval mini / geometry pending",
        "domain": "naval",
        "supported": False,
        "lines": {},
    })
    return result


def battlefield(name: str) -> Battlefield:
    if name in LAND_BATTLEFIELDS:
        return LAND_BATTLEFIELDS[name]
    if name in NAVAL_BATTLEFIELDS:
        return NAVAL_BATTLEFIELDS[name]
    raise ScenarioError(f"{name} is reserved but its geometry is unsupported")


def deploy(army: Army, registry: UnitRegistry, field: Battlefield,
           formation_profile: str = "formation-land") -> list[Wave]:
    from .formation import FormationRules, build_initial_formation
    for item in army.units:
        unit = registry.get(item.unit_id)
        if unit.army_kind != army.army_kind:
            raise ScenarioError(
                f"{unit.id} belongs to the {unit.army_kind} army package, "
                f"not {army.army_kind}"
            )
        if unit.domain != field.domain:
            raise ScenarioError(f"{unit.id} is {unit.domain} and cannot enter {field.id}")
        if unit.role != "support" and not unit.numerically_supported:
            raise ScenarioError(f"{unit.id} has unverified numerical fields and cannot be simulated")
    return build_initial_formation(army, registry, field, FormationRules.load(formation_profile))
