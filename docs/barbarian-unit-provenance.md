# Barbarian Village unit catalog provenance

This catalog covers the **new Barbarian Village land army**, not the retired early-game
Barbarian-Axe Swinger system and not the Barbarian fleet.

## Scope boundary

- The nine units are exposed as a read-only catalog.
- They are **not** inserted into the player `UnitRegistry`.
- `selectable_by_player = false`.
- `simulation_ready = false`.
- NPC formation quantities, wall transitions, target selection, morale, retaliation,
  Workshop behavior and other Barbarian-specific battle rules remain outside this change.

## Sources

1. Gameforge forum Barbarian Village guide:
   https://forum.ikariam.gameforge.com/forum/thread/8492-tutorial-a-vila-dos-b%C3%A1rbaros-6/
   - identifies nine Barbarian land-unit types;
   - documents battlefield line roles and appearance levels;
   - gives player-unit equivalences.

2. Official Infinite Horizons Milestone 2 changelog:
   https://forum.ikariam.gameforge.com/forum/thread/107634-infinite-horizons-milestone-2/
   - states that the basic stats of all units were increased.

3. Infinite Horizons player-test discussion:
   https://forum.ikariam.gameforge.com/forum/thread/107659-infinite-horizons-2/?pageNo=4
   - documents the x20 unit-stat scaling with the Hoplite example
     56 HP / 1 armour / 18 damage -> 1120 / 20 / 360.

4. 2026 Gameforge forum battle analysis:
   https://forum.ikariam.gameforge.com/forum/thread/107659-infinite-horizons-2/?pageNo=45
   - directly reports current Barbarian Knifeman HP = 360.

5. Archived Barbarian guide mirror:
   https://static.s123-cdn-static-d.com/uploads/4367622/normal_60b2770c74e23.pdf
   - records player-unit equivalences and exceptions, including Clubman HP/damage,
     Axe Thrower ammunition, Catapult ammunition, and Barbarian Ram core stats.

## Current catalog

| Unit | Line | First level | Current catalog HP / armour / damage | Accuracy | Ammo | Size | Derivation |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| Barbarian Clubman | Front | 1 | 240 / 0 / 100 | 70 | — | 1 | Spearman equivalence; documented old exceptions 12 HP vs 13 and 5 damage vs 4, then x20 |
| Barbarian Ram | Artillery | 10 | 1400 / 20 / 2100 | 10 | — | 5 | old HP 70 and damage 105 scaled x20; accuracy directly documented; armour/size from Ram equivalence |
| Barbarian Axe Swinger | Front | 20 | 1120 / 20 / 360 | 90 | — | 1 | Hoplite equivalence |
| Barbarian Knifeman | Flank | 30 | 360 / 0 / 200 | 90 | — | 1 | Swordsman equivalence; HP 360 independently observed in 2026 |
| Barbarian Axe Thrower | Long range | 40* | 320 / 0 / 100 | 40 | 7 | 1 | Archer equivalence except ammo 7 instead of 3 |
| Barbarian Catapult | Artillery | 40 | 640 / 0 / 5400 | 10 | 5 | 5 | Mortar equivalence except ammo 5 instead of 3 |
| Barbarian War Walker | Front | 50 | 3680 / 60 / 840 | 80 | — | 3 | Steam Giant equivalence |
| Barbarian Dirigible | Air bomber | 50 | 800 / 0 / 960 | 20 | 2 | 2 | Balloon-Bombardier equivalence |
| Barbarian Fighter | Air defense | 50 | 580 / 0 / 340 | 80 | 4 | 1 | Gyrocopter equivalence |

`—` means the equivalent current player-unit profile has no finite ammunition pool.

### Axe Thrower appearance-level conflict

The Gameforge guide's level-by-level narrative introduces the second-line Axe Thrower
at level 40, and the archived guide also lists Level 40–50. A separate unit-summary line
on the same Gameforge guide says level 30. The catalog therefore uses **40** while keeping
the conflict explicit instead of silently treating the source as unanimous.

## Confidence model

The JSON stores a `provenance.confidence` string per unit. Current numbers can be:

- directly corroborated in current battle discussion;
- derived from a documented player-unit equivalence;
- derived from pre-Infinite-Horizons values using the documented x20 scaling;
- or a combination of these.

These labels are intentionally more conservative than `numerically_supported` in the
player-unit registry. They do **not** mean that Barbarian combat mechanics are calibrated.
