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


@dataclass(frozen=True)
class UnitDefinition:
    id: str
    display_name: str
    domain: str
    role: str
    support_effect: str | None
    battlefield_class: str
    hit_points: int | None
    base_armor: int | None
    accuracy: int | None
    size: int | None
    weapons: tuple[Weapon, ...]
    counts_toward_garrison_limit: bool
    provenance: dict[str, Any]

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
    def load(cls, profile: str = "infinite-horizons-current") -> "UnitRegistry":
        resource = files("ikariam_battle.data.units").joinpath(f"{profile}.json")
        raw = json.loads(resource.read_text(encoding="utf-8"))
        definitions = {}
        for row in raw["units"]:
            definitions[row["id"]] = UnitDefinition(
                row["id"], row["display_name"], row["domain"], row["role"], row.get("support_effect"), row["battlefield_class"],
                row.get("hp"), row.get("base_armor"), row.get("accuracy"), row.get("size"),
                tuple(Weapon(w["id"], w.get("damage"), w.get("ammunition"), w.get("trigger", "primary"), w.get("accuracy")) for w in row.get("weapons", [])),
                row.get("counts_toward_garrison_limit", True), row["provenance"])
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
                 "support_effect":u.support_effect, "battlefield_class": u.battlefield_class, "numerically_supported": u.numerically_supported,
                 "counts_toward_garrison_limit": u.counts_toward_garrison_limit} for u in self.all()]
