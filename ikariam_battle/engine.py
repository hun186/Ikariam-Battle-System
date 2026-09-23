from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .attacking_matrix import from_slot_counts
from .battlefield import battlefield, deploy
from .damage import RoundingPolicy, calculate_damage
from .events import Event
from .models import Policy, Scenario, Wave
from .profiles import ForgeProfile, SupportProfile, WorkshopProfile
from .redistribution import SlotShare, reserve_redistribution
from .units import UnitRegistry


EXPERIMENTAL_ASSUMPTIONS = {
    "EXP-I-KILL-001": "Pool damage per slot and apply indirect kills.",
    "EXP-ROUND-FLOOR-001": "Floor non-integer net damage; the general selector is unknown.",
    "EXP-CHRONOLOGY-001": "Both sides plan fire from the same phase-start snapshot.",
    "EXP-RETARGET-NONE-001": "Do not retarget shots after a slot/line is destroyed within a phase.",
    "EXP-RR-ROUND-NEAREST-001": "Round the total deployed RR share, then assign remainder by damage priority.",
    "EXP-AMMO-STOP-001": "After primary ammunition is exhausted, do not silently switch to an unverified secondary weapon.",
}


def _event(events: list[Event], round_no: int, phase: str, kind: str, side: str | None, **details: Any) -> None:
    events.append(Event(round_no, phase, kind, side, details))


def _snapshot(waves: list[Wave], registry: UnitRegistry) -> dict[str, Any]:
    units, reserve, slots = defaultdict(int), defaultdict(int), []
    for wave in waves:
        unit = registry.get(wave.unit.unit_id)
        units[unit.id] += wave.alive; reserve[unit.id] += wave.reserve
        slots.extend({"slot_id": s.slot_id, "line": s.line, "physical_position": s.physical_position,
                      "damage_position": s.damage_position, "unit_id": s.unit_id, "wave_id": s.wave_id,
                      "units": s.units, "capacity": s.capacity, "damage": s.damage,
                      "ammo_remaining": wave.ammo_remaining} for s in wave.slots)
    slots.sort(key=lambda s: (s["line"], s["physical_position"], s["unit_id"], s["wave_id"]))
    return {"remaining": dict(units), "reserve": dict(reserve), "slots": slots, "total": sum(units.values())}


def _unsupported(scenario: Scenario, events: list[Event], initial: dict, blockers: list[str], warnings: list[str]) -> dict:
    for rule in blockers:
        _event(events, 0, "preflight", "unsupported_mechanic", None, rule_id=rule)
    return {"profiles": scenario.profiles.__dict__, "policy": scenario.policy.value, "status": "inconclusive",
            "outcome": "inconclusive", "rounds_completed": 0, "casualties": {"attacker": {}, "defender": {}},
            "initial_state": initial, "final_state": initial,
            "rounds": [{"round": 0, **deepcopy(initial), "casualties": {"attacker": {}, "defender": {}}}],
            "events": [e.as_dict() for e in events], "assumptions": [], "warnings": warnings}


def _preflight(waves: list[Wave], registry: UnitRegistry) -> list[str]:
    blockers = []
    line_types: dict[str, set[str]] = defaultdict(set)
    line_waves: dict[str, int] = defaultdict(int)
    for wave in waves:
        unit = registry.get(wave.unit.unit_id)
        if unit.role == "support": blockers.append("UNKNOWN-HEALING-ALLOCATION")
        else:
            line_types[unit.battlefield_class].add(unit.id)
            line_waves[unit.battlefield_class] += 1
    if any(len(types) > 1 for types in line_types.values()): blockers.append("UNKNOWN-MIXED-UNIT-AM-ROWS")
    if any(count > 1 for count in line_waves.values()): blockers.append("UNKNOWN-MULTIPLE-TARGET-WAVES")
    return blockers


def _redistribute(waves: list[Wave], events: list[Event], number: int, side: str) -> None:
    for wave in waves:
        total = wave.reserve_damage + sum(slot.damage for slot in wave.slots)
        if not total or not wave.alive: continue
        allocated, reserve = reserve_redistribution(total, wave.alive,
            [SlotShare(slot.damage_position, slot.units) for slot in wave.slots])
        for slot in wave.slots: slot.damage = allocated[slot.damage_position]
        wave.reserve_damage = reserve
        _event(events, number, "redistribute", "redistribution", side, rule="RR", unit_id=wave.unit.unit_id,
               wave_id=wave.unit.wave_id, total_wave_damage=total, deployed_damage=allocated,
               reserve_damage=reserve, damage_conserved=sum(allocated.values()) + reserve == total)


def _refill(waves: list[Wave], events: list[Event], number: int, side: str) -> None:
    for wave in waves:
        for slot in sorted(wave.slots, key=lambda item: item.damage_position):
            moved = min(slot.capacity - slot.units, wave.reserve)
            if moved:
                slot.units += moved; wave.reserve -= moved
                _event(events, number, "deploy", "slot_refilled", side, slot_id=slot.slot_id, quantity=moved)


def _combat_waves(waves: list[Wave], registry: UnitRegistry) -> list[Wave]:
    return sorted((w for w in waves if registry.get(w.unit.unit_id).role == "combat"),
                  key=lambda w: (registry.get(w.unit.unit_id).battlefield_class, w.unit.unit_id, w.unit.wave_id))


def _target(source: Wave, targets: list[Wave], registry: UnitRegistry) -> Wave | None:
    # Narrow MVP: same battlefield class only. Transfers and multiple target
    # types are rejected by preflight rather than decided by Python list order.
    source_line = registry.get(source.unit.unit_id).battlefield_class
    line = {"second":"first", "third":"first", "flank":"first", "balloon":"third",
            "anti-balloon":"balloon"}.get(source_line, source_line)
    choices = [w for w in _combat_waves(targets, registry)
               if registry.get(w.unit.unit_id).battlefield_class == line and w.alive]
    return choices[0] if len(choices) == 1 else None


def _plan_fire(source: list[Wave], target: list[Wave], registry: UnitRegistry, workshop: WorkshopProfile,
               forge: ForgeProfile, events: list[Event], number: int, side: str,
               source_army, target_army) -> list[dict[str, Any]]:
    plans = []
    for wave in _combat_waves(source, registry):
        if not wave.slots or not wave.alive: continue
        unit = registry.get(wave.unit.unit_id)
        if wave.ammo_remaining == 0:
            _event(events, number, "fire", "ammo_exhausted", side, unit_id=unit.id,
                   assumption_id="EXP-AMMO-STOP-001", action="no_primary_fire_no_secondary_switch")
            continue
        enemy = _target(wave, target, registry)
        if enemy is None: continue
        active = [slot for slot in enemy.slots if slot.units]
        trace = from_slot_counts([slot.units for slot in wave.slots], [slot.damage_position for slot in active])
        damage = calculate_damage(unit, registry.get(enemy.unit.unit_id), source_army.workshop.attack_level,
                                  target_army.workshop.armor_level, source_army.forge_level,
                                  target_army.forge_level, workshop, forge, RoundingPolicy.FLOOR)
        _event(events, number, "fire", "attacking_matrix", side, unit_id=unit.id,
               target_unit_id=enemy.unit.unit_id, trace=trace.as_dict())
        _event(events, number, "fire", "damage_calculation", side, source_unit_id=unit.id,
               target_unit_id=enemy.unit.unit_id, **damage.as_dict())
        for slot in active:
            plans.append({"target_unit": enemy.unit.unit_id, "target_wave": enemy.unit.wave_id,
                          "slot_id": slot.slot_id, "hits": trace.hits_by_damage_position[slot.damage_position],
                          "damage_per_hit": damage.final_damage, "source_unit": unit.id, "side": side})
        if wave.ammo_remaining is not None: wave.ammo_remaining -= 1
    return plans


def _apply(plans: list[dict[str, Any]], targets: list[Wave], registry: UnitRegistry,
           events: list[Event], number: int, casualties: dict[str, int]) -> None:
    lookup = {(w.unit.unit_id, w.unit.wave_id, s.slot_id): s for w in targets for s in w.slots}
    for plan in plans:
        slot = lookup[(plan["target_unit"], plan["target_wave"], plan["slot_id"])]
        hp = registry.get(slot.unit_id).hit_points
        assert hp is not None
        dealt, prior = plan["hits"] * plan["damage_per_hit"], slot.damage
        killed = min(slot.units, (prior + dealt) // hp)
        slot.units -= killed; slot.damage = prior + dealt - killed * hp; casualties[slot.unit_id] += killed
        _event(events, number, "fire", "damage", plan["side"], target_slot=slot.slot_id,
               source_unit_id=plan["source_unit"], target_unit_id=slot.unit_id, firing_units=plan["hits"],
               damage=dealt, prior_damage=prior, casualties=killed, persistent_damage=slot.damage,
               assumption_ids=["EXP-I-KILL-001", "EXP-RETARGET-NONE-001"])


def simulate(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    if isinstance(scenario, dict): scenario = Scenario.from_dict(scenario)
    registry = UnitRegistry.load(scenario.profiles.unit_stats)
    field = battlefield(scenario.battlefield)
    attacker, defender = deploy(scenario.attacker, registry, field), deploy(scenario.defender, registry, field)
    events: list[Event] = []
    for side, waves in (("attacker", attacker), ("defender", defender)):
        for wave in waves:
            for slot in wave.slots:
                _event(events, 0, "deploy", "deployment", side, slot_id=slot.slot_id, line=slot.line,
                       physical_position=slot.physical_position, damage_position=slot.damage_position,
                       unit_id=slot.unit_id, wave_id=slot.wave_id, quantity=slot.units, reserve=wave.reserve)
    initial = {"attacker": _snapshot(attacker, registry), "defender": _snapshot(defender, registry)}
    warnings = ["Legacy empirical mechanics are being applied to review-supplied current numeric profiles; calibration is required."]
    blockers = sorted(set(_preflight(attacker, registry) + _preflight(defender, registry)))
    if scenario.policy is Policy.STRICT:
        blockers += ["UNKNOWN-KILL-SELECTION", "UNKNOWN-ROUNDING-SELECTOR", "UNKNOWN-COMPLETE-CHRONOLOGY"]
        return _unsupported(scenario, events, initial, sorted(set(blockers)), warnings)
    if {"UNKNOWN-MIXED-UNIT-AM-ROWS", "UNKNOWN-MULTIPLE-TARGET-WAVES"} & set(blockers):
        return _unsupported(scenario, events, initial, blockers, warnings)
    assumptions = [{"id": key, "description": value} for key, value in EXPERIMENTAL_ASSUMPTIONS.items()]
    if "UNKNOWN-HEALING-ALLOCATION" in blockers:
        assumptions.append({"id":"EXP-HEAL-NONE-001", "description":"Support healing is not applied because allocation is unknown."})
    for assumption in assumptions:
        _event(events, 0, "preflight", "assumption_applied", None, **assumption)
    workshop, forge = WorkshopProfile.load(scenario.profiles.workshop), ForgeProfile.load(scenario.profiles.forge)
    total = {"attacker": defaultdict(int), "defender": defaultdict(int)}
    rounds = [{"round":0, **deepcopy(initial), "casualties":{"attacker":{},"defender":{}}}]
    completed = 0
    for number in range(1, scenario.max_rounds + 1):
        _redistribute(attacker, events, number, "attacker"); _redistribute(defender, events, number, "defender")
        _refill(attacker, events, number, "attacker"); _refill(defender, events, number, "defender")
        # Both plans are made before either is applied: no hidden attacker-first bias.
        a_plan = _plan_fire(attacker, deepcopy(defender), registry, workshop, forge, events, number, "attacker", scenario.attacker, scenario.defender)
        d_plan = _plan_fire(defender, deepcopy(attacker), registry, workshop, forge, events, number, "defender", scenario.defender, scenario.attacker)
        a_dead, d_dead = defaultdict(int), defaultdict(int)
        _apply(a_plan, defender, registry, events, number, d_dead); _apply(d_plan, attacker, registry, events, number, a_dead)
        for k,v in a_dead.items(): total["attacker"][k] += v
        for k,v in d_dead.items(): total["defender"][k] += v
        completed = number
        rounds.append({"round":number,"attacker":_snapshot(attacker,registry),"defender":_snapshot(defender,registry),
                       "casualties":{"attacker":dict(a_dead),"defender":dict(d_dead)}})
        if not a_dead and not d_dead and not a_plan and not d_plan: break
    final = {"attacker":_snapshot(attacker,registry),"defender":_snapshot(defender,registry)}
    a, d = final["attacker"]["total"], final["defender"]["total"]
    outcome = "draw" if not a and not d else "attacker" if not d else "defender" if not a else "inconclusive"
    return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"completed" if outcome != "inconclusive" else "inconclusive",
            "outcome":outcome,"rounds_completed":completed,"casualties":{k:dict(v) for k,v in total.items()},
            "initial_state":initial,"final_state":final,"rounds":rounds,"events":[e.as_dict() for e in events],
            "assumptions":assumptions,"warnings":warnings}
