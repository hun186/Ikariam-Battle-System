from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.resources import files
import json
from typing import Any

from .engine import simulate
from .models import Scenario, ScenarioError, _integer, _object
from .units import UnitRegistry


SIDES = frozenset({"attacker", "defender"})
RUNTIME_LINES = frozenset({"first", "second", "third", "flank", "balloon", "anti-balloon"})
MATCH = "match"
MISMATCH = "mismatch"
NOT_ASSESSABLE = "not_assessable"


@dataclass(frozen=True)
class ObservedSlot:
    side: str
    line: str
    damage_position: int
    casualties: int | None = None
    damage_percent: int | None = None
    life_percent: int | None = None


@dataclass(frozen=True)
class BattleReportFixture:
    game_version: str
    round_number: int
    scenario: Scenario
    observations: tuple[ObservedSlot, ...]
    fixture_id: str | None = None
    evidence_class: str | None = None
    source_note: str | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "BattleReportFixture":
        data = _object(value, "calibration fixture")
        if not isinstance(data.get("game_version"), str):
            raise ScenarioError("game_version must be a string")
        observations = []
        seen: set[tuple[str, str, int, str]] = set()
        raw = data.get("observations")
        if not isinstance(raw, list):
            raise ScenarioError("observations must be a list")
        for item in raw:
            row = _object(item, "observation")
            side, line = row.get("side"), row.get("line")
            if side not in SIDES:
                raise ScenarioError("observation.side must be attacker or defender")
            if line not in RUNTIME_LINES:
                raise ScenarioError("observation.line must be a supported runtime line")
            position = _integer(row.get("damage_position"), "damage_position", 1)
            present = [field for field in ("casualties", "damage_percent", "life_percent") if field in row]
            if not present:
                raise ScenarioError("observation must contain casualties, damage_percent, or life_percent")
            for field in present:
                key = (side, line, position, field)
                if key in seen:
                    raise ScenarioError(f"duplicate observation for {side}/{line}/{position}/{field}")
                seen.add(key)
            observations.append(ObservedSlot(
                side, line, position,
                None if "casualties" not in row else _integer(row["casualties"], "casualties"),
                None if "damage_percent" not in row else _integer(row["damage_percent"], "damage_percent", 0, 100),
                None if "life_percent" not in row else _integer(row["life_percent"], "life_percent", 0, 100),
            ))
        metadata = {}
        for field in ("fixture_id", "evidence_class", "source_note"):
            item = data.get(field)
            if item is not None and (not isinstance(item, str) or not item):
                raise ScenarioError(f"{field} must be a non-empty string")
            metadata[field] = item
        return cls(data["game_version"], _integer(data["round_number"], "round_number", 1),
                   Scenario.from_dict(data["scenario"]), tuple(observations), **metadata)


@dataclass(frozen=True)
class ObservationAssessment:
    side: str
    line: str
    damage_position: int
    field: str
    status: str
    observed: int
    simulated: int | None = None
    expected_interval: tuple[int, int] | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.expected_interval is not None:
            value["expected_interval"] = list(self.expected_interval)
        return {key: item for key, item in value.items() if item is not None}


@dataclass(frozen=True)
class CalibrationResult:
    fixture_id: str | None
    game_version: str
    round_number: int
    simulation_status: str
    reached_round: int
    blockers: tuple[str, ...]
    assessments: tuple[ObservationAssessment, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "game_version": self.game_version,
            "round_number": self.round_number,
            "simulation_status": self.simulation_status,
            "reached_round": self.reached_round,
            "blockers": list(self.blockers),
            "assessments": [assessment.as_dict() for assessment in self.assessments],
        }


def damage_interval_from_report(percent: int, alive_hit_points: int) -> tuple[int, int]:
    """Integer interval compatible with an observed damage percentage rounded up."""
    if not 0 <= percent <= 100 or alive_hit_points < 0: raise ValueError("invalid percentage/HP")
    if percent == 0: return (0, 0)
    lower = ((percent - 1) * alive_hit_points) // 100 + 1
    upper = (percent * alive_hit_points) // 100
    return lower, upper


def _not_assessable(observation: ObservedSlot, field: str, observed: int, reason: str) -> ObservationAssessment:
    return ObservationAssessment(observation.side, observation.line, observation.damage_position,
                                 field, NOT_ASSESSABLE, observed, reason=reason)


def _blockers(result: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({event.get("details", {}).get("rule_id")
                         for event in result.get("events", [])
                         if event.get("type") == "unsupported_mechanic"
                         and event.get("details", {}).get("rule_id")}))


def evaluate_fixture(fixture: BattleReportFixture, simulation_result: dict[str, Any]) -> CalibrationResult:
    """Compare one fixture round with simulator state and slot-addressed damage events."""
    rounds = [row for row in simulation_result.get("rounds", [])
              if row.get("round") == fixture.round_number]
    reached_round = max((row.get("round", 0) for row in simulation_result.get("rounds", [])), default=0)
    blockers = _blockers(simulation_result)
    assessments: list[ObservationAssessment] = []
    if len(rounds) != 1:
        reason = "SIMULATION-ROUND-NOT-REACHED" if not rounds else "AMBIGUOUS-SIMULATION-ROUND"
        for observation in fixture.observations:
            for field in ("casualties", "damage_percent", "life_percent"):
                observed = getattr(observation, field)
                if observed is not None:
                    assessments.append(_not_assessable(observation, field, observed, reason))
        return CalibrationResult(fixture.fixture_id, fixture.game_version, fixture.round_number,
                                 str(simulation_result.get("status", "unknown")), reached_round,
                                 blockers, tuple(assessments))

    round_state = rounds[0]
    registry = UnitRegistry.load(fixture.scenario.profiles.unit_stats)
    for observation in fixture.observations:
        slots = [slot for slot in round_state.get(observation.side, {}).get("slots", [])
                 if slot.get("line") == observation.line
                 and slot.get("damage_position") == observation.damage_position]
        slot_reason = None
        if not slots:
            slot_reason = "SIMULATION-SLOT-NOT-FOUND"
        elif len(slots) > 1:
            slot_reason = "AMBIGUOUS-SIMULATION-SLOT"
        slot = slots[0] if len(slots) == 1 else None

        if observation.casualties is not None:
            matching_events = [event for event in simulation_result.get("events", [])
                               if event.get("round") == fixture.round_number
                               and event.get("type") == "damage"
                               and event.get("details", {}).get("target_side") == observation.side
                               and event.get("details", {}).get("target_line") == observation.line
                               and event.get("details", {}).get("target_damage_position") == observation.damage_position]
            round_damage_events = [event for event in simulation_result.get("events", [])
                                   if event.get("round") == fixture.round_number
                                   and event.get("type") == "damage"]
            unidentified = any(not {"target_side", "target_line", "target_damage_position"}
                               <= event.get("details", {}).keys() for event in round_damage_events)
            if slot_reason:
                assessments.append(_not_assessable(observation, "casualties", observation.casualties, slot_reason))
            elif unidentified:
                assessments.append(_not_assessable(observation, "casualties", observation.casualties,
                                                   "DAMAGE-EVENT-TARGET-IDENTITY-UNAVAILABLE"))
            else:
                actual = sum(event["details"].get("casualties", 0) for event in matching_events)
                status = MATCH if actual == observation.casualties else MISMATCH
                assessments.append(ObservationAssessment(observation.side, observation.line,
                    observation.damage_position, "casualties", status, observation.casualties,
                    simulated=actual, reason="EXACT-TARGET-SLOT-DAMAGE-EVENTS"))

        if observation.damage_percent is not None:
            if slot_reason:
                assessments.append(_not_assessable(observation, "damage_percent", observation.damage_percent, slot_reason))
            else:
                assert slot is not None
                unit = registry.get(slot["unit_id"])
                alive_hp = slot.get("units", 0) * (unit.hit_points or 0)
                if alive_hp <= 0:
                    assessments.append(_not_assessable(observation, "damage_percent", observation.damage_percent,
                                                       "NO-SURVIVING-HIT-POINT-DENOMINATOR"))
                else:
                    interval = damage_interval_from_report(observation.damage_percent, alive_hp)
                    actual = slot.get("damage")
                    if not isinstance(actual, int):
                        assessments.append(_not_assessable(observation, "damage_percent", observation.damage_percent,
                                                           "MISSING-PERSISTENT-SLOT-DAMAGE"))
                    else:
                        status = MATCH if interval[0] <= actual <= interval[1] else MISMATCH
                        assessments.append(ObservationAssessment(observation.side, observation.line,
                            observation.damage_position, "damage_percent", status, observation.damage_percent,
                            simulated=actual, expected_interval=interval,
                            reason="REPORT-PERCENT-ROUND-UP-INTERVAL"))

        if observation.life_percent is not None:
            assessments.append(_not_assessable(observation, "life_percent", observation.life_percent,
                "UNKNOWN-BATTLE-REPORT-LIFE-PERCENT-SEMANTICS"))

    return CalibrationResult(fixture.fixture_id, fixture.game_version, fixture.round_number,
                             str(simulation_result.get("status", "unknown")), reached_round,
                             blockers, tuple(assessments))


def run_fixture(fixture: BattleReportFixture) -> CalibrationResult:
    """Run the fixture scenario, then evaluate its requested report round."""
    return evaluate_fixture(fixture, simulate(fixture.scenario))


def ranged_formation_observations() -> dict[str, Any]:
    """Return calibration-only observations without promoting them to rules."""
    resource = files("ikariam_battle.data.calibration").joinpath(
        "ranged-formation-user-observations.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))
