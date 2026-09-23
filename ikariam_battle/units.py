from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .models import ScenarioError


@dataclass(frozen=True)
class UnitDefinition:
    id: str
    display_name: str
    battlefield_class: str
    base_attack: int
    base_armor: int
    hit_points: int
    slot_capacity: int
    ammunition: int | None
    target_priority: tuple[str, ...]
    special_properties: tuple[str, ...]
    attack_upgrade_per_level: int
    armor_upgrade_per_level: int
    source: str
    ruleset_version: str


class UnitRegistry:
    def __init__(self, definitions: dict[str, UnitDefinition]):
        self._definitions = definitions

    @classmethod
    def load(cls, ruleset: str = "paper-2020") -> "UnitRegistry":
        path = Path(__file__).resolve().parents[1] / "data" / "units" / f"{ruleset}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls({row["id"]: UnitDefinition(
            id=row["id"], display_name=row["display_name"], battlefield_class=row["battlefield_class"],
            base_attack=row["base_attack"], base_armor=row["base_armor"], hit_points=row["hit_points"],
            slot_capacity=row["slot_capacity"], ammunition=row.get("ammunition"),
            target_priority=tuple(row["target_priority"]), special_properties=tuple(row.get("special_properties", [])),
            attack_upgrade_per_level=row["upgrade_semantics"]["attack_per_level"],
            armor_upgrade_per_level=row["upgrade_semantics"]["armor_per_level"], source=row["source"],
            ruleset_version=row["ruleset_version"],
        ) for row in raw["units"]})

    def get(self, unit_id: str) -> UnitDefinition:
        try:
            return self._definitions[unit_id]
        except KeyError as exc:
            raise ScenarioError(f"unsupported unit_id: {unit_id}") from exc

    def public(self) -> list[dict]:
        return [{"id": u.id, "display_name": u.display_name, "battlefield_class": u.battlefield_class,
                 "source": u.source} for u in self._definitions.values()]
