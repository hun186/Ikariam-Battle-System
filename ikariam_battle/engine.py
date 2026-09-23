from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .attacking_matrix import from_slots
from .battlefield import SMALL_LAND, deploy
from .damage import RoundingPolicy, integer_damage
from .events import Event
from .models import Policy, Scenario, Slot, Wave
from .redistribution import reserve_redistribution
from .units import UnitRegistry


ASSUMPTION = "EXP-I-KILL-001: pooled indirect-kill and floor rounding are used because kill-type selection is unknown"


def _event(events: list[Event], round_no: int, phase: str, kind: str, side: str | None, **details: Any) -> None:
    events.append(Event(round_no, phase, kind, side, details))


def _snapshot(waves: list[Wave]) -> dict[str, Any]:
    units: dict[str, int] = defaultdict(int)
    reserve: dict[str, int] = defaultdict(int)
    slots = []
    for wave in waves:
        units[wave.unit.unit_id] += wave.alive
        reserve[wave.unit.unit_id] += wave.reserve
        slots.extend({"line": None, "slot": s.number, "unit_id": s.unit_id, "wave_id": s.wave_id,
                      "units": s.units, "capacity": s.capacity, "damage": s.damage} for s in wave.slots)
    return {"remaining": dict(units), "reserve": dict(reserve), "slots": slots, "total": sum(units.values())}


def _redistribute(waves: list[Wave], events: list[Event], round_no: int, side: str) -> None:
    for wave in waves:
        alive = wave.alive
        total = wave.total_damage + sum(slot.damage for slot in wave.slots)
        if not alive or not total:
            continue
        allocated = reserve_redistribution(total, alive, [(s.number, s.units) for s in wave.slots])
        for slot in wave.slots:
            slot.damage = allocated[slot.number]
        wave.total_damage = total - sum(allocated.values())
        _event(events, round_no, "redistribute", "redistribution", side, rule="RR", unit_id=wave.unit.unit_id,
               total_damage=total, deployed_damage=allocated, reserve_damage=wave.total_damage)


def _refill(waves: list[Wave], events: list[Event], round_no: int, side: str) -> None:
    for wave in waves:
        for slot in wave.slots:
            available = slot.capacity - slot.units
            moved = min(available, wave.reserve)
            if moved:
                slot.units += moved
                wave.reserve -= moved
                _event(events, round_no, "deploy", "slot_refilled", side, unit_id=slot.unit_id, slot=slot.number, quantity=moved)


def _target_wave(attacker: Wave, targets: list[Wave], registry: UnitRegistry) -> Wave | None:
    priorities = registry.get(attacker.unit.unit_id).target_priority
    for line in priorities:
        candidate = next((w for w in targets if w.alive and registry.get(w.unit.unit_id).battlefield_class == line), None)
        if candidate:
            return candidate
    return None


def _fire(source: list[Wave], target: list[Wave], registry: UnitRegistry, events: list[Event], round_no: int,
          side: str, attacker_hephaistos: bool, defender_hephaistos: bool, casualties: dict[str, int]) -> None:
    # A phase uses a start-of-phase firing snapshot, so casualties do not erase return fire.
    for wave in source:
        if not wave.alive or not wave.slots:
            continue
        target_wave = _target_wave(wave, target, registry)
        if not target_wave or not target_wave.slots:
            continue
        active = [s for s in target_wave.slots if s.units]
        matrix = from_slots([s.units for s in wave.slots], [s.number for s in active])
        _event(events, round_no, "fire", "attacking_matrix", side, unit_id=wave.unit.unit_id,
               target_unit_id=target_wave.unit.unit_id, trace=matrix.as_dict())
        atk = registry.get(wave.unit.unit_id)
        tgt = registry.get(target_wave.unit.unit_id)
        per_hit = integer_damage(atk, tgt, wave.unit.attack_upgrade, target_wave.unit.defense_upgrade,
                                 attacker_hephaistos, defender_hephaistos, RoundingPolicy.FLOOR)
        for slot in active:
            hits = matrix.hits[slot.number]
            dealt = hits * per_hit
            prior_damage = slot.damage
            total = prior_damage + dealt
            killed = min(slot.units, total // tgt.hit_points)
            slot.units -= killed
            slot.damage = total - killed * tgt.hit_points
            casualties[slot.unit_id] += killed
            _event(events, round_no, "fire", "damage", side, source_unit_id=wave.unit.unit_id,
                   target_unit_id=slot.unit_id, target_slot=slot.number, firing_units=hits,
                   damage_per_hit=per_hit, damage=dealt, prior_damage=prior_damage,
                   casualties=killed, persistent_damage=slot.damage,
                   rule="experimental-pooled-I-kill")
            if killed:
                _event(events, round_no, "casualties", "kill", "defender" if side == "attacker" else "attacker",
                       unit_id=slot.unit_id, slot=slot.number, quantity=killed, kill_type="I-kill (experimental)")


def simulate(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    if isinstance(scenario, dict):
        scenario = Scenario.from_dict(scenario)
    registry = UnitRegistry.load(scenario.ruleset)
    attacker = deploy(scenario.attacker, registry, SMALL_LAND)
    defender = deploy(scenario.defender, registry, SMALL_LAND)
    events: list[Event] = []
    for side, waves in (("attacker", attacker), ("defender", defender)):
        for wave in waves:
            for slot in wave.slots:
                _event(events, 0, "deploy", "deployment", side, unit_id=slot.unit_id, wave_id=slot.wave_id,
                       line=registry.get(slot.unit_id).battlefield_class, slot=slot.number, quantity=slot.units,
                       reserve=wave.reserve)
    initial = {"attacker": _snapshot(attacker), "defender": _snapshot(defender)}
    assumptions: list[str] = []
    warnings: list[str] = []
    rounds: list[dict[str, Any]] = [{"round": 0, **deepcopy(initial), "casualties": {"attacker": {}, "defender": {}}}]
    if scenario.policy is Policy.STRICT:
        message = "The paper cannot predict kill-type selection a priori; strict simulation stops before fabricated casualties."
        _event(events, 1, "fire", "unsupported_mechanic", None, rule_id="UNKNOWN-KILL-SELECTION", message=message)
        warnings.append(message)
        return {"ruleset": scenario.ruleset, "policy": scenario.policy.value, "status": "inconclusive",
                "outcome": "inconclusive", "rounds_completed": 0, "casualties": {"attacker": {}, "defender": {}},
                "initial_state": initial, "final_state": initial, "rounds": rounds,
                "events": [e.as_dict() for e in events], "assumptions": assumptions, "warnings": warnings}

    assumptions.append(ASSUMPTION)
    _event(events, 1, "fire", "assumption_applied", None, rule_id="EXP-I-KILL-001", message=ASSUMPTION)
    total_casualties = {"attacker": defaultdict(int), "defender": defaultdict(int)}
    completed = 0
    for number in range(1, scenario.max_rounds + 1):
        _redistribute(attacker, events, number, "attacker"); _redistribute(defender, events, number, "defender")
        _refill(attacker, events, number, "attacker"); _refill(defender, events, number, "defender")
        a_round: dict[str, int] = defaultdict(int); d_round: dict[str, int] = defaultdict(int)
        # Fire is evaluated sequentially by side but each side's surviving deployed units fire.
        _fire(attacker, defender, registry, events, number, "attacker", scenario.effects.attacker_hephaistos,
              scenario.effects.defender_hephaistos, d_round)
        _fire(defender, attacker, registry, events, number, "defender", scenario.effects.defender_hephaistos,
              scenario.effects.attacker_hephaistos, a_round)
        for key, value in a_round.items(): total_casualties["attacker"][key] += value
        for key, value in d_round.items(): total_casualties["defender"][key] += value
        completed = number
        rounds.append({"round": number, "attacker": _snapshot(attacker), "defender": _snapshot(defender),
                       "casualties": {"attacker": dict(a_round), "defender": dict(d_round)}})
        a_alive, d_alive = sum(w.alive for w in attacker), sum(w.alive for w in defender)
        if not a_alive or not d_alive:
            break
        if not a_round and not d_round:
            warnings.append("No casualties occurred; unresolved targeting/damage may prevent a conclusive result.")
            break
    final = {"attacker": _snapshot(attacker), "defender": _snapshot(defender)}
    if final["attacker"]["total"] == 0 and final["defender"]["total"] == 0: outcome = "draw"
    elif final["defender"]["total"] == 0: outcome = "attacker"
    elif final["attacker"]["total"] == 0: outcome = "defender"
    else: outcome = "inconclusive"
    return {"ruleset": scenario.ruleset, "policy": scenario.policy.value, "status": "completed" if outcome != "inconclusive" else "inconclusive",
            "outcome": outcome, "rounds_completed": completed,
            "casualties": {side: dict(values) for side, values in total_casualties.items()},
            "initial_state": initial, "final_state": final, "rounds": rounds,
            "events": [e.as_dict() for e in events], "assumptions": assumptions, "warnings": warnings}
