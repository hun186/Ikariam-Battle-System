from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from typing import Any

from .attacking_matrix import from_slot_counts
from .battlefield import battlefield, deploy
from .damage import RoundingPolicy, calculate_damage
from .economy import MilitaryEconomyProfile
from .events import Event
from .formation import FormationRules, eligible_runtime_lines
from .models import Policy, Scenario, ScenarioError, Wave
from .profiles import BattleEndProfile, ContinuationState, ForgeProfile, TargetingProfile, WorkshopProfile
from .redistribution import SlotShare, reserve_redistribution
from .units import UnitRegistry
from .weapon_selection import UnsupportedWeaponSelection, select_active_weapon


EXPERIMENTAL_POLICIES = {
    "EXP-I-KILL-001": "Pool damage per slot and apply indirect kills.",
    "EXP-ROUND-FLOOR-001": "Floor non-integer net damage; the general selector is unknown.",
    "EXP-CHRONOLOGY-001": "Both sides plan fire from the same phase-start snapshot.",
    "EXP-RETARGET-NONE-001": "Do not retarget shots after a slot/line is destroyed within a phase.",
    "EXP-RR-ROUND-HALF-UP-001": "Round the total deployed RR share half-up, then assign remainder by damage priority.",
    "EXP-AMMO-STOP-001": "After primary ammunition is exhausted, do not silently switch to an unverified secondary weapon.",
    "EXP-AMMO-PARTIAL-ORDER-001": "Allocate a partial ammunition pool by source-slot damage priority.",
    "EXP-TARGET-LEGACY-001": "Use the versioned legacy/community class target priorities.",
    "EXP-ACCURACY-IGNORED-001": "Do not reduce Am hits by weapon accuracy because its algorithm is unresolved.",
    "EXP-BATTLE-END-ROUND-BOUNDARY-001": "Evaluate battle-sustaining forces at the initial and completed-round boundaries.",
    "EXP-HEAL-NONE-001": "Support healing is not applied because allocation is unknown.",
    "EXP-MORALE-NONE-001": "Cook morale is not applied because the current morale algorithm is unresolved.",
}


def _event(events: list[Event], round_no: int, phase: str, kind: str, side: str | None, **details: Any) -> None:
    events.append(Event(round_no, phase, kind, side, details))


def _assume(applied: dict[str, dict[str, str]], events: list[Event], assumption_id: str,
            round_no: int, phase: str) -> None:
    if assumption_id in applied:
        return
    assumption = {"id": assumption_id, "description": EXPERIMENTAL_POLICIES[assumption_id]}
    applied[assumption_id] = assumption
    _event(events, round_no, phase, "assumption_applied", None, **assumption)


def _snapshot(waves: list[Wave], registry: UnitRegistry, battle_end: BattleEndProfile) -> dict[str, Any]:
    units, main_line, fallback, reserve, support = (defaultdict(int) for _ in range(5))
    slots: list[dict[str, Any]] = []
    wave_states: list[dict[str, Any]] = []
    for wave in waves:
        unit = registry.get(wave.unit.unit_id)
        units[unit.id] += wave.alive; reserve[unit.id] += wave.reserve
        runtime_lines = {slot.line for slot in wave.slots}
        if "first" in runtime_lines:
            main_line[unit.id] += wave.alive
        elif unit.native_line in battle_end.fallback_candidate_classes:
            fallback[unit.id] += wave.alive
        if wave.support_units:
            support[unit.id] += wave.support_units
        ammo_percent = None if wave.ammo_capacity_shots is None else round(
            100 * (wave.ammo_pool_shots or 0) / wave.ammo_capacity_shots, 2)
        wave_states.append({"unit_id": unit.id, "wave_id": wave.unit.wave_id,
                            "entry_batch_id": wave.unit.wave_id, "alive": wave.alive,
                            "reserve": wave.reserve, "ammo_pool_shots": wave.ammo_pool_shots,
                            "ammo_capacity_shots": wave.ammo_capacity_shots,
                            "munition_percent": ammo_percent,
                            "deployed_lines": sorted({slot.line for slot in wave.slots if slot.units})})
        slots.extend({"slot_id": s.slot_id, "line": s.line, "physical_position": s.physical_position,
                      "damage_position": s.damage_position, "unit_id": s.unit_id, "wave_id": s.wave_id,
                      "units": s.units, "capacity": s.capacity, "damage": s.damage,
                      "entry_batch_id": s.wave_id, "display_name": unit.display_name,
                      "semantic_class": unit.semantic_class, "native_line": unit.native_line,
                      "attack_upgrade": wave.unit.attack_upgrade,
                      "armor_upgrade": wave.unit.armor_upgrade,
                      "hit_points_percent": round(100 * (s.units * unit.hit_points - s.damage) /
                                                  (s.units * unit.hit_points), 2) if s.units else None,
                      "ammo_pool_shots": wave.ammo_pool_shots,
                      "ammo_capacity_shots": wave.ammo_capacity_shots,
                      "munition_percent": ammo_percent} for s in wave.slots)
    slots.sort(key=lambda s: (s["line"], s["physical_position"], s["unit_id"], s["wave_id"]))
    state = battle_end.continuation_state(sum(main_line.values()), sum(fallback.values()))
    return {"remaining": dict(units), "main_line_holding_remaining": dict(main_line),
            "main_line_holding_total": sum(main_line.values()),
            "fallback_candidate_remaining": dict(fallback),
            "fallback_candidate_total": sum(fallback.values()), "continuation_state": state.value,
            "reserve": dict(reserve),
            "deployed_support": dict(support), "waves": wave_states,
            "slots": slots, "total": sum(units.values())}


def _unsupported(scenario: Scenario, events: list[Event], initial: dict, blockers: list[str], warnings: list[str]) -> dict:
    for rule in blockers:
        _event(events, 0, "preflight", "unsupported_mechanic", None, rule_id=rule)
    return {"profiles": scenario.profiles.__dict__, "policy": scenario.policy.value, "status": "inconclusive",
            "outcome": "inconclusive", "rounds_completed": 0, "casualties": {"attacker": {}, "defender": {}},
            "initial_state": initial, "final_state": initial,
            "rounds": [{"round": 0, **deepcopy(initial), "casualties": {"attacker": {}, "defender": {}}}],
            "events": [e.as_dict() for e in events], "assumptions": [], "warnings": warnings}


def _preflight(waves: list[Wave], registry: UnitRegistry, rules: FormationRules, field) -> list[str]:
    blockers = []
    line_types: dict[str, set[str]] = defaultdict(set)
    line_waves: dict[str, int] = defaultdict(int)
    deployed_lines = {slot.line for wave in waves for slot in wave.slots if slot.units}
    for wave in waves:
        if len({slot.line for slot in wave.slots}) > 1:
            blockers.append("UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS")
        unit = registry.get(wave.unit.unit_id)
        if unit.support_effect == "healing": blockers.append("UNKNOWN-HEALING-ALLOCATION")
        elif unit.support_effect == "morale": blockers.append("UNKNOWN-MORALE-SUPPORT")
        else:
            if (wave.reserve and not any(slot.units for slot in wave.slots)
                    and deployed_lines.intersection(eligible_runtime_lines(unit, rules, field))):
                blockers.append("UNKNOWN-CROSS-WAVE-FORMATION-REBUILD")
            for runtime_line in {slot.line for slot in wave.slots if slot.units}:
                line_types[runtime_line].add(unit.id)
                line_waves[runtime_line] += 1
                try:
                    select_active_weapon(unit, runtime_line)
                except UnsupportedWeaponSelection:
                    if unit.semantic_class == "light_infantry":
                        blockers.append("UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT")
    if any(len(types) > 1 for types in line_types.values()): blockers.append("UNKNOWN-MIXED-UNIT-AM-ROWS")
    if any(count > 1 for count in line_waves.values()): blockers.append("UNKNOWN-MULTIPLE-TARGET-WAVES")
    return blockers


def _guard_single_line_waves(waves: list[Wave]) -> None:
    """Prevent structurally valid, but uncalibrated, multi-line execution."""
    if any(len({slot.line for slot in wave.slots}) > 1 for wave in waves):
        raise ScenarioError("UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS")


def _redistribute(waves: list[Wave], events: list[Event], number: int, side: str,
                  applied: dict[str, dict[str, str]]) -> None:
    _guard_single_line_waves(waves)
    for wave in waves:
        total = wave.reserve_damage + sum(slot.damage for slot in wave.slots)
        if not total or not wave.alive: continue
        _assume(applied, events, "EXP-RR-ROUND-HALF-UP-001", number, "redistribute")
        allocated, reserve = reserve_redistribution(total, wave.alive,
            [SlotShare(slot.damage_position, slot.units) for slot in wave.slots])
        for slot in wave.slots: slot.damage = allocated[slot.damage_position]
        wave.reserve_damage = reserve
        _event(events, number, "redistribute", "redistribution", side, rule="RR", unit_id=wave.unit.unit_id,
               wave_id=wave.unit.wave_id, total_wave_damage=total, deployed_damage=allocated,
               reserve_damage=reserve, damage_conserved=sum(allocated.values()) + reserve == total)


def _rebuild_formation(waves: list[Wave], events: list[Event], number: int, side: str) -> None:
    """Re-establish existing runtime placements before RR.

    Initial placement is owned by the pure formation planner. Cross-wave slot
    replacement remains deliberately guarded until damage transfer is known.
    """
    _guard_single_line_waves(waves)
    for wave in waves:
        for slot in sorted(wave.slots, key=lambda item: item.damage_position):
            moved = min(slot.capacity - slot.units, wave.reserve)
            if moved:
                slot.units += moved; wave.reserve -= moved
                _event(events, number, "deploy", "slot_refilled", side, slot_id=slot.slot_id, quantity=moved)


def _prepare_round_start(waves: list[Wave], events: list[Event], number: int, side: str,
                         applied: dict[str, dict[str, str]]) -> None:
    """Establish the following-round deployment before applying PDF RR."""
    _rebuild_formation(waves, events, number, side)
    _redistribute(waves, events, number, side, applied)


def _runtime_line(wave: Wave, registry: UnitRegistry) -> str:
    lines = {slot.line for slot in wave.slots if slot.units}
    if len(lines) == 1:
        return next(iter(lines))
    # Reserve-only compatibility for internal callers; deployed combat always
    # takes its role from Slot.line and multi-line execution is guarded.
    return registry.get(wave.unit.unit_id).native_line


def _combat_waves(waves: list[Wave], registry: UnitRegistry) -> list[Wave]:
    return sorted((w for w in waves if registry.get(w.unit.unit_id).role == "combat"),
                  key=lambda w: (_runtime_line(w, registry), w.unit.unit_id, w.unit.wave_id))


def _target(source: Wave, targets: list[Wave], registry: UnitRegistry,
            targeting: TargetingProfile) -> tuple[Wave | None, str | None]:
    _guard_single_line_waves([source, *targets])
    source_line = _runtime_line(source, registry)
    for target_line in targeting.priorities[source_line]:
        choices = [w for w in _combat_waves(targets, registry)
                   if _runtime_line(w, registry) == target_line
                   and any(slot.units > 0 for slot in w.slots)]
        if len(choices) == 1: return choices[0], target_line
        if len(choices) > 1: return None, target_line
    return None, None


def _plan_fire(source: list[Wave], target: list[Wave], registry: UnitRegistry, workshop: WorkshopProfile,
               forge: ForgeProfile, targeting: TargetingProfile, events: list[Event], number: int, side: str,
               source_army, target_army, applied: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    _guard_single_line_waves([*source, *target])
    plans = []
    for wave in _combat_waves(source, registry):
        if not wave.slots or not wave.alive: continue
        unit = registry.get(wave.unit.unit_id)
        runtime_line = _runtime_line(wave, registry)
        weapon = select_active_weapon(unit, runtime_line)
        if wave.ammo_pool_shots == 0:
            _assume(applied, events, "EXP-AMMO-STOP-001", number, "fire")
            _event(events, number, "fire", "ammo_exhausted", side, unit_id=unit.id,
                   assumption_id="EXP-AMMO-STOP-001", action="no_primary_fire_no_secondary_switch")
            continue
        enemy, target_class = _target(wave, target, registry, targeting)
        if enemy is None: continue
        _assume(applied, events, "EXP-TARGET-LEGACY-001", number, "fire")
        _assume(applied, events, "EXP-ACCURACY-IGNORED-001", number, "fire")
        _assume(applied, events, "EXP-ROUND-FLOOR-001", number, "fire")
        active = [slot for slot in enemy.slots if slot.units]
        deployed = sorted(wave.slots, key=lambda slot: slot.damage_position)
        firing_counts = [slot.units for slot in deployed]
        total_firing = sum(firing_counts)
        if wave.ammo_pool_shots is not None and wave.ammo_pool_shots < total_firing:
            _assume(applied, events, "EXP-AMMO-PARTIAL-ORDER-001", number, "fire")
            remaining = wave.ammo_pool_shots
            firing_counts = []
            for slot in deployed:
                count = min(slot.units, remaining); firing_counts.append(count); remaining -= count
            _event(events, number, "fire", "partial_ammunition", side, unit_id=unit.id,
                   assumption_id="EXP-AMMO-PARTIAL-ORDER-001", firing_counts=firing_counts)
        shots = sum(firing_counts)
        if shots == 0: continue
        trace = from_slot_counts(firing_counts, [slot.damage_position for slot in active])
        damage = calculate_damage(unit, registry.get(enemy.unit.unit_id), wave.unit.attack_upgrade,
                                  enemy.unit.armor_upgrade, source_army.forge_level,
                                  target_army.forge_level, workshop, forge, RoundingPolicy.FLOOR,
                                  weapon=weapon)
        _event(events, number, "fire", "attacking_matrix", side, unit_id=unit.id,
               target_unit_id=enemy.unit.unit_id, target_class=target_class,
               weapon_id=weapon.id, targeting_assumption="EXP-TARGET-LEGACY-001", trace=trace.as_dict())
        _event(events, number, "fire", "damage_calculation", side, source_unit_id=unit.id,
               target_unit_id=enemy.unit.unit_id, **damage.as_dict())
        for slot in active:
            plans.append({"target_unit": enemy.unit.unit_id, "target_wave": enemy.unit.wave_id,
                          "target_side": "defender" if side == "attacker" else "attacker",
                          "slot_id": slot.slot_id, "hits": trace.hits_by_damage_position[slot.damage_position],
                          "damage_per_hit": damage.final_damage, "source_unit": unit.id, "side": side})
        if wave.ammo_pool_shots is not None: wave.ammo_pool_shots -= shots
    return plans


def _apply(plans: list[dict[str, Any]], targets: list[Wave], registry: UnitRegistry,
           events: list[Event], number: int, casualties: dict[str, int],
           applied: dict[str, dict[str, str]]) -> None:
    lookup = {(w.unit.unit_id, w.unit.wave_id, s.slot_id): s for w in targets for s in w.slots}
    for plan in plans:
        _assume(applied, events, "EXP-I-KILL-001", number, "fire")
        _assume(applied, events, "EXP-RETARGET-NONE-001", number, "fire")
        slot = lookup[(plan["target_unit"], plan["target_wave"], plan["slot_id"])]
        hp = registry.get(slot.unit_id).hit_points
        assert hp is not None
        dealt, prior = plan["hits"] * plan["damage_per_hit"], slot.damage
        killed = min(slot.units, (prior + dealt) // hp)
        slot.units -= killed; slot.damage = prior + dealt - killed * hp; casualties[slot.unit_id] += killed
        _event(events, number, "fire", "damage", plan["side"], target_slot=slot.slot_id,
               target_side=plan["target_side"], target_line=slot.line,
               target_damage_position=slot.damage_position, source_unit_id=plan["source_unit"], target_unit_id=slot.unit_id, firing_units=plan["hits"],
               damage=dealt, prior_damage=prior, casualties=killed, persistent_damage=slot.damage,
               assumption_ids=["EXP-I-KILL-001", "EXP-RETARGET-NONE-001"])


def _termination(attacker: dict[str, Any], defender: dict[str, Any]) -> tuple[str | None, str | None]:
    a, d = attacker["continuation_state"], defender["continuation_state"]
    if ContinuationState.FALLBACK_REQUIRED.value in {a, d}: return None, None
    if a == ContinuationState.SUSTAINING.value and d == ContinuationState.NOT_SUSTAINING.value:
        return "attacker", "defender"
    if d == ContinuationState.SUSTAINING.value and a == ContinuationState.NOT_SUSTAINING.value:
        return "defender", "attacker"
    return None, None


def _non_sustaining(snapshot: dict[str, Any]) -> dict[str, int]:
    sustaining = {**snapshot["main_line_holding_remaining"], **snapshot["fallback_candidate_remaining"]}
    return {unit: count for unit, count in snapshot["remaining"].items()
            if count and unit not in sustaining}


def _simulate_core(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    if isinstance(scenario, dict): scenario = Scenario.from_dict(scenario)
    registry = UnitRegistry.load(scenario.profiles.unit_stats)
    field = battlefield(scenario.battlefield)
    formation_rules = FormationRules.load(scenario.profiles.formation)
    battle_end = BattleEndProfile.load(scenario.profiles.battle_end)
    attacker = deploy(scenario.attacker, registry, field, scenario.profiles.formation)
    defender = deploy(scenario.defender, registry, field, scenario.profiles.formation)
    events: list[Event] = []
    for side, waves in (("attacker", attacker), ("defender", defender)):
        for wave in waves:
            for slot in wave.slots:
                _event(events, 0, "deploy", "deployment", side, slot_id=slot.slot_id, line=slot.line,
                       physical_position=slot.physical_position, damage_position=slot.damage_position,
                       unit_id=slot.unit_id, wave_id=slot.wave_id, quantity=slot.units, reserve=wave.reserve)
    initial = {"attacker": _snapshot(attacker, registry, battle_end),
               "defender": _snapshot(defender, registry, battle_end)}
    warnings = ["Legacy empirical mechanics are being applied to review-supplied current numeric profiles; calibration is required."]
    blockers = sorted(set(_preflight(attacker, registry, formation_rules, field)
                          + _preflight(defender, registry, formation_rules, field)))
    initial_states = {side: state["continuation_state"] for side, state in initial.items()}
    fallback_sides = [side for side, state in initial_states.items()
                      if state == ContinuationState.FALLBACK_REQUIRED.value]
    initial_outcome, _ = _termination(initial["attacker"], initial["defender"])
    if fallback_sides:
        blockers.append("UNKNOWN-FORMATION-FALLBACK")
    if initial_outcome is not None:
        blockers.append("UNKNOWN-INITIAL-BATTLE-END-TIMING")
    if all(state == ContinuationState.NOT_SUSTAINING.value for state in initial_states.values()):
        blockers.append("UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
    if scenario.policy is Policy.STRICT:
        blockers += ["UNKNOWN-KILL-SELECTION", "UNKNOWN-ROUNDING-SELECTOR", "UNKNOWN-COMPLETE-CHRONOLOGY",
                     "UNKNOWN-ACCURACY", "UNKNOWN-TARGET-TRANSFER"]
        return _unsupported(scenario, events, initial, sorted(set(blockers)), warnings)
    if {"UNKNOWN-MIXED-UNIT-AM-ROWS", "UNKNOWN-MULTIPLE-TARGET-WAVES",
        "UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS",
        "UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT",
        "UNKNOWN-CROSS-WAVE-FORMATION-REBUILD"} & set(blockers):
        return _unsupported(scenario, events, initial, blockers, warnings)
    applied: dict[str, dict[str, str]] = {}
    if "UNKNOWN-HEALING-ALLOCATION" in blockers:
        _assume(applied, events, "EXP-HEAL-NONE-001", 0, "preflight")
    if "UNKNOWN-MORALE-SUPPORT" in blockers:
        _assume(applied, events, "EXP-MORALE-NONE-001", 0, "preflight")
    if fallback_sides:
        _event(events, 0, "battle_end", "unsupported_mechanic", None,
               rule_id="UNKNOWN-FORMATION-FALLBACK", affected_sides=fallback_sides)
        return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"inconclusive",
                "outcome":"inconclusive","rounds_completed":0,"casualties":{"attacker":{},"defender":{}},
                "initial_state":initial,"final_state":initial,
                "rounds":[{"round":0,**deepcopy(initial),"casualties":{"attacker":{},"defender":{}}}],
                "events":[e.as_dict() for e in events],"assumptions":list(applied.values()),"warnings":warnings}
    if all(state == ContinuationState.NOT_SUSTAINING.value for state in initial_states.values()):
        _event(events, 0, "battle_end", "unsupported_mechanic", None,
               rule_id="UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
        return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"inconclusive",
                "outcome":"inconclusive","rounds_completed":0,"casualties":{"attacker":{},"defender":{}},
                "initial_state":initial,"final_state":initial,
                "rounds":[{"round":0,**deepcopy(initial),"casualties":{"attacker":{},"defender":{}}}],
                "events":[e.as_dict() for e in events],"assumptions":list(applied.values()),"warnings":warnings}
    if initial_outcome is not None:
        _assume(applied, events, "EXP-BATTLE-END-ROUND-BOUNDARY-001", 0, "battle_end")
        _, losing = _termination(initial["attacker"], initial["defender"])
        _event(events, 0, "battle_end", "battle_termination", None,
               reason="no_battle_sustaining_units", losing_side=losing,
               surviving_non_sustaining={side: _non_sustaining(state) for side, state in initial.items()})
        return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"completed",
                "outcome":initial_outcome,"rounds_completed":0,"casualties":{"attacker":{},"defender":{}},
                "initial_state":initial,"final_state":initial,
                "rounds":[{"round":0,**deepcopy(initial),"casualties":{"attacker":{},"defender":{}}}],
                "events":[e.as_dict() for e in events],"assumptions":list(applied.values()),"warnings":warnings}
    workshop, forge = WorkshopProfile.load(scenario.profiles.workshop), ForgeProfile.load(scenario.profiles.forge)
    targeting = TargetingProfile.load(scenario.profiles.targeting)
    total = {"attacker": defaultdict(int), "defender": defaultdict(int)}
    rounds = [{"round":0, **deepcopy(initial), "casualties":{"attacker":{},"defender":{}}}]
    completed = 0
    fallback_boundary = False
    both_zero_boundary = False
    round_cap_reached = False
    for number in range(1, scenario.max_rounds + 1):
        _prepare_round_start(attacker, events, number, "attacker", applied); _prepare_round_start(defender, events, number, "defender", applied)
        # Both plans are made before either is applied: no hidden attacker-first bias.
        a_plan = _plan_fire(attacker, deepcopy(defender), registry, workshop, forge, targeting, events, number, "attacker", scenario.attacker, scenario.defender, applied)
        d_plan = _plan_fire(defender, deepcopy(attacker), registry, workshop, forge, targeting, events, number, "defender", scenario.defender, scenario.attacker, applied)
        if a_plan or d_plan:
            _assume(applied, events, "EXP-CHRONOLOGY-001", number, "fire")
        a_dead, d_dead = defaultdict(int), defaultdict(int)
        _apply(a_plan, defender, registry, events, number, d_dead, applied); _apply(d_plan, attacker, registry, events, number, a_dead, applied)
        for k,v in a_dead.items(): total["attacker"][k] += v
        for k,v in d_dead.items(): total["defender"][k] += v
        completed = number
        attacker_state, defender_state = _snapshot(attacker,registry,battle_end), _snapshot(defender,registry,battle_end)
        rounds.append({"round":number,"attacker":attacker_state,"defender":defender_state,
                       "casualties":{"attacker":dict(a_dead),"defender":dict(d_dead)}})
        states = {"attacker": attacker_state["continuation_state"],
                  "defender": defender_state["continuation_state"]}
        fallback_sides = [side for side, state in states.items()
                          if state == ContinuationState.FALLBACK_REQUIRED.value]
        if fallback_sides:
            _event(events, number, "battle_end", "unsupported_mechanic", None,
                   rule_id="UNKNOWN-FORMATION-FALLBACK", affected_sides=fallback_sides)
            fallback_boundary = True
            break
        if all(state == ContinuationState.NOT_SUSTAINING.value for state in states.values()):
            _event(events, number, "battle_end", "unsupported_mechanic", None,
                   rule_id="UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
            both_zero_boundary = True
            break
        outcome, losing = _termination(attacker_state, defender_state)
        if outcome is not None:
            _assume(applied, events, "EXP-BATTLE-END-ROUND-BOUNDARY-001", number, "battle_end")
            _event(events, number, "battle_end", "battle_termination", None,
                   reason="no_battle_sustaining_units", losing_side=losing,
                   surviving_non_sustaining={"attacker":_non_sustaining(attacker_state),
                                             "defender":_non_sustaining(defender_state)})
            break
        if not a_dead and not d_dead and not a_plan and not d_plan: break
    else:
        round_cap_reached = True
        _event(events, scenario.max_rounds, "battle_end", "safety_limit_reached", None,
               reason="max_rounds_reached", limit=scenario.max_rounds)
    final = {"attacker":_snapshot(attacker,registry,battle_end),"defender":_snapshot(defender,registry,battle_end)}
    outcome, _ = _termination(final["attacker"], final["defender"])
    if fallback_boundary or both_zero_boundary:
        outcome = None
    outcome = outcome or "inconclusive"
    return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"completed" if outcome != "inconclusive" else "inconclusive",
            "outcome":outcome,"rounds_completed":completed,"casualties":{k:dict(v) for k,v in total.items()},
            "initial_state":initial,"final_state":final,"rounds":rounds,"events":[e.as_dict() for e in events],
            "assumptions":list(applied.values()),"warnings":warnings}


def _decimal_json(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _attach_battle_statistics(result: dict[str, Any], economy: MilitaryEconomyProfile) -> dict[str, Any]:
    losses: dict[str, dict[str, int | float]] = {}
    for side in ("attacker", "defender"):
        casualties = result.get("casualties", {}).get(side, {})
        basis_loss = economy.resource_cost_basis_loss(casualties)
        score_loss = economy.score_loss(casualties)
        losses[side] = {
            "resource_cost_basis_lost": basis_loss,
            "general_score_lost": _decimal_json(score_loss),
        }

    result["military_score"] = {
        "attacker": {
            **losses["attacker"],
            "general_score_destroyed": losses["defender"]["general_score_lost"],
        },
        "defender": {
            **losses["defender"],
            "general_score_destroyed": losses["attacker"]["general_score_lost"],
        },
    }

    gross_damage = {"attacker": 0, "defender": 0}
    for event in result.get("events", []):
        if event.get("type") != "damage":
            continue
        side = event.get("side")
        if side in gross_damage:
            gross_damage[side] += int(event.get("details", {}).get("damage", 0))
    result["combat_statistics"] = {
        side: {"gross_damage_dealt": gross_damage[side]}
        for side in ("attacker", "defender")
    }
    return result


def simulate(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    normalized = Scenario.from_dict(scenario) if isinstance(scenario, dict) else scenario
    result = _simulate_core(normalized)
    economy = MilitaryEconomyProfile.load(normalized.profiles.economy)
    return _attach_battle_statistics(result, economy)
