from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .models import Army, Slot, Wave
from .units import UnitRegistry


@dataclass(frozen=True)
class FormationRules:
    metadata: dict
    lines: dict
    unknowns: tuple[str, ...]

    @classmethod
    def load(cls, name: str = "formation-land") -> "FormationRules":
        raw = json.loads(files("ikariam_battle.data.rules").joinpath(f"{name}.json").read_text(encoding="utf-8"))
        return cls(raw["metadata"], raw["lines"], tuple(raw["unknowns"]))


@dataclass(frozen=True)
class FormationPlacement:
    unit_id: str
    wave_id: str
    runtime_line: str
    physical_position: int
    damage_position: int
    quantity: int
    capacity: int


@dataclass(frozen=True)
class FormationPlan:
    placements: tuple[FormationPlacement, ...]
    reserves: dict[tuple[str, str], int]


def plan_initial_formation(army: Army, registry: UnitRegistry, field, rules: FormationRules | None = None) -> FormationPlan:
    """Pure, deterministic placement; formation does not select weapons or targets."""
    rules = rules or FormationRules.load()
    remaining = {(item.unit_id, item.wave_id): item.quantity for item in army.units}
    placements: list[FormationPlacement] = []
    occupied: dict[str, set[int]] = {}

    def place(item, line_name: str) -> None:
        unit = registry.get(item.unit_id)
        geometry = field.lines.get(line_name)
        if geometry is None or unit.role != "combat":
            return
        capacity = geometry.slot_space // unit.size
        used = occupied.setdefault(line_name, set())
        key = (item.unit_id, item.wave_id)
        for damage_position in geometry.damage_priority:
            if not remaining[key] or damage_position in used:
                continue
            quantity = min(remaining[key], capacity)
            placements.append(FormationPlacement(item.unit_id, item.wave_id, line_name,
                geometry.physical_position(damage_position), damage_position, quantity, capacity))
            remaining[key] -= quantity
            used.add(damage_position)

    # The first line is planned globally: heavy before light. A partial heavy
    # batch owns its slot; a fallback class is never mixed into that slot.
    first = rules.lines["first"]
    for semantic_class in first["class_precedence"]:
        for item in army.units:
            if registry.get(item.unit_id).semantic_class == semantic_class:
                place(item, "first")

    # Only after front requirements have consumed light infantry do remaining
    # units enter their native lines. This gives front-before-flank precedence.
    for line_name in field.lines:
        if line_name == "first":
            continue
        for item in army.units:
            if registry.get(item.unit_id).native_line == line_name:
                place(item, line_name)
    return FormationPlan(tuple(placements), remaining)


def build_initial_formation(army: Army, registry: UnitRegistry, field, rules: FormationRules | None = None) -> list[Wave]:
    plan = plan_initial_formation(army, registry, field, rules)
    by_wave: dict[tuple[str, str], list[Slot]] = {}
    for placement in plan.placements:
        key = (placement.unit_id, placement.wave_id)
        by_wave.setdefault(key, []).append(Slot(
            f"{placement.runtime_line}-{placement.damage_position}", placement.runtime_line,
            placement.physical_position, placement.damage_position, placement.unit_id,
            placement.wave_id, placement.quantity, placement.capacity))
    waves = []
    for item in army.units:
        unit = registry.get(item.unit_id)
        if unit.role == "support":
            waves.append(Wave(item, 0, [], 0, None, item.quantity))
            continue
        ammo = None if unit.primary_weapon.ammunition is None else item.quantity * unit.primary_weapon.ammunition
        waves.append(Wave(item, plan.reserves[(item.unit_id, item.wave_id)],
                          by_wave.get((item.unit_id, item.wave_id), []), 0, ammo, 0, ammo))
    return waves
