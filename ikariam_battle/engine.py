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
from .models import Army, Policy, Scenario, ScenarioError, Slot, Wave
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
    "EXP-HEAL-NONE-001": "When Doctor capacity cannot clear all eligible Human persistent damage at a round boundary, do not apply partial healing because allocation and exact Healing/RR ordering are unresolved.",
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
                try:
                    select_active_weapon(unit, runtime_line)
                except UnsupportedWeaponSelection:
                    if unit.semantic_class == "light_infantry":
                        blockers.append("UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT")
    return blockers


def _guard_single_line_waves(waves: list[Wave]) -> None:
    """Prevent structurally valid, but uncalibrated, multi-line execution."""
    if any(len({slot.line for slot in wave.slots}) > 1 for wave in waves):
        raise ScenarioError("UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS")


def _apply_supported_doctor_healing(
    waves: list[Wave], registry: UnitRegistry, support: SupportProfile,
    events: list[Event], number: int, side: str,
    applied: dict[str, dict[str, str]],
) -> int:
    """Apply the order-invariant exact subset of Doctor healing.

    Empirical evidence establishes a per-round heal that is reflected before
    the next round's combat, while current data gives a derived 4000-capacity
    reference per Doctor and Human/Machine eligibility. Exact allocation and
    Healing-vs-RR order remain unresolved.

    Therefore we execute only the case whose result is independent of those
    unknowns: total Doctor capacity covers *all* persistent damage on eligible
    Human combat waves. Every eligible wave is then fully healed before the
    ordinary RR pass; whether the real game heals before or after RR cannot
    change that all-zero result. If capacity is insufficient, Experimental
    continues with the named no-partial-healing assumption instead of inventing
    an allocation priority.
    """
    doctor_count = sum(
        wave.support_units
        for wave in waves
        if wave.unit.unit_id == "doctor" and wave.support_units > 0
    )
    if not doctor_count:
        return 0

    damaged: list[tuple[Wave, int]] = []
    for wave in waves:
        if not wave.alive:
            continue
        unit = registry.get(wave.unit.unit_id)
        if unit.role != "combat" or unit.unit_class != "human":
            continue
        total_damage = wave.reserve_damage + sum(slot.damage for slot in wave.slots)
        if total_damage > 0:
            damaged.append((wave, total_damage))

    eligible_damage = sum(total for _, total in damaged)
    if not eligible_damage:
        return 0

    capacity = doctor_count * support.derived_capacity
    if capacity < eligible_damage:
        _assume(applied, events, "EXP-HEAL-NONE-001", number, "heal", side)
        _event(
            events, number, "heal", "healing_allocation_unresolved", side,
            doctor_count=doctor_count, capacity=capacity,
            eligible_damage=eligible_damage,
            unresolved_damage=eligible_damage,
            rule_id="UNKNOWN-HEALING-ALLOCATION",
            action="no_partial_healing_applied",
        )
        return 0

    by_wave: list[dict[str, Any]] = []
    by_unit: dict[str, int] = defaultdict(int)
    for wave, total_damage in damaged:
        by_wave.append({
            "unit_id": wave.unit.unit_id,
            "wave_id": wave.unit.wave_id,
            "healing": total_damage,
        })
        by_unit[wave.unit.unit_id] += total_damage
        wave.reserve_damage = 0
        for slot in wave.slots:
            slot.damage = 0

    _event(
        events, number, "heal", "healing", side,
        doctor_count=doctor_count, capacity=capacity,
        eligible_damage_before=eligible_damage,
        healing=eligible_damage,
        unused_capacity=capacity - eligible_damage,
        affected_waves=sorted(
            by_wave, key=lambda item: (item["unit_id"], item["wave_id"])
        ),
        affected_units=dict(sorted(by_unit.items())),
        eligibility="land_human_combat",
        timing="round_boundary_before_next_combat",
        exact_subset="capacity_covers_all_eligible_persistent_damage",
        healing_rr_order="order_invariant_for_full_clear",
    )
    return eligible_damage


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


def _supported_same_batch_heavy_first_handoffs(
    waves: list[Wave], registry: UnitRegistry, rules: FormationRules, field,
    events: list[Event], number: int, side: str,
) -> None:
    """Center-pack same-entry-batch Heavy Infantry across existing First slots.

    Same-wave rebuild runs first. This second, deliberately narrow pass then
    treats Heavy Infantry waves from one entry batch as one First-line formation
    for physical placement only: earlier waves keep precedence, a partial earlier
    wave keeps its own slot, and later Heavy Infantry may take ownership of the
    next center-first slots. No new physical slot, cross-batch move, cross-line
    move, or Light-Infantry fallback is inferred here.

    Persistent damage remains owned by its concrete unit-state wave. Because
    ownership may move between physical slots, each participating wave's total
    damage is preserved temporarily on Reserve and RR immediately redistributes
    it over the final deployment.
    """
    geometry = field.lines.get("first")
    if geometry is None:
        return

    groups: dict[str, list[Wave]] = defaultdict(list)
    for wave in waves:
        unit = registry.get(wave.unit.unit_id)
        if (
            unit.role == "combat"
            and unit.semantic_class == "heavy_infantry"
            and "first" in eligible_runtime_lines(unit, rules, field)
        ):
            groups[wave.unit.batch_id].append(wave)

    for batch_id, group in groups.items():
        if len(group) < 2:
            continue

        owners: dict[int, tuple[Wave, Slot]] = {}
        for wave in group:
            for slot in wave.slots:
                if slot.line != "first":
                    continue
                if slot.damage_position in owners:
                    raise ScenarioError(
                        f"duplicate First-line ownership at damage position "
                        f"{slot.damage_position} in entry batch {batch_id}"
                    )
                owners[slot.damage_position] = (wave, slot)
        if not owners:
            continue

        positions = [
            position for position in geometry.damage_priority
            if position in owners
        ]
        totals: dict[tuple[str, str], int] = {}
        damage_totals: dict[tuple[str, str], int] = {}
        for wave in group:
            key = (wave.unit.unit_id, wave.unit.wave_id)
            totals[key] = wave.reserve + sum(
                slot.units for slot in wave.slots if slot.line == "first"
            )
            damage_totals[key] = wave.reserve_damage + sum(
                slot.damage for slot in wave.slots
            )

        desired: dict[int, tuple[Wave, int, int]] = {}
        for wave in group:
            key = (wave.unit.unit_id, wave.unit.wave_id)
            remaining = totals[key]
            unit = registry.get(wave.unit.unit_id)
            capacity = geometry.slot_space // unit.size
            if capacity <= 0:
                continue
            for position in positions:
                if not remaining:
                    break
                if position in desired:
                    continue
                quantity = min(remaining, capacity)
                desired[position] = (wave, quantity, capacity)
                remaining -= quantity
            wave.reserve = remaining

        # Ownership changes below may remove a damaged slot from one wave and
        # recreate it for another. Preserve per-wave damage before that mutation;
        # _redistribute() immediately reapportions it after this function returns.
        for wave in group:
            key = (wave.unit.unit_id, wave.unit.wave_id)
            wave.reserve_damage = damage_totals[key]
            for slot in wave.slots:
                slot.damage = 0

        for position in positions:
            previous_wave, previous_slot = owners[position]
            assignment = desired.get(position)
            if assignment is None:
                prior = previous_slot.units
                previous_slot.units = 0
                previous_slot.damage = 0
                if prior:
                    _event(
                        events, number, "deploy", "slot_repacked", side,
                        slot_id=previous_slot.slot_id,
                        damage_position=position,
                        previous_units=prior, units=0,
                        reason="same_batch_heavy_front_compaction",
                    )
                continue

            target_wave, quantity, capacity = assignment
            if previous_wave is target_wave:
                prior = previous_slot.units
                previous_slot.units = quantity
                previous_slot.capacity = capacity
                previous_slot.damage = 0
                if prior != quantity:
                    _event(
                        events, number, "deploy", "slot_repacked", side,
                        slot_id=previous_slot.slot_id,
                        damage_position=position,
                        previous_units=prior, units=quantity,
                        reason="same_batch_heavy_front_compaction",
                    )
                continue

            previous_unit = registry.get(previous_wave.unit.unit_id)
            target_unit = registry.get(target_wave.unit.unit_id)
            previous_wave.slots.remove(previous_slot)
            slot = Slot(
                f"first-{position}", "first",
                geometry.physical_position(position), position,
                target_unit.id, target_wave.unit.wave_id, quantity, capacity,
            )
            target_wave.slots.append(slot)
            owners[position] = (target_wave, slot)
            _event(
                events, number, "deploy", "slot_handoff", side,
                line="first", damage_position=position,
                physical_position=slot.physical_position,
                from_unit_id=previous_unit.id,
                from_wave_id=previous_wave.unit.wave_id,
                to_unit_id=target_unit.id,
                to_wave_id=target_wave.unit.wave_id,
                entry_batch_id=batch_id,
                quantity=quantity, capacity=capacity,
                reason="same_batch_heavy_front_replacement",
                compaction=True,
            )

        for wave in group:
            wave.slots.sort(key=lambda slot: (slot.line, slot.damage_position))


def _supported_same_unit_same_line_handoffs(
    waves: list[Wave], registry: UnitRegistry, rules: FormationRules, field,
    events: list[Event], number: int, side: str,
) -> None:
    """Compact same-unit waves across their already-owned runtime-line slots.

    Different entry batches of the same unit may replace each other on the same
    runtime line without sharing wave state. Existing physical slots are reused
    center-first, earlier waves keep precedence, and one physical slot never
    mixes waves. Ammo, persistent damage, Workshop state, and wave identity stay
    attached to the concrete wave.

    Reserve-only waves join only their native runtime line. This deliberately
    does not infer Light-Infantry fallback, cross-line placement, a different
    unit type taking ownership, or creation of new physical slots.
    """
    _guard_single_line_waves(waves)

    groups: dict[tuple[str, str], list[Wave]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()

    # Existing slot ownership defines which physical runtime-line positions are
    # available to this narrow cross-wave compaction.
    for wave in waves:
        if not wave.slots:
            continue
        lines = {slot.line for slot in wave.slots}
        if len(lines) != 1:
            continue
        runtime_line = next(iter(lines))
        key = (wave.unit.unit_id, runtime_line)
        groups[key].append(wave)
        seen.add((wave.unit.unit_id, wave.unit.wave_id, runtime_line))

    # A reserve-only wave may continue the same unit's native line when that
    # line already exists. We do not use fallback eligibility to guess a line.
    for wave in waves:
        if wave.slots or not wave.reserve:
            continue
        unit = registry.get(wave.unit.unit_id)
        runtime_line = unit.native_line
        key = (unit.id, runtime_line)
        identity = (unit.id, wave.unit.wave_id, runtime_line)
        if (
            key in groups
            and identity not in seen
            and runtime_line in eligible_runtime_lines(unit, rules, field)
        ):
            groups[key].append(wave)
            seen.add(identity)

    for (unit_id, runtime_line), group in groups.items():
        if len(group) < 2:
            continue
        geometry = field.lines.get(runtime_line)
        if geometry is None:
            continue

        group.sort(key=lambda wave: wave.unit.formation_order_key)

        owners: dict[int, tuple[Wave, Slot]] = {}
        for wave in group:
            for slot in wave.slots:
                if slot.line != runtime_line:
                    continue
                if slot.damage_position in owners:
                    raise ScenarioError(
                        f"duplicate {runtime_line} ownership at damage position "
                        f"{slot.damage_position} for unit {unit_id}"
                    )
                owners[slot.damage_position] = (wave, slot)
        if not owners:
            continue

        positions = [
            position for position in geometry.damage_priority
            if position in owners
        ]
        unit = registry.get(unit_id)
        capacity = geometry.slot_space // unit.size
        if capacity <= 0:
            continue

        totals: dict[str, int] = {}
        damage_totals: dict[str, int] = {}
        for wave in group:
            totals[wave.unit.wave_id] = wave.reserve + sum(
                slot.units for slot in wave.slots
                if slot.line == runtime_line
            )
            damage_totals[wave.unit.wave_id] = (
                wave.reserve_damage + sum(slot.damage for slot in wave.slots)
            )

        desired: dict[int, tuple[Wave, int]] = {}
        for wave in group:
            remaining = totals[wave.unit.wave_id]
            for position in positions:
                if not remaining:
                    break
                if position in desired:
                    continue
                quantity = min(remaining, capacity)
                desired[position] = (wave, quantity)
                remaining -= quantity
            wave.reserve = remaining

        # Ownership may move across waves; keep each wave's damage total intact
        # and let RR redistribute it over that wave's final slots immediately
        # after all supported compactions finish.
        for wave in group:
            wave.reserve_damage = damage_totals[wave.unit.wave_id]
            for slot in wave.slots:
                slot.damage = 0

        for position in positions:
            previous_wave, previous_slot = owners[position]
            assignment = desired.get(position)
            if assignment is None:
                prior = previous_slot.units
                previous_slot.units = 0
                previous_slot.damage = 0
                if prior:
                    _event(
                        events, number, "deploy", "slot_repacked", side,
                        slot_id=previous_slot.slot_id,
                        damage_position=position,
                        previous_units=prior, units=0,
                        reason="same_unit_same_line_compaction",
                    )
                continue

            target_wave, quantity = assignment
            if previous_wave is target_wave:
                prior = previous_slot.units
                previous_slot.units = quantity
                previous_slot.capacity = capacity
                previous_slot.damage = 0
                if prior != quantity:
                    _event(
                        events, number, "deploy", "slot_repacked", side,
                        slot_id=previous_slot.slot_id,
                        damage_position=position,
                        previous_units=prior, units=quantity,
                        reason="same_unit_same_line_compaction",
                    )
                continue

            previous_wave.slots.remove(previous_slot)
            slot = Slot(
                f"{runtime_line}-{position}", runtime_line,
                geometry.physical_position(position), position,
                unit.id, target_wave.unit.wave_id, quantity, capacity,
            )
            target_wave.slots.append(slot)
            owners[position] = (target_wave, slot)
            _event(
                events, number, "deploy", "slot_handoff", side,
                line=runtime_line, damage_position=position,
                physical_position=slot.physical_position,
                from_unit_id=unit.id,
                from_wave_id=previous_wave.unit.wave_id,
                to_unit_id=unit.id,
                to_wave_id=target_wave.unit.wave_id,
                from_entry_batch_id=previous_wave.unit.batch_id,
                entry_batch_id=target_wave.unit.batch_id,
                quantity=quantity, capacity=capacity,
                reason="same_unit_same_line_wave_replacement",
                compaction=True,
            )

        for wave in group:
            wave.slots.sort(key=lambda slot: (slot.line, slot.damage_position))


def _supported_whole_wave_light_first_fallback(
    waves: list[Wave], registry: UnitRegistry, rules: FormationRules, field,
    events: list[Event], number: int, side: str,
) -> None:
    """Move one whole native Light Infantry wave into open First slots.

    The in-game formation rule gives First-line placement precedence over Flank.
    This executable subset is deliberately narrow: the surviving wave must fit
    completely into currently open First slots, so the wave never spans First
    and Flank at the same time. Partial cross-line splitting remains guarded by
    UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS.

    Persistent damage stays wave-owned. It is parked on reserve_damage while
    slots are rebuilt, then the existing RR pass redistributes it over the new
    single-line placement.
    """
    geometry = field.lines.get("first")
    if geometry is None:
        return

    occupied = {
        slot.damage_position
        for wave in waves
        for slot in wave.slots
        if slot.line == "first" and slot.units
    }
    first_owners = {
        slot.damage_position: (wave, slot)
        for wave in waves
        for slot in wave.slots
        if slot.line == "first"
    }

    candidates = sorted(waves, key=lambda wave: wave.unit.formation_order_key)
    for wave in candidates:
        unit = registry.get(wave.unit.unit_id)
        if (
            unit.role != "combat"
            or unit.semantic_class != "light_infantry"
            or unit.native_line == "first"
            or "first" not in eligible_runtime_lines(unit, rules, field)
            or not wave.alive
        ):
            continue

        live_lines = {slot.line for slot in wave.slots if slot.units}
        # This exact fallback subset starts from an already deployed native
        # Light formation. A wholly reserve-only wave still belongs behind the
        # cross-wave rebuild boundary and must not materialize in First here.
        if live_lines != {unit.native_line}:
            continue

        total_units = wave.reserve + sum(slot.units for slot in wave.slots)
        capacity = geometry.slot_space // unit.size
        if total_units <= 0 or capacity <= 0:
            continue
        open_positions = [
            position for position in geometry.damage_priority
            if position not in occupied
        ]
        required_slots = (total_units + capacity - 1) // capacity
        if required_slots > len(open_positions):
            # Supporting this case would split one state wave across First and
            # Flank. Keep that separate evidence/RR boundary explicit. Do not
            # let a later Light wave leapfrog this canonical earlier wave.
            break

        source_lines = sorted({slot.line for slot in wave.slots if slot.units})
        total_damage = wave.reserve_damage + sum(slot.damage for slot in wave.slots)

        # The completed previous-round snapshot already owns old slot casualty
        # history. Round-start fallback creates the next formation cleanly.
        #
        # If later state waves of the *same unit* still occupy the native line,
        # preserve the physical native positions released by this promoted wave.
        # Attach empty ownership shells to the earliest later native peer, then
        # the existing same-unit/same-line compaction pass can refill them
        # center-first without merging wave state or inventing a new slot.
        released_native_slots = [
            slot for slot in wave.slots if slot.line == unit.native_line
        ]
        later_native_peers = [
            peer for peer in candidates
            if peer is not wave
            and peer.unit.unit_id == wave.unit.unit_id
            and peer.unit.formation_order_key > wave.unit.formation_order_key
            and (
                peer.reserve > 0
                or any(slot.line == unit.native_line for slot in peer.slots)
            )
            and len({slot.line for slot in peer.slots if slot.units}) <= 1
        ]
        for slot in list(wave.slots):
            wave.slots.remove(slot)
        if released_native_slots and later_native_peers:
            peer = later_native_peers[0]
            owned = {slot.damage_position for slot in peer.slots
                     if slot.line == unit.native_line}
            for released in released_native_slots:
                if released.damage_position in owned:
                    continue
                peer.slots.append(Slot(
                    f"{unit.native_line}-{released.damage_position}",
                    unit.native_line,
                    released.physical_position,
                    released.damage_position,
                    unit.id,
                    peer.unit.wave_id,
                    0,
                    released.capacity,
                    0,
                ))
                owned.add(released.damage_position)
            peer.slots.sort(key=lambda slot: (slot.line, slot.damage_position))
        wave.reserve = 0
        wave.reserve_damage = total_damage

        remaining = total_units
        positions_used: list[int] = []
        for position in open_positions[:required_slots]:
            previous = first_owners.get(position)
            if previous is not None:
                previous_wave, previous_slot = previous
                if previous_slot in previous_wave.slots and not previous_slot.units:
                    # Empty physical slots may still carry persistent damage
                    # owned by their previous unit-state wave. Replacing the
                    # slot must not discard that damage; park it on the owning
                    # wave so the ordinary RR pass can redistribute it after
                    # the new formation is complete.
                    previous_wave.reserve_damage += previous_slot.damage
                    previous_slot.damage = 0
                    previous_wave.slots.remove(previous_slot)

            quantity = min(capacity, remaining)
            slot = Slot(
                f"first-{position}", "first",
                geometry.physical_position(position), position,
                unit.id, wave.unit.wave_id, quantity, capacity,
            )
            wave.slots.append(slot)
            occupied.add(position)
            first_owners[position] = (wave, slot)
            positions_used.append(position)
            remaining -= quantity

        if remaining:
            raise ScenarioError("whole-wave Light Infantry fallback left unexpected reserve")
        wave.slots.sort(key=lambda slot: (slot.line, slot.damage_position))
        _event(
            events, number, "deploy", "formation_fallback", side,
            unit_id=unit.id, wave_id=wave.unit.wave_id,
            entry_batch_id=wave.unit.batch_id,
            from_lines=source_lines or [unit.native_line], to_line="first",
            quantity=total_units, damage_positions=positions_used,
            rule="first_before_flank_whole_wave_light_fallback",
            whole_wave=True,
        )


def _has_supported_round_start_first_placement(
    waves: list[Wave], registry: UnitRegistry, rules: FormationRules, field,
) -> bool:
    """Whether supported round-start placement can restore the First line."""
    projected = deepcopy(waves)
    projection_events: list[Event] = []
    _rebuild_formation(projected, projection_events, 0, "projection")
    _supported_same_batch_heavy_first_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")
    _supported_same_unit_same_line_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")
    _supported_whole_wave_light_first_fallback(
        projected, registry, rules, field, projection_events, 0, "projection")
    _rebuild_formation(projected, projection_events, 0, "projection")
    _supported_same_unit_same_line_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")
    return any(
        slot.line == "first" and slot.units
        for wave in projected
        for slot in wave.slots
    )


def _prepare_round_start(
    waves: list[Wave], events: list[Event], number: int, side: str,
    applied: dict[str, dict[str, str]], registry: UnitRegistry | None = None,
    rules: FormationRules | None = None, field=None,
    support: SupportProfile | None = None,
) -> None:
    """Re-pack, apply safe Doctor healing when exact, then RR persistent damage."""
    _rebuild_formation(waves, events, number, side)
    if registry is not None and rules is not None and field is not None:
        _supported_same_batch_heavy_first_handoffs(
            waves, registry, rules, field, events, number, side)
        _supported_same_unit_same_line_handoffs(
            waves, registry, rules, field, events, number, side)
        _supported_whole_wave_light_first_fallback(
            waves, registry, rules, field, events, number, side)
        # Whole-wave promotion can vacate native-line physical positions that
        # a later same-unit wave is allowed to inherit. First re-pack each
        # concrete wave across its inherited slots, then run the already
        # supported same-unit/same-line cross-wave compaction.
        _rebuild_formation(waves, events, number, side)
        _supported_same_unit_same_line_handoffs(
            waves, registry, rules, field, events, number, side)
    if registry is not None and support is not None:
        _apply_supported_doctor_healing(
            waves, registry, support, events, number, side, applied)
    # RR must see the final deployment after every supported compaction. The
    # healing subset above is intentionally limited to full-clear cases, so the
    # unknown Healing/RR order cannot alter its result.
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
    """Return cross-wave placements still unsupported after exact supported projection.

    The projection reuses the same round-start formation code as execution on a
    deep copy. This prevents the safety guard from drifting behind supported
    same-wave refill, same-batch mixed-Heavy compaction, or same-unit same-line
    replacement across entry batches.
    """
    projected = deepcopy(waves)
    projection_events: list[Event] = []
    _rebuild_formation(projected, projection_events, 0, "projection")
    _supported_same_batch_heavy_first_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")
    _supported_same_unit_same_line_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")
    _supported_whole_wave_light_first_fallback(
        projected, registry, rules, field, projection_events, 0, "projection")
    _rebuild_formation(projected, projection_events, 0, "projection")
    _supported_same_unit_same_line_handoffs(
        projected, registry, rules, field, projection_events, 0, "projection")

    occupied: dict[str, set[int]] = defaultdict(set)
    for wave in projected:
        for slot in wave.slots:
            if slot.units:
                occupied[slot.line].add(slot.damage_position)

    requirements: list[dict[str, Any]] = []
    for wave in projected:
        # A wave that already owns slots has a supported same-wave path. A
        # reserve-only wave reaches this boundary only when the supported
        # compactions above still cannot place it.
        if not wave.reserve or wave.slots:
            continue
        unit = registry.get(wave.unit.unit_id)
        if unit.role != "combat":
            continue
        for runtime_line in eligible_runtime_lines(unit, rules, field):
            geometry = field.lines.get(runtime_line)
            if geometry is None:
                continue
            open_positions = [
                position for position in geometry.damage_priority
                if position not in occupied[runtime_line]
            ]
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


def _target_waves_for_line(source_line: str, targets: list[Wave], registry: UnitRegistry,
                           targeting: TargetingProfile) -> tuple[list[Wave], str | None]:
    """Return every deployed wave in the highest-priority target formation."""
    _guard_single_line_waves(targets)
    for target_line in targeting.priorities[source_line]:
        choices = [w for w in _combat_waves(targets, registry)
                   if _runtime_line(w, registry) == target_line
                   and any(slot.units > 0 for slot in w.slots)]
        if choices:
            return choices, target_line
    return [], None


def _target_for_line(source_line: str, targets: list[Wave], registry: UnitRegistry,
                     targeting: TargetingProfile) -> tuple[Wave | None, str | None]:
    """Compatibility view for callers that require a unique target wave."""
    choices, target_line = _target_waves_for_line(
        source_line, targets, registry, targeting)
    if len(choices) == 1:
        return choices[0], target_line
    return None, target_line


def _target(source: Wave, targets: list[Wave], registry: UnitRegistry,
            targeting: TargetingProfile) -> tuple[Wave | None, str | None]:
    return _target_for_line(_runtime_line(source, registry), targets, registry, targeting)


def _shot_rows(firing_counts: list[int]) -> list[int]:
    """Expand an Am source into individual shots while preserving row order."""
    return [row
            for row in range(1, max(firing_counts, default=0) + 1)
            for _ in range(sum(count >= row for count in firing_counts))]


def _shot_source_positions(deployed: list[Slot], firing_counts: list[int]) -> list[int]:
    """Return the concrete source-slot column for every row-ordered Am shot."""
    return [slot.damage_position
            for row in range(1, max(firing_counts, default=0) + 1)
            for slot, count in zip(deployed, firing_counts)
            if count >= row]


def _formation_shots(volleys: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Merge mixed source waves into one row-major Attacking Matrix sequence.

    Each volley still owns its weapon, upgrades and ammunition pool. The AM row
    is shared by the runtime formation, while source damage position is the
    deterministic column order. Legacy/internal volleys without additive source
    positions retain their historical explicit sequence.
    """
    prepared: list[tuple[list[int], list[int]]] = []
    for volley in volleys:
        rows = list(volley.get("row_numbers", ()))
        positions = volley.get("source_damage_positions")
        if not isinstance(positions, list) or len(positions) != len(rows):
            return [(volley_index, row)
                    for volley_index, item in enumerate(volleys)
                    for row in item.get("row_numbers", ())]
        prepared.append((rows, positions))

    ordered: list[tuple[int, int, int, int]] = []
    for volley_index, (rows, positions) in enumerate(prepared):
        for shot_index, (row, position) in enumerate(zip(rows, positions)):
            ordered.append((row, position, volley_index, shot_index))
    ordered.sort()
    return [(volley_index, row) for row, _, volley_index, _ in ordered]


def _snapshot_phase_fire(source: list[Wave], target: list[Wave], registry: UnitRegistry,
                         targeting: TargetingProfile, events: list[Event], number: int,
                         side: str, runtime_line: str,
                         applied: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Freeze firing eligibility for one formation before either side takes damage."""
    volleys: list[dict[str, Any]] = []
    for wave in _combat_waves(source, registry):
        if _runtime_line(wave, registry) != runtime_line or not wave.slots or not wave.alive:
            continue
        enemies, _ = _target_waves_for_line(runtime_line, target, registry, targeting)
        if not enemies:
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
        source_damage_positions = _shot_source_positions(deployed, firing_counts)
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
            "source_damage_positions": source_damage_positions,
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
    contexts: dict[int, dict[str, Any]] = {}
    for volley_index, volley in enumerate(volleys):
        if not volley["row_numbers"]:
            continue
        _assume(applied, events, "EXP-D-KILL-SEQUENTIAL-001", number, "fire")
        _assume(applied, events, "EXP-IR-DISABLED-001", number, "fire")
        source_unit = registry.get(volley["source_unit"])
        weapon = next(item for item in source_unit.weapons if item.id == volley["weapon_id"])
        contexts[volley_index] = {
            "volley": volley,
            "source_unit": source_unit,
            "weapon": weapon,
            "matrix_groups": {},
            "damage_groups": {},
            "calculation_keys": set(),
        }

    # One target address book belongs to the whole runtime formation phase, not
    # to one source unit. This is required when different unit types occupy
    # different columns of the same Attacking Matrix.
    address_books: dict[str, tuple[Any, ...]] = {}

    for volley_index, row_number in _formation_shots(volleys):
        context = contexts.get(volley_index)
        if context is None:
            continue
        volley = context["volley"]
        source_unit = context["source_unit"]
        weapon = context["weapon"]
        matrix_groups = context["matrix_groups"]
        damage_groups = context["damage_groups"]
        calculation_keys = context["calculation_keys"]

        enemies, target_class = _target_waves_for_line(
            volley["runtime_line"], targets, registry, targeting)
        if not enemies or target_class is None:
            break

        if target_class not in address_books:
            addressed_slots = []
            for enemy in enemies:
                addressed_slots.extend(
                    (slot.damage_position, enemy, slot)
                    for slot in enemy.slots if slot.units
                )
            address_books[target_class] = tuple(
                sorted(addressed_slots, key=lambda item: (
                    item[0], item[1].unit.unit_id, item[1].unit.wave_id)))
        addressed = address_books[target_class]
        if not addressed:
            continue
        _, enemy, target_slot = addressed[(row_number - 1) % len(addressed)]

        matrix_key = (enemy.unit.unit_id, enemy.unit.wave_id, target_class)
        matrix = matrix_groups.setdefault(matrix_key, {
            "target_unit_id": enemy.unit.unit_id,
            "target_wave": enemy.unit.wave_id,
            "target_class": target_class,
            "rows": defaultdict(int),
            "hits": defaultdict(int),
            "empty_hits": defaultdict(int),
            "formation_positions": {
                slot.damage_position for _, _, slot in addressed
            },
            "wave_positions": {
                slot.damage_position
                for _, addressed_enemy, slot in addressed
                if (
                    addressed_enemy.unit.unit_id == enemy.unit.unit_id
                    and addressed_enemy.unit.wave_id == enemy.unit.wave_id
                )
            },
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
            "_persistent_damage": target_slot.damage,
        })
        group["damage"] += damage_trace.final_damage
        group["firing_units"] += 1
        group["casualties"] += killed
        group["overkill_discarded"] += overkill
        group["_persistent_damage"] = target_slot.damage

        if _ir_trigger(volley, enemy, target_slot, row_number):
            _rebalance_damage_queue(queue)
            target_slot.damage = sum(queue)
            group["_persistent_damage"] = target_slot.damage

    for volley_index in sorted(contexts):
        context = contexts[volley_index]
        volley = context["volley"]
        source_unit = context["source_unit"]
        weapon = context["weapon"]
        for matrix in context["matrix_groups"].values():
            max_row = max(matrix["rows"], default=0)
            _event(events, number, "fire", "attacking_matrix", volley["side"],
                   firing_phase=volley["runtime_line"], unit_id=source_unit.id,
                   target_unit_id=matrix["target_unit_id"],
                   target_wave=matrix["target_wave"],
                   target_class=matrix["target_class"], weapon_id=weapon.id,
                   targeting_authority="GAMEFORGE_IN_GAME_HELP",
                   trace={
                       "row_populations": [matrix["rows"].get(row, 0)
                                           for row in range(1, max_row + 1)],
                       "target_damage_positions": sorted(matrix["wave_positions"]),
                       "formation_target_damage_positions": sorted(
                           matrix["formation_positions"]),
                       "hits_by_damage_position": dict(matrix["hits"]),
                       "empty_addressed_shots_by_damage_position": dict(matrix["empty_hits"]),
                   })
        for group in context["damage_groups"].values():
            details = {key: value for key, value in group.items()
                       if key != "_persistent_damage"}
            _event(events, number, "fire", "damage", volley["side"],
                   firing_phase=volley["runtime_line"],
                   target_side="defender" if volley["side"] == "attacker" else "attacker",
                   source_unit_id=source_unit.id,
                   resolution="sequential_d_kill_baseline",
                   persistent_damage=group["_persistent_damage"],
                   assumption_ids=["EXP-D-KILL-SEQUENTIAL-001", "EXP-IR-DISABLED-001"],
                   **details)

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


def _pending_sustaining_arrivals(army: Army, after_round: int, registry: UnitRegistry,
                                 battle_end: BattleEndProfile) -> list[dict[str, Any]]:
    """Future arrivals that could participate in battle-end continuation.

    This is intentionally used only before an engagement has started. Once both
    sides have reached a battle-sustaining state, normal round-boundary battle
    termination remains authoritative; later reinforcements do not retroactively
    keep an already-started battle alive.
    """
    sustaining_lines = battle_end.main_line_classes | battle_end.fallback_candidate_classes
    pending: list[dict[str, Any]] = []
    for item in army.units:
        if item.quantity <= 0 or item.arrival_round <= after_round:
            continue
        unit = registry.get(item.unit_id)
        if unit.role != "combat" or unit.native_line not in sustaining_lines:
            continue
        pending.append({
            "unit_id": unit.id,
            "quantity": item.quantity,
            "entry_batch_id": item.batch_id,
            "wave_id": item.wave_id,
            "arrival_round": item.arrival_round,
        })
    return sorted(pending, key=lambda row: (
        row["arrival_round"], row["entry_batch_id"], row["unit_id"], row["wave_id"]))


def _non_sustaining(snapshot: dict[str, Any]) -> dict[str, int]:
    sustaining = {**snapshot["main_line_holding_remaining"], **snapshot["fallback_candidate_remaining"]}
    return {unit: count for unit, count in snapshot["remaining"].items()
            if count and unit not in sustaining}


def _validate_army_package(army: Army, registry: UnitRegistry, field) -> None:
    """Enforce army-package invariants for dict and typed Scenario callers."""
    if not isinstance(army.army_kind, str) or army.army_kind not in {"player", "barbarian"}:
        raise ScenarioError("army_kind must be player or barbarian")
    active = [item for item in army.units if item.quantity]
    if army.army_kind == "barbarian":
        if army.forge_level != 0:
            raise ScenarioError("barbarian armies do not use Forge levels")
        if any(item.attack_upgrade or item.armor_upgrade for item in active):
            raise ScenarioError("barbarian armies do not use Workshop upgrades")
        if any(item.arrival_round != 0 for item in active):
            raise ScenarioError("barbarian armies do not use delayed entry batches")
        if len({item.batch_id for item in active}) != 1:
            raise ScenarioError("barbarian armies use one fixed entry batch")
        waves_by_unit: dict[str, set[str]] = {}
        for item in active:
            waves_by_unit.setdefault(item.unit_id, set()).add(item.wave_id)
        if any(len(waves) != 1 for waves in waves_by_unit.values()):
            raise ScenarioError("barbarian unit types cannot be split across waves")

    for item in army.units:
        unit = registry.get(item.unit_id)
        if unit.army_kind != army.army_kind:
            raise ScenarioError(
                f"{unit.id} belongs to the {unit.army_kind} army package, "
                f"not {army.army_kind}"
            )
        if unit.domain != field.domain:
            raise ScenarioError(f"{unit.id} is {unit.domain} and cannot enter {field.id}")
        if unit.role != "support" and not unit.numerically_supported:
            raise ScenarioError(f"{unit.id} has unverified numerical fields and cannot be simulated")


def _simulate_core(scenario: Scenario | dict[str, Any]) -> dict[str, Any]:
    if isinstance(scenario, dict): scenario = Scenario.from_dict(scenario)
    registry = UnitRegistry.load(scenario.profiles.unit_stats, include_barbarians=True)
    field = battlefield(scenario.battlefield)
    formation_rules = FormationRules.load(scenario.profiles.formation)
    battle_end = BattleEndProfile.load(scenario.profiles.battle_end)
    # Validate every scheduled unit and package invariant now, including
    # callers that bypass dict parsing and pass a typed Scenario directly.
    for army in (scenario.attacker, scenario.defender):
        _validate_army_package(army, registry, field)
    attacker = deploy(Army(tuple(item for item in scenario.attacker.units if item.arrival_round == 0),
                           scenario.attacker.forge_level, scenario.attacker.army_kind),
                      registry, field, scenario.profiles.formation)
    defender = deploy(Army(tuple(item for item in scenario.defender.units if item.arrival_round == 0),
                           scenario.defender.forge_level, scenario.defender.army_kind),
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
    initial_pending = {
        "attacker": _pending_sustaining_arrivals(
            scenario.attacker, 0, registry, battle_end),
        "defender": _pending_sustaining_arrivals(
            scenario.defender, 0, registry, battle_end),
    }
    initial_outcome, initial_losing = _termination(initial["attacker"], initial["defender"])
    initial_waiting = initial_outcome is not None and bool(initial_pending.get(initial_losing or ""))
    both_initially_empty_but_pending = (
        all(state == ContinuationState.NOT_SUSTAINING.value for state in initial_states.values())
        and any(initial_pending.values())
    )
    if fallback_sides:
        blockers.append("UNKNOWN-FORMATION-FALLBACK")
    if initial_outcome is not None and not initial_waiting:
        blockers.append("UNKNOWN-INITIAL-BATTLE-END-TIMING")
    if (all(state == ContinuationState.NOT_SUSTAINING.value for state in initial_states.values())
            and not both_initially_empty_but_pending):
        blockers.append("UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
    if scenario.policy is Policy.STRICT:
        blockers += ["UNKNOWN-KILL-SELECTION", "UNKNOWN-ROUNDING-SELECTOR",
                     "UNKNOWN-ACCURACY", "UNKNOWN-IR-TRIGGER", "UNKNOWN-SR-TRIGGER"]
        return _unsupported(scenario, events, initial, sorted(set(blockers)), warnings)
    if {"UNKNOWN-MULTIPLE-TARGET-WAVES",
        "UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS",
        "UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT"} & set(blockers):
        return _unsupported(scenario, events, initial, blockers, warnings)
    applied: dict[str, dict[str, str]] = {}
    for side, side_blockers in (("attacker", attacker_blockers), ("defender", defender_blockers)):
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
    if (all(state == ContinuationState.NOT_SUSTAINING.value for state in initial_states.values())
            and not both_initially_empty_but_pending):
        _event(events, 0, "battle_end", "unsupported_mechanic", None,
               rule_id="UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
        return {"profiles":scenario.profiles.__dict__,"policy":scenario.policy.value,"status":"inconclusive",
                "outcome":"inconclusive","rounds_completed":0,"casualties":{"attacker":{},"defender":{}},
                "initial_state":initial,"final_state":initial,
                "rounds":[{"round":0,**deepcopy(initial),"casualties":{"attacker":{},"defender":{}}}],
                "events":[e.as_dict() for e in events],"assumptions":list(applied.values()),"warnings":warnings}
    if both_initially_empty_but_pending:
        pending_sides = [side for side, rows in initial_pending.items() if rows]
        _event(events, 0, "battle_start", "waiting_for_arrival", None,
               pending_sides=pending_sides,
               pending={side: initial_pending[side] for side in pending_sides},
               next_arrival_round=min(
                   row["arrival_round"]
                   for side in pending_sides
                   for row in initial_pending[side]))
    elif initial_waiting:
        _event(events, 0, "battle_start", "waiting_for_arrival", initial_losing,
               pending=initial_pending[initial_losing],
               next_arrival_round=min(row["arrival_round"] for row in initial_pending[initial_losing]))
    elif initial_outcome is not None:
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
    support = SupportProfile.load(scenario.profiles.support)
    total = {"attacker": defaultdict(int), "defender": defaultdict(int)}
    rounds = [{"round":0, **deepcopy(initial), "casualties":{"attacker":{},"defender":{}}}]
    completed = 0
    fallback_boundary = False
    both_zero_boundary = False
    cross_wave_boundary = False
    engagement_started = all(
        state == ContinuationState.SUSTAINING.value for state in initial_states.values())
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
            if "UNKNOWN-MORALE-SUPPORT" in side_blockers:
                _assume(applied, events, "EXP-MORALE-NONE-001", number, "arrival", side)
        _prepare_round_start(
            attacker, events, number, "attacker", applied,
            registry, formation_rules, field, support)
        _prepare_round_start(
            defender, events, number, "defender", applied,
            registry, formation_rules, field, support)
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
            # Arrival and same-wave round-start state for this round are already
            # observable even though cross-wave placement cannot continue.
            # Preserve that boundary round for paging/debug export before exit.
            completed = number
            attacker_state = _snapshot(attacker, registry, battle_end)
            defender_state = _snapshot(defender, registry, battle_end)
            rounds.append({
                "round": number,
                "attacker": attacker_state,
                "defender": defender_state,
                "casualties": {"attacker": {}, "defender": {}},
            })
            cross_wave_boundary = True
            break
        round_start_states = {
            "attacker": _snapshot(attacker, registry, battle_end)["continuation_state"],
            "defender": _snapshot(defender, registry, battle_end)["continuation_state"],
        }
        if all(state == ContinuationState.SUSTAINING.value
               for state in round_start_states.values()):
            engagement_started = True
        # Art of Warfare: same formations on both sides shoot simultaneously;
        # casualties from an earlier formation suppress firing in later phases.
        round_had_fire = False
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
            round_had_fire = True
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

        # Combat itself can create the first real vacancy that requires a
        # different reserve-only wave to enter. Recheck before any continuation
        # or termination decision so an unimplemented cross-wave replacement
        # can never be mistaken for an exact battle outcome.
        post_combat_cross_wave = {
            "attacker": _cross_wave_rebuild_requirements(
                attacker, registry, formation_rules, field),
            "defender": _cross_wave_rebuild_requirements(
                defender, registry, formation_rules, field),
        }
        if any(post_combat_cross_wave.values()):
            for side, requirements in post_combat_cross_wave.items():
                if requirements:
                    _event(events, number, "round_end", "unsupported_mechanic", side,
                           rule_id="UNKNOWN-CROSS-WAVE-FORMATION-REBUILD",
                           requirements=requirements)
            cross_wave_boundary = True
            break

        states = {"attacker": attacker_state["continuation_state"],
                  "defender": defender_state["continuation_state"]}
        # Any already-supported round-start placement that can restore First on
        # the next round must keep the battle alive. This includes same-wave
        # refill, same-batch mixed-Heavy compaction, and same-unit same-line
        # replacement across entry batches. Do not mutate the completed snapshot.
        for side, side_waves in (("attacker", attacker), ("defender", defender)):
            if (states[side] != ContinuationState.SUSTAINING.value
                    and _has_supported_round_start_first_placement(
                        side_waves, registry, formation_rules, field)):
                states[side] = ContinuationState.SUSTAINING.value
        effective_attacker_state = dict(attacker_state)
        effective_defender_state = dict(defender_state)
        effective_attacker_state["continuation_state"] = states["attacker"]
        effective_defender_state["continuation_state"] = states["defender"]
        fallback_sides = [side for side, state in states.items()
                          if state == ContinuationState.FALLBACK_REQUIRED.value]
        if fallback_sides:
            _event(events, number, "battle_end", "unsupported_mechanic", None,
                   rule_id="UNKNOWN-FORMATION-FALLBACK", affected_sides=fallback_sides)
            fallback_boundary = True
            break
        pending_now = {
            "attacker": _pending_sustaining_arrivals(
                scenario.attacker, number, registry, battle_end),
            "defender": _pending_sustaining_arrivals(
                scenario.defender, number, registry, battle_end),
        }
        if all(state == ContinuationState.NOT_SUSTAINING.value for state in states.values()):
            if not engagement_started and any(pending_now.values()):
                _event(events, number, "battle_start", "waiting_for_arrival", None,
                       pending_sides=[side for side, rows in pending_now.items() if rows],
                       next_arrival_round=min(
                           row["arrival_round"] for rows in pending_now.values() for row in rows))
            else:
                _event(events, number, "battle_end", "unsupported_mechanic", None,
                       rule_id="UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME")
                both_zero_boundary = True
                break
        outcome, losing = _termination(
            effective_attacker_state, effective_defender_state)
        if outcome is not None:
            losing_pending = pending_now.get(losing or "", [])
            if not engagement_started and losing_pending:
                _event(events, number, "battle_start", "waiting_for_arrival", losing,
                       pending=losing_pending,
                       next_arrival_round=min(row["arrival_round"] for row in losing_pending))
            else:
                _assume(applied, events, "EXP-BATTLE-END-ROUND-BOUNDARY-001", number, "battle_end")
                _event(events, number, "battle_end", "battle_termination", None,
                       reason="no_battle_sustaining_units", losing_side=losing,
                       surviving_non_sustaining={"attacker":_non_sustaining(attacker_state),
                                                 "defender":_non_sustaining(defender_state)})
                break
        if not a_dead and not d_dead and not round_had_fire:
            if not engagement_started and any(pending_now.values()):
                continue
            break
    else:
        _event(events, scenario.max_rounds, "battle_end", "safety_limit_reached", None,
               reason="max_rounds_reached", limit=scenario.max_rounds)
    final = {"attacker":_snapshot(attacker,registry,battle_end),"defender":_snapshot(defender,registry,battle_end)}
    outcome, final_losing = _termination(final["attacker"], final["defender"])
    pending_handoff_after_horizon = {
        "attacker": _has_supported_round_start_first_placement(
            attacker, registry, formation_rules, field),
        "defender": _has_supported_round_start_first_placement(
            defender, registry, formation_rules, field),
    }
    pending_after_horizon = {
        "attacker": _pending_sustaining_arrivals(
            scenario.attacker, scenario.max_rounds, registry, battle_end),
        "defender": _pending_sustaining_arrivals(
            scenario.defender, scenario.max_rounds, registry, battle_end),
    }
    if (fallback_boundary or both_zero_boundary or cross_wave_boundary
            or (final_losing is not None
                and pending_handoff_after_horizon.get(final_losing))
            or (not engagement_started
                and final_losing is not None
                and pending_after_horizon.get(final_losing))):
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
        heal_events = [
            event for event in result.get("events", [])
            if event.get("type") == "healing" and event.get("side") == side
        ]
        applied_amount = sum(
            int(event.get("details", {}).get("healing", 0))
            for event in heal_events
        )
        reach_round = _support_assumption_round(result, assumption_id, side)
        strict_reached = _strict_support_boundary_reached(
            scenario, result, side, "doctor", strict_rule_id)
        if not doctor_count:
            status = "not_present"
            amount: int | None = 0
        elif strict_reached:
            status = "unsupported_boundary"
            amount = None
        elif reach_round is not None:
            status = "partial_allocation_unresolved"
            amount = None
        elif heal_events:
            status = "applied_exact_subset"
            amount = applied_amount
        else:
            status = "not_reached"
            amount = 0
        sides[side] = {
            "doctor_count": doctor_count,
            "status": status,
            "effect_applied": bool(applied_amount),
            "healing_amount": amount,
            "engine_healing_applied": applied_amount,
        }
    return {
        "modeled": False,
        "partial_model": True,
        "model_status": "EXACT_FULL_CLEAR_SUBSET_ONLY",
        "strict_rule_id": strict_rule_id,
        "experimental_assumption_id": assumption_id,
        "derived_capacity_per_doctor": support.derived_capacity,
        "capacity_is_allocation_formula": False,
        "timing_contract": "per_round_before_next_round_combat",
        "healing_rr_order": "UNKNOWN_EXCEPT_FULL_CLEAR_IS_ORDER_INVARIANT",
        "executable_subset": "capacity_covers_all_eligible_human_persistent_damage",
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
        army = scenario.attacker if side == "attacker" else scenario.defender
        if army.army_kind == "barbarian":
            # Barbarian military score is a package-level rule, not part of the
            # player military-economy profile.
            basis_loss = 0
            score_loss = Decimal(0)
        else:
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
    gross_healing_applied = {"attacker": 0, "defender": 0}
    per_round: dict[int, dict[str, dict[str, int]]] = {}

    def round_stats(number: int) -> dict[str, dict[str, int]]:
        return per_round.setdefault(number, {
            "attacker": {"damage_dealt": 0, "damage_taken": 0, "healing": 0},
            "defender": {"damage_dealt": 0, "damage_taken": 0, "healing": 0},
        })

    for row in result.get("rounds", []):
        round_stats(int(row.get("round", 0)))

    for event in result.get("events", []):
        kind = event.get("type")
        number = int(event.get("round", 0))
        if kind == "damage":
            source = event.get("side")
            target = event.get("details", {}).get("target_side")
            if source not in gross_dealt or target not in gross_taken:
                continue
            amount = int(event.get("details", {}).get("damage", 0))
            stats = round_stats(number)
            stats[source]["damage_dealt"] += amount
            stats[target]["damage_taken"] += amount
            gross_dealt[source] += amount
            gross_taken[target] += amount
        elif kind == "healing":
            side = event.get("side")
            if side not in gross_healing_applied:
                continue
            amount = int(event.get("details", {}).get("healing", 0))
            round_stats(number)[side]["healing"] += amount
            gross_healing_applied[side] += amount

    cumulative = {
        "attacker": {"damage_dealt": 0, "damage_taken": 0, "healing": 0},
        "defender": {"damage_dealt": 0, "damage_taken": 0, "healing": 0},
    }
    for row in sorted(result.get("rounds", []), key=lambda value: int(value.get("round", 0))):
        number = int(row.get("round", 0))
        stats = round_stats(number)
        row_combat: dict[str, dict[str, int | None]] = {}
        for side in ("attacker", "defender"):
            cumulative[side]["damage_dealt"] += stats[side]["damage_dealt"]
            cumulative[side]["damage_taken"] += stats[side]["damage_taken"]
            cumulative[side]["healing"] += stats[side]["healing"]
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
                "healing": None if healing_unknown else stats[side]["healing"],
                "cumulative_healing": None if healing_unknown else cumulative[side]["healing"],
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
            ) else gross_healing_applied[side],
            "engine_healing_applied": gross_healing_applied[side],
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
