from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from typing import Any

from .models import ScenarioError


@dataclass(frozen=True)
class Weapon:
    id: str
    damage: int | None
    ammunition: int | None
    trigger: str
    accuracy: int | None
    provenance: dict[str, Any]


@dataclass(frozen=True)
class UnitDefinition:
    id: str
    display_name: str
    domain: str
    role: str
    support_effect: str | None
    battlefield_class: str
    semantic_class: str
    native_line: str
    unit_class: str | None
    hit_points: int | None
    base_armor: int | None
    accuracy: int | None
    size: int | None
    weapons: tuple[Weapon, ...]
    counts_toward_garrison_limit: bool
    provenance: dict[str, Any]
    army_kind: str = "player"

    @property
    def primary_weapon(self) -> Weapon:
        return self.weapons[0]

    @property
    def numerically_supported(self) -> bool:
        return self.hit_points is not None and self.base_armor is not None and bool(self.weapons) and self.primary_weapon.damage is not None


class UnitRegistry:
    def __init__(self, definitions: dict[str, UnitDefinition], metadata: dict[str, Any]):
        self._definitions = definitions
        self.metadata = metadata

    @classmethod
    def load(
        cls, profile: str = "infinite-horizons-current", *, include_barbarians: bool = False
    ) -> "UnitRegistry":
        resource = files("ikariam_battle.data.units").joinpath(f"{profile}.json")
        raw = json.loads(resource.read_text(encoding="utf-8"))
        definitions = {}
        for row in raw["units"]:
            definitions[row["id"]] = UnitDefinition(
                row["id"], row["display_name"], row["domain"], row["role"], row.get("support_effect"), row["battlefield_class"],
                row.get("semantic_class", "unknown"), row.get("native_line", row["battlefield_class"]),
                row.get("unit_class"), row.get("hp"), row.get("base_armor"), row.get("accuracy"), row.get("size"),
                tuple(Weapon(w["id"], w.get("damage"), w.get("ammunition"), w.get("trigger", "primary"),
                             w.get("accuracy"), w.get("provenance", {})) for w in row.get("weapons", [])),
                row.get("counts_toward_garrison_limit", True), row["provenance"])
        if include_barbarians:
            from .barbarians import BarbarianFleetRegistry, BarbarianRegistry
            barbarian_registry = BarbarianRegistry.load()
            for barbarian in barbarian_registry.all():
                equivalent = definitions.get(barbarian.equivalent_player_unit or "")
                definitions[barbarian.id] = UnitDefinition(
                    id=barbarian.id,
                    display_name=barbarian.display_name,
                    domain="land",
                    role="combat",
                    support_effect=None,
                    battlefield_class=barbarian.native_line,
                    semantic_class=barbarian.semantic_class,
                    native_line=barbarian.native_line,
                    unit_class=equivalent.unit_class if equivalent else None,
                    hit_points=barbarian.hit_points,
                    base_armor=barbarian.base_armor,
                    accuracy=barbarian.accuracy,
                    size=barbarian.size,
                    weapons=(
                        Weapon(
                            "primary", barbarian.damage, barbarian.ammunition,
                            "primary", barbarian.accuracy, barbarian.provenance,
                        ),
                    ),
                    counts_toward_garrison_limit=True,
                    provenance=barbarian.provenance,
                    army_kind="barbarian",
                )
            fleet_registry = BarbarianFleetRegistry.load()
            for barbarian in fleet_registry.all():
                definitions[barbarian.id] = UnitDefinition(
                    id=barbarian.id,
                    display_name=barbarian.display_name,
                    domain="naval",
                    role="combat",
                    support_effect=None,
                    battlefield_class=barbarian.native_line,
                    semantic_class=barbarian.semantic_class,
                    native_line=barbarian.native_line,
                    unit_class=barbarian.unit_class,
                    hit_points=barbarian.hit_points,
                    base_armor=barbarian.base_armor,
                    accuracy=barbarian.primary_weapon.accuracy,
                    size=barbarian.size,
                    weapons=tuple(
                        Weapon(
                            weapon.id,
                            weapon.damage,
                            weapon.ammunition,
                            weapon.trigger,
                            weapon.accuracy,
                            weapon.provenance,
                        )
                        for weapon in barbarian.weapons
                    ),
                    counts_toward_garrison_limit=True,
                    provenance=barbarian.provenance,
                    army_kind="barbarian",
                )
        return cls(definitions, raw["metadata"])

    def get(self, unit_id: str) -> UnitDefinition:
        try:
            return self._definitions[unit_id]
        except KeyError as exc:
            raise ScenarioError(f"unsupported unit_id: {unit_id}") from exc

    def all(self) -> tuple[UnitDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def public(self) -> list[dict[str, Any]]:
        return [{"id": u.id, "display_name": u.display_name, "domain": u.domain, "role": u.role,
                 "army_kind":u.army_kind,
                 "support_effect":u.support_effect, "battlefield_class": u.battlefield_class,
                 "semantic_class":u.semantic_class, "native_line":u.native_line,
                 "unit_class":u.unit_class, "size":u.size,
                 "hit_points":u.hit_points, "base_armor":u.base_armor,
                 "weapons":[{"id":w.id,"damage":w.damage,"ammunition":w.ammunition,
                             "trigger":w.trigger,"accuracy":w.accuracy} for w in u.weapons],
                 "numerically_supported": u.numerically_supported,
                 "counts_toward_garrison_limit": u.counts_toward_garrison_limit} for u in self.all()]
