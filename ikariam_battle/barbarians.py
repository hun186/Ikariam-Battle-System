from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from typing import Any


@dataclass(frozen=True)
class BarbarianUnit:
    id: str
    display_name: str
    semantic_class: str
    native_line: str
    first_appearance_level: int
    last_appearance_level: int | None
    equivalent_player_unit: str | None
    hit_points: int | None
    base_armor: int | None
    damage: int | None
    accuracy: int | None
    ammunition: int | None
    size: int | None
    provenance: dict[str, Any]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "domain": "barbarian",
            "semantic_class": self.semantic_class,
            "native_line": self.native_line,
            "first_appearance_level": self.first_appearance_level,
            "last_appearance_level": self.last_appearance_level,
            "equivalent_player_unit": self.equivalent_player_unit,
            "hit_points": self.hit_points,
            "base_armor": self.base_armor,
            "damage": self.damage,
            "accuracy": self.accuracy,
            "ammunition": self.ammunition,
            "size": self.size,
            "selectable_by_player": False,
            "simulation_ready": False,
            "provenance": self.provenance,
        }


class BarbarianRegistry:
    def __init__(self, definitions: dict[str, BarbarianUnit], metadata: dict[str, Any]):
        self._definitions = definitions
        self.metadata = metadata

    @classmethod
    def load(cls, profile: str = "barbarian-village-current") -> "BarbarianRegistry":
        resource = files("ikariam_battle.data.barbarians").joinpath(f"{profile}.json")
        raw = json.loads(resource.read_text(encoding="utf-8"))
        definitions = {}
        for row in raw["units"]:
            definitions[row["id"]] = BarbarianUnit(
                id=row["id"],
                display_name=row["display_name"],
                semantic_class=row["semantic_class"],
                native_line=row["native_line"],
                first_appearance_level=row["first_appearance_level"],
                last_appearance_level=row.get("last_appearance_level"),
                equivalent_player_unit=row.get("equivalent_player_unit"),
                hit_points=row.get("hp"),
                base_armor=row.get("base_armor"),
                damage=row.get("damage"),
                accuracy=row.get("accuracy"),
                ammunition=row.get("ammunition"),
                size=row.get("size"),
                provenance=row["provenance"],
            )
        return cls(definitions, raw["metadata"])

    def get(self, unit_id: str) -> BarbarianUnit:
        return self._definitions[unit_id]

    def all(self) -> tuple[BarbarianUnit, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def public(self) -> list[dict[str, Any]]:
        return [unit.public() for unit in self.all()]
