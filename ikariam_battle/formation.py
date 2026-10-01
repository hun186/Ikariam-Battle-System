from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .models import Army, ScenarioError, Slot, Wave
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


def _first_line_contract(rules: FormationRules) -> tuple[tuple[str, ...], tuple[str, ...], frozenset[str]]:
    first = rules.lines["first"]
    eligible = tuple(first["eligible_semantic_classes"])
    precedence = tuple(first["class_precedence"])
    fallback = frozenset(first["fallback_semantic_classes"])
    if len(set(precedence)) != len(precedence) or set(precedence) != set(eligible):
        raise ScenarioError("first-line class_precedence must contain each eligible semantic class exactly once")
    if not fallback <= set(eligible):
        raise ScenarioError("first-line fallback classes must be eligible semantic classes")
    return eligible, precedence, fallback


def eligible_runtime_lines(unit, rules: FormationRules, field) -> tuple[str, ...]:
    """Return runtime lines this combat unit may occupy under formation rules."""
    if unit.role != "combat":
        return ()
    eligible, _, fallback = _first_line_contract(rules)
    result: list[str] = []
    if ("first" in field.lines and unit.semantic_class in eligible
            and (unit.native_line == "first" or unit.semantic_class in fallback)):
        result.append("first")
    for line_name in field.lines:
        if line_name == "first":
            continue
        native_lines = frozenset(rules.lines[line_name].get("eligible_native_lines", ()))
        if unit.native_line in native_lines:
            result.append(line_name)
    return tuple(result)


def _formation_ordered_units(army: Army) -> tuple:
    """Canonical unit-state order for dict and directly-constructed typed armies."""
    return tuple(sorted(army.units, key=lambda item: item.formation_order_key))


def plan_initial_formation(army: Army, registry: UnitRegistry, field, rules: FormationRules | None = None) -> FormationPlan:
    """Pure, deterministic placement; formation does not select weapons or targets."""
    rules = rules or FormationRules.load()
    ordered_units = _formation_ordered_units(army)
    remaining = {(item.unit_id, item.wave_id): item.quantity for item in ordered_units}
    placements: list[FormationPlacement] = []
    occupied: dict[str, set[int]] = {}

    def placement_order(line_name: str):
        line_rules = rules.lines[line_name]
        if line_rules.get("deployment_order_authority") != "battlefield_geometry.damage_priority":
            raise ScenarioError(f"unsupported deployment order authority for {line_name}")
        return field.lines[line_name].damage_priority

    def place(item, line_name: str) -> None:
        unit = registry.get(item.unit_id)
        geometry = field.lines.get(line_name)
        if geometry is None or unit.role != "combat":
            return
        capacity = geometry.slot_space // unit.size
        used = occupied.setdefault(line_name, set())
        key = (item.unit_id, item.wave_id)
        for damage_position in placement_order(line_name):
            if not remaining[key] or damage_position in used:
                continue
            quantity = min(remaining[key], capacity)
            placements.append(FormationPlacement(item.unit_id, item.wave_id, line_name,
                geometry.physical_position(damage_position), damage_position, quantity, capacity))
            remaining[key] -= quantity
            used.add(damage_position)

    # The first line is planned globally: heavy before light. A partial heavy
    # batch owns its slot; a fallback class is never mixed into that slot.
    _, precedence, _ = _first_line_contract(rules)
    for semantic_class in precedence:
        for item in ordered_units:
            unit = registry.get(item.unit_id)
            if unit.semantic_class == semantic_class and "first" in eligible_runtime_lines(unit, rules, field):
                place(item, "first")

    # Only after front requirements have consumed light infantry do remaining
    # units enter their native lines. This gives front-before-flank precedence.
    for line_name in field.lines:
        if line_name == "first":
            continue
        for item in ordered_units:
            if line_name in eligible_runtime_lines(registry.get(item.unit_id), rules, field):
                place(item, line_name)
    return FormationPlan(tuple(placements), remaining)


def build_initial_formation(army: Army, registry: UnitRegistry, field, rules: FormationRules | None = None) -> list[Wave]:
    ordered_units = _formation_ordered_units(army)
    plan = plan_initial_formation(army, registry, field, rules)
    by_wave: dict[tuple[str, str], list[Slot]] = {}
    for placement in plan.placements:
        key = (placement.unit_id, placement.wave_id)
        by_wave.setdefault(key, []).append(Slot(
            f"{placement.runtime_line}-{placement.damage_position}", placement.runtime_line,
            placement.physical_position, placement.damage_position, placement.unit_id,
            placement.wave_id, placement.quantity, placement.capacity))
    waves = []
    for item in ordered_units:
        unit = registry.get(item.unit_id)
        if unit.role == "support":
            waves.append(Wave(item, 0, [], 0, None, item.quantity))
            continue
        ammo = None if unit.primary_weapon.ammunition is None else item.quantity * unit.primary_weapon.ammunition
        waves.append(Wave(item, plan.reserves[(item.unit_id, item.wave_id)],
                          by_wave.get((item.unit_id, item.wave_id), []), 0, ammo, 0, ammo))
    return waves
