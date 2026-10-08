"""Land Town Wall deployment constraints, separate from damage/target selection.

The wall has priority over defender First slots. A section breached during
round N becomes fillable from Reserve at the *start of N+1*. Both armies'
Flanks are held in Reserve until the next round after the last section
breaches. Suppressed walls / open-field battles use normal deployment.
"""
from dataclasses import replace
from types import MappingProxyType

from .battlefield import Battlefield, LineGeometry
from .formation import plan_initial_formation
from .models import Army, Slot


def hold_initial_wall_formations(attacker, defender):
    """Reserve initial Flanks on both sides and defender First under active wall.

    Only call if the wall is present, not when the wall is garrison-suppressed.
    Slot ownership is removed entirely: it is not a zero-unit vacancy until
    the next-round wall deployment logic assigns that physical position.
    """
    for side, waves, held in (
        ("attacker", attacker, frozenset({"flank"})),
        ("defender", defender, frozenset({"first", "flank"})),
    ):
        for wave in waves:
            kept = []
            for slot in wave.slots:
                if slot.line in held:
                    if slot.damage:
                        raise ValueError("initial Town Wall hold requires undamaged slots")
                    wave.reserve += slot.units
                else:
                    kept.append(slot)
            wave.slots[:] = kept


def _open_positions(waves, line, geometry, valid_positions):
    owned = {slot.damage_position for wave in waves for slot in wave.slots
             if slot.line == line}
    return tuple(position for position in geometry.physical_order
                 if position in valid_positions and position not in owned)


def deploy_prior_round_wall_vacancies(waves, registry, rules, field, sections,
                                      round_no, side, events, emit):
    """Fill positions that were vacant at this round's *start*.

    Called only once at the round-start boundary after arrivals/refill, and
    before this round's shots. Restrict candidates to native lines, so a
    partially deployed wave cannot be promoted to two runtime lines and
    cross-wave replacement precedence is not fabricated.
    """
    if round_no < 2 or not sections or field.domain != "land":
        return
    intact = {section.damage_position for section in sections if not section.destroyed}
    breached = {section.damage_position for section in sections if section.destroyed}
    available_lines = []
    if side == "defender" and breached:
        available_lines.append(("first", breached, "wall_gap_next_round"))
    if not intact and "flank" in field.lines:
        available_lines.append(("flank", set(field.lines["flank"].damage_priority),
                                "wall_all_breached_previous_round"))
    for line, permitted, reason in available_lines:
        geometry = field.lines[line]
        positions = _open_positions(waves, line, geometry, permitted)
        if not positions:
            continue
        native_candidates = [
            wave for wave in waves if wave.reserve > 0
            and registry.get(wave.unit.unit_id).role == "combat"
            and registry.get(wave.unit.unit_id).native_line == line
            and not any(slot.line != line for slot in wave.slots)
        ]
        if not native_candidates:
            continue
        # A subset geometry keeps original *damage-position identifiers*.
        # Temporary physical indexes are never used for permanent Slots.
        first = field.lines["first"]
        subset_lines = {
            "first": LineGeometry("first", positions if line == "first" else (), first.slot_space)
        }
        if line == "flank":
            subset_lines["flank"] = LineGeometry("flank", positions, geometry.slot_space)
        planning_field = Battlefield(field.id, field.domain,
                                     MappingProxyType(subset_lines), field.provenance)
        units = tuple(replace(wave.unit, quantity=wave.reserve)
                      for wave in native_candidates)
        plan = plan_initial_formation(Army(units), registry, planning_field, rules)
        by_key = {(wave.unit.unit_id, wave.unit.wave_id): wave
                  for wave in native_candidates}
        for placement in plan.placements:
            if placement.runtime_line != line:
                continue
            wave = by_key[(placement.unit_id, placement.wave_id)]
            if placement.quantity > wave.reserve:
                raise ValueError("wall filling cannot exceed held Reserve")
            slot = Slot(f"{line}-{placement.damage_position}", line,
                        geometry.physical_position(placement.damage_position),
                        placement.damage_position, placement.unit_id,
                        placement.wave_id, placement.quantity, placement.capacity)
            wave.slots.append(slot)
            wave.reserve -= placement.quantity
            emit(events, round_no, "deploy", "deployment", side,
                 slot_id=slot.slot_id, line=line,
                 physical_position=slot.physical_position,
                 damage_position=slot.damage_position, unit_id=slot.unit_id,
                 wave_id=slot.wave_id, entry_batch_id=wave.unit.batch_id,
                 arrival_round=wave.unit.arrival_round,
                 quantity=placement.quantity, reserve=wave.reserve,
                 reason=reason)


def wall_cross_wave_requirements(requirements, side, wall_runtime_active):
    """Do not declare deliberately held First/Flank reserves as generic UNKNOWN.

    Dedicated next-round wall filling is responsible for these positions.
    Other lines and unrelated cross-wave requirements retain the existing guard.
    """
    if not wall_runtime_active:
        return requirements
    return [
        requirement for requirement in requirements
        if requirement["runtime_line"] != "flank"
        and not (side == "defender" and requirement["runtime_line"] == "first")
    ]


def wall_safe_round_start_field(field, wall_present, wall_still_intact):
    """Hide Flank from *new* native-line arrivals while any wall remains.

    Existing line geometry never changes and will be used for regular combat.
    This is only the round-start formation helper's eligibility view.
    """
    if not wall_present or not wall_still_intact or "flank" not in field.lines:
        return field
    return Battlefield(field.id, field.domain,
                       MappingProxyType({name: geometry for name, geometry in field.lines.items()
                                         if name != "flank"}), field.provenance)


def defender_has_held_front_reserve(waves, registry):
    return any(
        wave.reserve > 0 and registry.get(wave.unit.unit_id).native_line == "first"
        for wave in waves
    )
