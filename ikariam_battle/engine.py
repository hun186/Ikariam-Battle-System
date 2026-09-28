from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from typing import Any

from .battlefield import battlefield, deploy
from .damage import RoundingPolicy, calculate_damage
from .economy import MilitaryEconomyProfile
from .events import Event
from .formation import FormationRules, eligible_runtime_lines
from .models import Army, Policy, Scenario, ScenarioError, Wave
from .profiles import BattleEndProfile, ContinuationState, ForgeProfile, SupportProfile, TargetingProfile, WorkshopProfile
from .redistribution import SlotShare, reserve_redistribution
from .units import UnitRegistry
from .weapon_selection import UnsupportedWeaponSelection, select_active_weapon


EXPERIMENTAL_POLICIES = {
    "EXP-D-KILL-SEQUENTIAL-001": "Resolve individual shots sequentially against the most-damaged current unit; discard overkill unless an unimplemented special kill rule applies.",
    "EXP-SLOT-DAMAGE-EVEN-001": "When RR leaves aggregate persistent damage in a slot, distribute it as evenly as possible across surviving units before sequential fire; exact within-slot allocation is unresolved.",
    "EXP-IR-DISABLED-001": "Immediate Redistribution has an implementation hook but its trigger is unknown, so it is not triggered.",
    "EXP-SR-DISABLED-001": "Slot Redistribution has an implementation hook but its trigger is unknown, so it is not triggered.",
    "EXP-ROUND-FLOOR-001": "Floor non-integer net damage; the general selector is unknown.",
    "EXP-RR-ROUND-HALF-UP-001": "Round the total deployed RR share half-up, then assign remainder by damage priority.",
    "EXP-AMMO-STOP-001": "After primary ammunition is exhausted, do not silently switch to an unverified secondary weapon.",
    "EXP-AMMO-PARTIAL-ORDER-001": "Allocate a partial ammunition pool by source-slot damage priority.",
    "EXP-ACCURACY-IGNORED-001": "Do not reduce Am hits by weapon accuracy because its algorithm is unresolved.",
    "EXP-BATTLE-END-ROUND-BOUNDARY-001": "Evaluate battle-sustaining forces at the initial and completed-round boundaries.",
    "EXP-HEAL-NONE-001": "Support healing is not applied because allocation is unknown.",
    "EXP-MORALE-NONE-001": "Cook morale is not applied because the current morale algorithm is unresolved.",
}


def _event(events: list[Event], round_no: int, phase: str, kind: str, side: str | None, **details: Any) -> None:
    events.append(Event(round_no, phase, kind, side, details))


def _assume(applied: dict[str, dict[str, str]], events: list[Event], assumption_id: str,
            round_no: int, phase: str, side: str | None = None) -> None:
    assumption = {"id": assumption_id, "description": EXPERIMENTAL_POLICIES[assumption_id]}
    if assumption_id not in applied:
        applied[assumption_id] = assumption
    # The public assumption list stays unique by policy ID, while events record
    # where a side-specific support boundary was actually reached.
    if any(event.type == "assumption_applied"
           and event.side == side
           and event.details.get("id") == assumption_id
           for event in events):
        return
    _event(events, round_no, phase, "assumption_applied", side, **assumption)


def _snapshot(waves: list[Wave], registry: UnitRegistry, battle_end: BattleEndProfile,
              slot_losses: dict[tuple[str, str], int] | None = None) -> dict[str, Any]:
    units, main_line, fallback, reserve, support = (defaultdict(int) for _ in range(5))
    slot_losses = slot_losses or {}
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
        reserve_hp_percent = None
        if wave.reserve and unit.hit_points:
            reserve_hp_percent = round(
                100 * (wave.reserve * unit.hit_points - wave.reserve_damage) /
                (wave.reserve * unit.hit_points), 2)
        wave_states.append({"unit_id": unit.id, "wave_id": wave.unit.wave_id,
                            "entry_batch_id": wave.unit.batch_id,
                            "arrival_round": wave.unit.arrival_round, "alive": wave.alive,
                            "reserve": wave.reserve, "reserve_damage": wave.reserve_damage,
                            "reserve_hit_points_percent": reserve_hp_percent,
                            "ammo_pool_shots": wave.ammo_pool_shots,
                            "ammo_capacity_shots": wave.ammo_capacity_shots,
                            "munition_percent": ammo_percent,
                            "deployed_lines": sorted({slot.line for slot in wave.slots if slot.units})})
        slots.extend({"slot_id": s.slot_id, "line": s.line, "physical_position": s.physical_position,
                      "damage_position": s.damage_position, "unit_id": s.unit_id, "wave_id": s.wave_id,
                      "units": s.units, "capacity": s.capacity, "damage": s.damage,
                      "entry_batch_id": wave.unit.batch_id,
                      "arrival_round": wave.unit.arrival_round, "display_name": unit.display_name,
                      "semantic_class": unit.semantic_class, "native_line": unit.native_line,
                      "attack_upgrade": wave.unit.attack_upgrade,
                      "armor_upgrade": wave.unit.armor_upgrade,
                      "casualties": slot_losses.get((s.wave_id, s.slot_id), 0),
                      "hit_points_percent": round(100 * (s.units * unit.hit_points - s.damage) /
                                                  (s.units * unit.hit_points), 2) if s.units else 0,
                      "ammo_pool_shots": wave.ammo_pool_shots,
                      "ammo_capacity_shots": wave.ammo_capacity_shots,
                      "munition_percent": ammo_percent} for s in wave.slots
                     if s.units or slot_losses.get((s.wave_id, s.slot_id), 0))
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
    for wave in waves:
        if not wave.alive:
            continue
        if len({slot.line for slot in wave.slots}) > 1:
            blockers.append("UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS")
        unit = registry.get(wave.unit.unit_id)
        if unit.support_effect == "healing": blockers.append("UNKNOWN-HEALING-ALLOCATION")
        elif unit.support_effect == "morale": blockers.append("UNKNOWN-MORALE-SUPPORT")
        else:
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
        deployed = [SlotShare(slot.damage_position, slot.units)
                    for slot in wave.slots if slot.units]
        allocated, reserve = reserve_redistribution(total, wave.alive, deployed)
        for slot in wave.slots:
            slot.damage = allocated.get(slot.damage_position, 0)
        wave.reserve_damage = reserve
        _event(events, number, "redistribute", "redistribution", side, rule="RR", unit_id=wave.unit.unit_id,
               wave_id=wave.unit.wave_id, total_wave_damage=total, deployed_damage=allocated,
               reserve_damage=reserve, damage_conserved=sum(allocated.values()) + reserve == total)


def _rebuild_formation(waves: list[Wave], events: list[Event], number: int, side: str) -> None:
    """Re-pack each existing same-wave runtime line by PDF damage priority before RR.

    Ascending damage position is the battlefield's center-first deployment order.
    This may move same-wave survivors from outer physical slots back toward the
    center, but it never creates new slots or crosses wave/line boundaries.
    """
    _guard_single_line_waves(waves)
    for wave in waves:
        slots = sorted(wave.slots, key=lambda item: item.damage_position)
        if not slots:
            continue
        deployable = wave.reserve + sum(slot.units for slot in slots)
        previous = {slot.slot_id: slot.units for slot in slots}
        remaining = deployable
        for slot in slots:
            slot.units = min(slot.capacity, remaining)
            remaining -= slot.units
        wave.reserve = remaining
        for slot in slots:
            prior = previous[slot.slot_id]
            if slot.units != prior:
                _event(events, number, "deploy", "slot_repacked", side,
                       slot_id=slot.slot_id, damage_position=slot.damage_position,
                       previous_units=prior, units=slot.units)


def _prepare_round_start(waves: list[Wave], events: list[Event], number: int, side: str,
                         applied: dict[str, dict[str, str]]) -> None:
    """Center-first re-pack same-wave placements, then apply PDF RR."""
    _rebuild_formation(waves, events, number, side)
    _redistribute(waves, events, number, side, applied)


def _arrival_waves(army: Army, round_no: int, registry: UnitRegistry,
                   events: list[Event], side: str) -> list[Wave]:
    """Activate unit-specific state waves for entry batches that arrive this round.

    Arrival is modeled independently from formation replacement: newly arrived
    combat units begin in Reserve. If they immediately need an open runtime slot,
    the deferred cross-wave boundary below stops rather than inventing placement.
    """
    items = [item for item in army.units if item.arrival_round == round_no]
    if not items:
        return []
    by_batch: dict[str, list[Any]] = defaultdict(list)
    result: list[Wave] = []
    for item in items:
        unit = registry.get(item.unit_id)
        by_batch[item.batch_id].append(item)
        if unit.role == "support":
            result.append(Wave(item, 0, [], 0, None, item.quantity))
        else:
            ammo = None if unit.primary_weapon.ammunition is None else item.quantity * unit.primary_weapon.ammunition
            result.append(Wave(item, item.quantity, [], 0, ammo, 0, ammo))
    for batch_id, batch_items in sorted(by_batch.items()):
        units: dict[str, int] = defaultdict(int)
        for item in batch_items:
            units[item.unit_id] += item.quantity
        _event(events, round_no, "arrival", "entry_batch_arrived", side,
               entry_batch_id=batch_id, arrival_round=round_no,
               units=dict(sorted(units.items())))
    return result


def _cross_wave_rebuild_requirements(waves: list[Wave], registry: UnitRegistry,
                                     rules: FormationRules, field) -> list[dict[str, Any]]:
    """Return only cross-wave placements that are required *now*.

    A reserve-only wave is harmless while every eligible runtime line is full.
    The evidence boundary is reached only after same-wave refill/repack leaves a
    real empty physical slot that another active wave could occupy.
    """
    occupied: dict[str, set[int]] = defaultdict(set)
    for wave in waves:
        for slot in wave.slots:
            if slot.units:
                occupied[slot.line].add(slot.damage_position)
    requirements: list[dict[str, Any]] = []
    for wave in waves:
        if not wave.reserve or any(slot.units for slot in wave.slots):
            continue
        unit = registry.get(wave.unit.unit_id)
        if unit.role != "combat":
            continue
        for runtime_line in eligible_runtime_lines(unit, rules, field):
            geometry = field.lines.get(runtime_line)
            if geometry is None:
                continue
            open_positions = [position for position in geometry.damage_priority
                              if position not in occupied[runtime_line]]
            if not open_positions:
                continue
            requirements.append({
                "runtime_line": runtime_line,
                "unit_id": unit.id,
                "wave_id": wave.unit.wave_id,
                "entry_batch_id": wave.unit.batch_id,
                "arrival_round": wave.unit.arrival_round,
                "reserve": wave.reserve,
                "open_damage_positions": open_positions,
            })
    return requirements


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


def _target_for_line(source_line: str, targets: list[Wave], registry: UnitRegistry,
                     targeting: TargetingProfile) -> tuple[Wave | None, str | None]:
    _guard_single_line_waves(targets)
    for target_line in targeting.priorities[source_line]:
        choices = [w for w in _combat_waves(targets, registry)
                   if _runtime_line(w, registry) == target_line
                   and any(slot.units > 0 for slot in w.slots)]
        if len(choices) == 1:
            return choices[0], target_line
        if len(choices) > 1:
            return None, target_line
    return None, None


def _target(source: Wave, targets: list[Wave], registry: UnitRegistry,
            targeting: TargetingProfile) -> tuple[Wave | None, str | None]:
    return _target_for_line(_runtime_line(source, registry), targets, registry, targeting)


def _shot_rows(firing_counts: list[int]) -> list[int]:
    """Expand an Am source into individual shots while preserving row order."""
    return [row
            for row in range(1, max(firing_counts, default=0) + 1)
            for _ in range(sum(count >= row for count in firing_counts))]


def _snapshot_phase_fire(source: list[Wave], target: list[Wave], registry: UnitRegistry,
                         targeting: TargetingProfile, events: list[Event], number: int,
                         side: str, runtime_line: str,
                         applied: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Freeze firing eligibility for one formation before either side takes damage."""
    volleys: list[dict[str, Any]] = []
    for wave in _combat_waves(source, registry):
        if _runtime_line(wave, registry) != runtime_line or not wave.slots or not wave.alive:
            continue
        enemy, _ = _target_for_line(runtime_line, target, registry, targeting)
        if enemy is None:
            continue
        unit = registry.get(wave.unit.unit_id)
        weapon = select_active_weapon(unit, runtime_line)
        if wave.ammo_pool_shots == 0:
            _assume(applied, events, "EXP-AMMO-STOP-001", number, "fire")
            _event(events, number, "fire", "ammo_exhausted", side, unit_id=unit.id,
                   firing_phase=runtime_line, assumption_id="EXP-AMMO-STOP-001",
                   action="no_primary_fire_no_secondary_switch")
            continue
        _assume(applied, events, "EXP-ACCURACY-IGNORED-001", number, "fire")
        _assume(applied, events, "EXP-ROUND-FLOOR-001", number, "fire")
        deployed = sorted((slot for slot in wave.slots if slot.units),
                          key=lambda slot: slot.damage_position)
        firing_counts = [slot.units for slot in deployed]
        total_firing = sum(firing_counts)
        if wave.ammo_pool_shots is not None and wave.ammo_pool_shots < total_firing:
            _assume(applied, events, "EXP-AMMO-PARTIAL-ORDER-001", number, "fire")
            remaining = wave.ammo_pool_shots
            firing_counts = []
            for slot in deployed:
                count = min(slot.units, remaining)
                firing_counts.append(count)
                remaining -= count
            _event(events, number, "fire", "partial_ammunition", side, unit_id=unit.id,
                   firing_phase=runtime_line, assumption_id="EXP-AMMO-PARTIAL-ORDER-001",
                   firing_counts=firing_counts)
        row_numbers = _shot_rows(firing_counts)
        if not row_numbers:
            continue
        if wave.ammo_pool_shots is not None:
            wave.ammo_pool_shots -= len(row_numbers)
        volleys.append({
            "side": side,
            "source_unit": unit.id,
            "source_wave": wave.unit.wave_id,
            "runtime_line": runtime_line,
            "weapon_id": weapon.id,
            "attack_upgrade": wave.unit.attack_upgrade,
            "row_numbers": row_numbers,
        })
    return volleys


def _plan_fire(source: list[Wave], target: list[Wave], registry: UnitRegistry,
               workshop: WorkshopProfile, forge: ForgeProfile, targeting: TargetingProfile,
               events: list[Event], number: int, side: str, source_army, target_army,
               applied: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Compatibility helper used by focused tests; the engine executes per phase."""
    del workshop, forge, source_army, target_army
    plans: list[dict[str, Any]] = []
    for runtime_line in targeting.firing_order:
        plans.extend(_snapshot_phase_fire(
            source, target, registry, targeting, events, number, side, runtime_line, applied))
    return plans


def _even_unit_damage(total: int, units: int) -> list[int]:
    if units <= 0:
        return []
    base, extra = divmod(total, units)
    return [base + 1] * extra + [base] * (units - extra)


def _build_damage_queues(waves: list[Wave], registry: UnitRegistry, events: list[Event],
                         number: int, side: str,
                         applied: dict[str, dict[str, str]]) -> dict[tuple[str, str, str], list[int]]:
    """Materialize aggregate slot damage for sequential-hit resolution this round."""
    queues: dict[tuple[str, str, str], list[int]] = {}
    for wave in waves:
        unit = registry.get(wave.unit.unit_id)
        if unit.role != "combat":
            continue
        hp = unit.hit_points
        assert hp is not None
        for slot in wave.slots:
            if not slot.units:
                continue
            if slot.damage < 0 or slot.damage >= hp * slot.units:
                raise ScenarioError("persistent slot damage must be below surviving slot HP")
            if slot.damage and slot.units > 1:
                _assume(applied, events, "EXP-SLOT-DAMAGE-EVEN-001", number, "round_start")
            queues[(wave.unit.unit_id, wave.unit.wave_id, slot.slot_id)] = sorted(
                _even_unit_damage(slot.damage, slot.units), reverse=True)
    return queues


def _rebalance_damage_queue(queue: list[int]) -> None:
    queue[:] = sorted(_even_unit_damage(sum(queue), len(queue)), reverse=True)


def _ir_trigger(*_args: Any, **_kwargs: Any) -> bool:
    return False


def _sr_trigger(*_args: Any, **_kwargs: Any) -> bool:
    return False


def _apply_sequential_hit(slot, queue: list[int], hp: int, damage: int) -> tuple[int, int, int]:
    """D-kill baseline: focus the most-damaged survivor; discard overkill."""
    if not queue or not slot.units:
        return 0, 0, 0
    prior_unit_damage = queue[0]
    casualty = 0
    overkill = 0
    if prior_unit_damage + damage >= hp:
        casualty = 1
        overkill = max(0, prior_unit_damage + damage - hp)
        queue.pop(0)
    else:
        queue[0] = prior_unit_damage + damage
    slot.units = len(queue)
    slot.damage = sum(queue)
    return prior_unit_damage, casualty, overkill


def _resolve_volleys(volleys: list[dict[str, Any]], targets: list[Wave],
                      queues: dict[tuple[str, str, str], list[int]],
                      registry: UnitRegistry, workshop: WorkshopProfile, forge: ForgeProfile,
                      targeting: TargetingProfile, events: list[Event], number: int,
                      source_army, target_army, casualties: dict[str, int],
                      slot_casualties: dict[tuple[str, str], int],
                      applied: dict[str, dict[str, str]]) -> None:
    for volley in volleys:
        if not volley["row_numbers"]:
            continue
        _assume(applied, events, "EXP-D-KILL-SEQUENTIAL-001", number, "fire")
        _assume(applied, events, "EXP-IR-DISABLED-001", number, "fire")
        source_unit = registry.get(volley["source_unit"])
        weapon = next(item for item in source_unit.weapons if item.id == volley["weapon_id"])
        matrix_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        damage_groups: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
        calculation_keys: set[tuple[str, str, str, int]] = set()
        address_books: dict[tuple[str, str, str], tuple[Any, ...]] = {}

        for row_number in volley["row_numbers"]:
            enemy, target_class = _target_for_line(
                volley["runtime_line"], targets, registry, targeting)
            if enemy is None or target_class is None:
                break

            address_key = (enemy.unit.unit_id, enemy.unit.wave_id, target_class)
            if address_key not in address_books:
                address_books[address_key] = tuple(sorted(
                    (slot for slot in enemy.slots if slot.units),
                    key=lambda slot: slot.damage_position))
            addressed = address_books[address_key]
            if not addressed:
                continue
            target_slot = addressed[(row_number - 1) % len(addressed)]

            matrix_key = (enemy.unit.unit_id, enemy.unit.wave_id, target_class)
            matrix = matrix_groups.setdefault(matrix_key, {
                "target_unit_id": enemy.unit.unit_id,
                "target_class": target_class,
                "rows": defaultdict(int),
                "hits": defaultdict(int),
                "empty_hits": defaultdict(int),
                "positions": {slot.damage_position for slot in addressed},
            })
            matrix["rows"][row_number] += 1
            matrix["hits"][target_slot.damage_position] += 1

            if not target_slot.units:
                matrix["empty_hits"][target_slot.damage_position] += 1
                _event(events, number, "fire", "shot_addressed_empty_slot", volley["side"],
                       firing_phase=volley["runtime_line"], source_unit_id=source_unit.id,
                       target_side="defender" if volley["side"] == "attacker" else "attacker",
                       target_unit_id=target_slot.unit_id, target_wave=enemy.unit.wave_id,
                       target_slot=target_slot.slot_id, target_line=target_slot.line,
                       target_damage_position=target_slot.damage_position,
                       target_class=target_class, weapon_id=weapon.id,
                       action="address_preserved_no_retarget")
                continue

            target_unit = registry.get(target_slot.unit_id)
            damage_trace = calculate_damage(
                source_unit, target_unit, volley["attack_upgrade"], enemy.unit.armor_upgrade,
                source_army.forge_level, target_army.forge_level, workshop, forge,
                RoundingPolicy.FLOOR, weapon=weapon)
            calculation_key = (
                source_unit.id, target_unit.id, weapon.id, damage_trace.final_damage)
            if calculation_key not in calculation_keys:
                calculation_keys.add(calculation_key)
                _event(events, number, "fire", "damage_calculation", volley["side"],
                       firing_phase=volley["runtime_line"], source_unit_id=source_unit.id,
                       target_unit_id=target_unit.id, **damage_trace.as_dict())

            queue_key = (enemy.unit.unit_id, enemy.unit.wave_id, target_slot.slot_id)
            queue = queues[queue_key]
            prior_slot_damage = target_slot.damage
            prior_unit_damage, killed, overkill = _apply_sequential_hit(
                target_slot, queue, target_unit.hit_points or 0, damage_trace.final_damage)
            casualties[target_slot.unit_id] += killed
            if killed:
                slot_casualties[(target_slot.wave_id, target_slot.slot_id)] += killed

            damage_key = (
                enemy.unit.unit_id, enemy.unit.wave_id, target_slot.slot_id,
                target_class, damage_trace.final_damage)
            group = damage_groups.setdefault(damage_key, {
                "target_unit_id": target_slot.unit_id,
                "target_wave": enemy.unit.wave_id,
                "target_slot": target_slot.slot_id,
                "target_line": target_slot.line,
                "target_damage_position": target_slot.damage_position,
                "damage": 0,
                "firing_units": 0,
                "casualties": 0,
                "overkill_discarded": 0,
                "prior_damage": prior_slot_damage,
                "first_target_unit_damage": prior_unit_damage,
            })
            group["damage"] += damage_trace.final_damage
            group["firing_units"] += 1
            group["casualties"] += killed
            group["overkill_discarded"] += overkill

            if _ir_trigger(volley, enemy, target_slot, row_number):
                _rebalance_damage_queue(queue)
                target_slot.damage = sum(queue)

        for matrix in matrix_groups.values():
            max_row = max(matrix["rows"], default=0)
            _event(events, number, "fire", "attacking_matrix", volley["side"],
                   firing_phase=volley["runtime_line"], unit_id=source_unit.id,
                   target_unit_id=matrix["target_unit_id"],
                   target_class=matrix["target_class"], weapon_id=weapon.id,
                   targeting_authority="GAMEFORGE_IN_GAME_HELP",
                   trace={
                       "row_populations": [matrix["rows"].get(row, 0)
                                           for row in range(1, max_row + 1)],
                       "target_damage_positions": sorted(matrix["positions"]),
                       "hits_by_damage_position": dict(matrix["hits"]),
                       "empty_addressed_shots_by_damage_position": dict(matrix["empty_hits"]),
                   })
        for group in damage_groups.values():
            target_wave = next(
                wave for wave in targets
                if wave.unit.unit_id == group["target_unit_id"]
                and wave.unit.wave_id == group["target_wave"])
            target_slot = next(slot for slot in target_wave.slots
                               if slot.slot_id == group["target_slot"])
            _event(events, number, "fire", "damage", volley["side"],
                   firing_phase=volley["runtime_line"],
                   target_side="defender" if volley["side"] == "attacker" else "attacker",
                   source_unit_id=source_unit.id,
                   resolution="sequential_d_kill_baseline",
                   persistent_damage=target_slot.damage,
                   assumption_ids=["EXP-D-KILL-SEQUENTIAL-001", "EXP-IR-DISABLED-001"],
                   **group)


def _apply_slot_redistribution(
    waves: list[Wave], queues: dict[tuple[str, str, str], list[int]]
) -> None:
    for wave in waves:
        for slot in wave.slots:
            key = (wave.unit.unit_id, wave.unit.wave_id, slot.slot_id)
            queue = queues.get(key)
            if queue is None or not queue:
                continue
            _rebalance_damage_queue(queue)
            slot.damage = sum(queue)



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
    # Validate every scheduled unit now, but only round-0 entry batches are
    # present on the battlefield initially.
    for army in (scenario.attacker, scenario.defender):
        for item in army.units:
            unit = registry.get(item.unit_id)
            if unit.domain != field.domain:
                raise ScenarioError(f"{unit.id} is {unit.domain} and cannot enter {field.id}")
            if unit.role != "support" and not unit.numerically_supported:
                raise ScenarioError(f"{unit.id} has unverified numerical fields and cannot be simulated")
    attacker = deploy(Army(tuple(item for item in scenario.attacker.units if item.arrival_round == 0),
                           scenario.attacker.forge_level),
                      registry, field, scenario.profiles.formation)
    defender = deploy(Army(tuple(item for item in scenario.defender.units if item.arrival_round == 0),
                           scenario.defender.forge_level),
                      registry, field, scenario.profiles.formation)
    events: list[Event] = []
    for side, waves in (("attacker", attacker), ("defender", defender)):
        for wave in waves:
            for slot in wave.slots:
                _event(events, 0, "deploy", "deployment", side, slot_id=slot.slot_id, line=slot.line,
                       physical_position=slot.physical_position, damage_position=slot.damage_position,
                       unit_id=slot.unit_id, wave_id=slot.wave_id,
                       entry_batch_id=wave.unit.batch_id, arrival_round=wave.unit.arrival_round,
                       quantity=slot.units, reserve=wave.reserve)
    initial = {"attacker": _snapshot(attacker, registry, battle_end),
               "defender": _snapshot(defender, registry, battle_end)}
    warnings = ["Legacy empirical mechanics are being applied to review-supplied current numeric profiles; calibration is required."]
    attacker_blockers = _preflight(attacker, registry, formation_rules, field)
    defender_blockers = _preflight(defender, registry, formation_rules, field)
    blockers = sorted(set(attacker_blockers + defender_blockers))
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
        blockers += ["UNKNOWN-KILL-SELECTION", "UNKNOWN-ROUNDING-SELECTOR",
                     "UNKNOWN-ACCURACY", "UNKNOWN-IR-TRIGGER", "UNKNOWN-SR-TRIGGER"]
        return _unsupported(scenario, events, initial, sorted(set(blockers)), warnings)
    if {"UNKNOWN-MIXED-UNIT-AM-ROWS", "UNKNOWN-MULTIPLE-TARGET-WAVES",
        "UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS",
        "UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT"} & set(blockers):
        return _unsupported(scenario, events, initial, blockers, warnings)
    applied: dict[str, dict[str, str]] = {}
    for side, side_blockers in (("attacker", attacker_blockers), ("defender", defender_blockers)):
        if "UNKNOWN-HEALING-ALLOCATION" in side_blockers:
            _assume(applied, events, "EXP-HEAL-NONE-001", 0, "preflight", side)
        if "UNKNOWN-MORALE-SUPPORT" in side_blockers:
            _assume(applied, events, "EXP-MORALE-NONE-001", 0, "preflight", side)
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
    cross_wave_boundary = False
    for number in range(1, scenario.max_rounds + 1):
        attacker_arrivals = _arrival_waves(scenario.attacker, number, registry, events, "attacker")
        defender_arrivals = _arrival_waves(scenario.defender, number, registry, events, "defender")
        attacker.extend(attacker_arrivals)
        defender.extend(defender_arrivals)
        arrival_blockers = {
            "attacker": _preflight(attacker_arrivals, registry, formation_rules, field),
            "defender": _preflight(defender_arrivals, registry, formation_rules, field),
        }
        for side, side_blockers in arrival_blockers.items():
            if "UNKNOWN-HEALING-ALLOCATION" in side_blockers:
                _assume(applied, events, "EXP-HEAL-NONE-001", number, "arrival", side)
            if "UNKNOWN-MORALE-SUPPORT" in side_blockers:
                _assume(applied, events, "EXP-MORALE-NONE-001", number, "arrival", side)
        _prepare_round_start(attacker, events, number, "attacker", applied)
        _prepare_round_start(defender, events, number, "defender", applied)
        cross_wave = {
            "attacker": _cross_wave_rebuild_requirements(attacker, registry, formation_rules, field),
            "defender": _cross_wave_rebuild_requirements(defender, registry, formation_rules, field),
        }
        if any(cross_wave.values()):
            for side, requirements in cross_wave.items():
                if requirements:
                    _event(events, number, "round_start", "unsupported_mechanic", side,
                           rule_id="UNKNOWN-CROSS-WAVE-FORMATION-REBUILD",
                           requirements=requirements)
            cross_wave_boundary = True
            break
        # Art of Warfare: same formations on both sides shoot simultaneously;
        # casualties from an earlier formation suppress firing in later phases.
        a_dead, d_dead = defaultdict(int), defaultdict(int)
        a_slot_dead, d_slot_dead = defaultdict(int), defaultdict(int)
        a_queues = _build_damage_queues(attacker, registry, events, number, "attacker", applied)
        d_queues = _build_damage_queues(defender, registry, events, number, "defender", applied)
        for firing_phase in targeting.firing_order:
            a_volleys = _snapshot_phase_fire(
                attacker, defender, registry, targeting, events, number, "attacker",
                firing_phase, applied)
            d_volleys = _snapshot_phase_fire(
                defender, attacker, registry, targeting, events, number, "defender",
                firing_phase, applied)
            if not a_volleys and not d_volleys:
                continue
            _event(events, number, "fire", "formation_fire_phase", None,
                   firing_phase=firing_phase, simultaneous=True,
                   attacker_shots=sum(len(v["row_numbers"]) for v in a_volleys),
                   defender_shots=sum(len(v["row_numbers"]) for v in d_volleys))
            _resolve_volleys(
                a_volleys, defender, d_queues, registry, workshop, forge, targeting,
                events, number, scenario.attacker, scenario.defender, d_dead, d_slot_dead, applied)
            _resolve_volleys(
                d_volleys, attacker, a_queues, registry, workshop, forge, targeting,
                events, number, scenario.defender, scenario.attacker, a_dead, a_slot_dead, applied)
            _assume(applied, events, "EXP-SR-DISABLED-001", number, "fire")
            if _sr_trigger(firing_phase, attacker, defender):
                _apply_slot_redistribution(attacker, a_queues)
                _apply_slot_redistribution(defender, d_queues)
        for k,v in a_dead.items(): total["attacker"][k] += v
        for k,v in d_dead.items(): total["defender"][k] += v
        completed = number
        attacker_state = _snapshot(attacker, registry, battle_end, a_slot_dead)
        defender_state = _snapshot(defender, registry, battle_end, d_slot_dead)
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
        _event(events, scenario.max_rounds, "battle_end", "safety_limit_reached", None,
               reason="max_rounds_reached", limit=scenario.max_rounds)
    final = {"attacker":_snapshot(attacker,registry,battle_end),"defender":_snapshot(defender,registry,battle_end)}
    outcome, _ = _termination(final["attacker"], final["defender"])
    if fallback_boundary or both_zero_boundary or cross_wave_boundary:
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


def _support_assumption_round(result: dict[str, Any], assumption_id: str,
                              side: str) -> int | None:
    rounds = [
        int(event.get("round", 0))
        for event in result.get("events", [])
        if event.get("type") == "assumption_applied"
        and event.get("side") == side
        and event.get("details", {}).get("id") == assumption_id
    ]
    return min(rounds) if rounds else None


def _strict_support_boundary_reached(scenario: Scenario, result: dict[str, Any],
                                     side: str, unit_id: str, rule_id: str) -> bool:
    if scenario.policy != Policy.STRICT:
        return False
    army = scenario.attacker if side == "attacker" else scenario.defender
    present_at_start = any(unit.unit_id == unit_id and unit.quantity > 0 and unit.arrival_round == 0
                           for unit in army.units)
    if not present_at_start:
        return False
    return any(event.get("type") == "unsupported_mechanic"
               and event.get("details", {}).get("rule_id") == rule_id
               for event in result.get("events", []))


def _morale_status(scenario: Scenario, result: dict[str, Any]) -> dict[str, Any]:
    assumption_id = "EXP-MORALE-NONE-001"
    strict_rule_id = "UNKNOWN-MORALE-SUPPORT"
    sides: dict[str, dict[str, Any]] = {}
    for side, army in (("attacker", scenario.attacker), ("defender", scenario.defender)):
        cook_count = sum(unit.quantity for unit in army.units if unit.unit_id == "cook")
        reach_round = _support_assumption_round(result, assumption_id, side)
        if not cook_count:
            status = "not_present"
        elif reach_round is not None:
            status = "ignored_by_named_assumption"
        elif _strict_support_boundary_reached(scenario, result, side, "cook", strict_rule_id):
            status = "unsupported_boundary"
        else:
            status = "not_reached"
        sides[side] = {
            "cook_count": cook_count,
            "status": status,
            "effect_applied": False,
        }
    return {
        "modeled": False,
        "strict_rule_id": strict_rule_id,
        "experimental_assumption_id": assumption_id,
        "common_player_reference": (
            "About 15 Cooks is a common practical configuration, "
            "not a verified fixed morale formula."
        ),
        "sides": sides,
    }


def _healing_status(
    scenario: Scenario,
    result: dict[str, Any],
    support: SupportProfile,
) -> dict[str, Any]:
    assumption_id = "EXP-HEAL-NONE-001"
    strict_rule_id = "UNKNOWN-HEALING-ALLOCATION"
    sides: dict[str, dict[str, Any]] = {}
    for side, army in (("attacker", scenario.attacker), ("defender", scenario.defender)):
        doctor_count = sum(unit.quantity for unit in army.units if unit.unit_id == "doctor")
        reach_round = _support_assumption_round(result, assumption_id, side)
        if not doctor_count:
            status = "not_present"
            amount = 0
        elif reach_round is not None:
            status = "ignored_by_named_assumption"
            amount = None
        elif _strict_support_boundary_reached(scenario, result, side, "doctor", strict_rule_id):
            status = "unsupported_boundary"
            amount = None
        else:
            status = "not_reached"
            amount = None
        sides[side] = {
            "doctor_count": doctor_count,
            "status": status,
            "effect_applied": False,
            "healing_amount": amount,
        }
    return {
        "modeled": False,
        "strict_rule_id": strict_rule_id,
        "experimental_assumption_id": assumption_id,
        "derived_capacity_per_doctor": support.derived_capacity,
        "capacity_is_allocation_formula": False,
        "sides": sides,
    }


def _attach_battle_statistics(
    result: dict[str, Any],
    economy: MilitaryEconomyProfile,
    scenario: Scenario,
) -> dict[str, Any]:
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

    support = SupportProfile.load(scenario.profiles.support)
    healing_status = _healing_status(scenario, result, support)
    healing_reach_round = {
        side: _support_assumption_round(result, "EXP-HEAL-NONE-001", side)
        for side in ("attacker", "defender")
    }
    gross_dealt = {"attacker": 0, "defender": 0}
    gross_taken = {"attacker": 0, "defender": 0}
    per_round: dict[int, dict[str, dict[str, int]]] = {}

    def round_stats(number: int) -> dict[str, dict[str, int]]:
        return per_round.setdefault(number, {
            "attacker": {"damage_dealt": 0, "damage_taken": 0},
            "defender": {"damage_dealt": 0, "damage_taken": 0},
        })

    for row in result.get("rounds", []):
        round_stats(int(row.get("round", 0)))

    for event in result.get("events", []):
        if event.get("type") != "damage":
            continue
        source = event.get("side")
        target = event.get("details", {}).get("target_side")
        if source not in gross_dealt or target not in gross_taken:
            continue
        amount = int(event.get("details", {}).get("damage", 0))
        number = int(event.get("round", 0))
        stats = round_stats(number)
        stats[source]["damage_dealt"] += amount
        stats[target]["damage_taken"] += amount
        gross_dealt[source] += amount
        gross_taken[target] += amount

    cumulative = {
        "attacker": {"damage_dealt": 0, "damage_taken": 0},
        "defender": {"damage_dealt": 0, "damage_taken": 0},
    }
    for row in sorted(result.get("rounds", []), key=lambda value: int(value.get("round", 0))):
        number = int(row.get("round", 0))
        stats = round_stats(number)
        row_combat: dict[str, dict[str, int | None]] = {}
        for side in ("attacker", "defender"):
            cumulative[side]["damage_dealt"] += stats[side]["damage_dealt"]
            cumulative[side]["damage_taken"] += stats[side]["damage_taken"]
            support_round = healing_reach_round[side]
            healing_unknown = support_round is not None and number >= support_round
            if scenario.policy == Policy.STRICT and _strict_support_boundary_reached(
                    scenario, result, side, "doctor", "UNKNOWN-HEALING-ALLOCATION"):
                healing_unknown = True
            row_combat[side] = {
                "damage_dealt": stats[side]["damage_dealt"],
                "damage_taken": stats[side]["damage_taken"],
                "cumulative_damage_dealt": cumulative[side]["damage_dealt"],
                "cumulative_damage_taken": cumulative[side]["damage_taken"],
                "healing": None if healing_unknown else 0,
                "cumulative_healing": None if healing_unknown else 0,
            }
        row["combat_statistics"] = row_combat

    result["combat_statistics"] = {
        side: {
            "gross_damage_dealt": gross_dealt[side],
            "gross_damage_taken": gross_taken[side],
            "gross_healing": None if (
                healing_reach_round[side] is not None
                or _strict_support_boundary_reached(
                    scenario, result, side, "doctor", "UNKNOWN-HEALING-ALLOCATION")
            ) else 0,
        }
        for side in ("attacker", "defender")
    }
    result["healing_status"] = healing_status
    result["morale_status"] = _morale_status(scenario, result)
    return result

def simulate(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    normalized = Scenario.from_dict(scenario) if isinstance(scenario, dict) else scenario
    result = _simulate_core(normalized)
    economy = MilitaryEconomyProfile.load(normalized.profiles.economy)
    return _attach_battle_statistics(result, economy, normalized)
