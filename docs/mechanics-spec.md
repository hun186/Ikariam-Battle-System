# Mechanics and current-data evidence register

The simulator combines **legacy empirical mechanics** with **current numerical profiles**, subject to calibration. The repository PDF is a-posteriori research, not Gameforge source code. Current values supplied by PR review remain explicitly network-unverified.

## Evidence classes

`OFFICIAL_CHANGELOG`, `OFFICIAL_FORUM_TEST_REPORT`, `COMMUNITY_TESTED`, `COMMUNITY_REFERENCE`, `EMPIRICAL_PAPER`, `REVIEW_SUPPLIED`, `DERIVED`, `HYPOTHESIS`, and `UNKNOWN` are distinct. `REVIEW_SUPPLIED_OFFICIAL_CHANGELOG_CLAIM` records what review says an official changelog contains; it is not upgraded to `OFFICIAL_CHANGELOG` until the source is retrieved.

## Profile bundle

| Profile | Responsibility | Verification |
| --- | --- | --- |
| `battle-system-paper-2020` | formation labels, Am, RR, observational SR/IR/kill taxonomy | `EMPIRICAL_PAPER`; current applicability requires calibration |
| `infinite-horizons-current` | HP, damage, armor, ammo, weapon/domain/role metadata | review-supplied target through 17.5.0 / 2026-09; network unverified |
| `v14-workshop` | land +5 and naval +10 per level | exact increments review-supplied community/PTS-tested |
| `v14-hephaistos` | forge level effects | exact table review-supplied community/PTS-tested |
| `v17-support-healing` | legacy 200, official-claim ×20, derived 4000 | absolute current capacity `DERIVED`; allocation `UNKNOWN` |

## Source matrix

| Feature | Source class | Simulator treatment |
| --- | --- | --- |
| Am, standard renumbering, RR | EMPIRICAL_PAPER | implemented and regression tested |
| SR, IR, partial line chronology | EMPIRICAL_PAPER | observed, trigger/generalization unknown |
| Kill-type selection | UNKNOWN | strict stops; experimental `EXP-I-KILL-001` |
| Infinite Horizons candidate stats | REVIEW_SUPPLIED | field-level provenance; cross-check required |
| v14 Workshop factor ×5 | REVIEW_SUPPLIED_OFFICIAL_CHANGELOG_CLAIM | metadata only |
| Workshop land +5 / naval +10 | REVIEW_SUPPLIED_COMMUNITY_PTS_TESTED | versioned profile |
| v14 Forge changed damage/armor | REVIEW_SUPPLIED_OFFICIAL_CHANGELOG_CLAIM | metadata only |
| Forge exact levels | REVIEW_SUPPLIED_COMMUNITY_PTS_TESTED | versioned profile |
| v17 Doctor/Tender ×20 | REVIEW_SUPPLIED_OFFICIAL_CHANGELOG_CLAIM | versioned multiplier |
| legacy Doctor/Tender 200 | LEGACY_COMMUNITY_AND_EMPIRICAL_PAPER | retained as legacy input |
| current support 4000 | DERIVED (`200 × 20`) | capacity metadata only |
| v17.4 support garrison exclusion | REVIEW_SUPPLIED_OFFICIAL_CHANGELOG_CLAIM | metadata; not casualty logic |

## Formation semantics

A slot has a stable `slot_id`, `line`, `physical_position`, and `damage_position`. For a full first/second line, physical left-to-right labels are `[6,4,2,1,3,5,7]`; damage and deployment priority are ascending `[1,2,3,4,5,6,7]`. Third `[5,3,1,2,4]`, flank halves `[6,4,2]` and `[1,3,5]`, balloons `[1,2]`, and anti-balloon `[2,1]` are physical layouts—not priority lists. Am mathematics targets damage positions; vector export alone uses physical order. RR integer remainder also follows damage priority.

Only the smallest first-line three-slot fact has direct paper support. Other `small-land` line counts/capacities are review-supplied calibration geometry and must not be described as documented. The registry stores unit `size`; it does not treat worked-example slot capacity as a unit stat. Until authoritative sizes/slot sizes are available, geometry owns calibration capacities.

## Implemented and unresolved mechanics

| Rule | Confidence | Behavior |
| --- | --- | --- |
| Am row modulo target damage positions | EMPIRICAL_PAPER | implemented; steam `[0,7,7,7,7,7,0]`, catapult `[7,7,7,14,7,7,7]` |
| RR `ds=D/N*s`, per wave | EMPIRICAL_PAPER | implemented; deployed + reserve damage conserved |
| Damage components | profile data | fully traced before explicit rounding |
| General rounding selector | UNKNOWN | strict stops; experimental floor is named |
| Casualty/kill selector | UNKNOWN | strict stops; experimental pooled I-kill named |
| Full chronology | UNKNOWN | strict stops; experimental simultaneous phase-start snapshot named |
| Ammo | profile data | primary ammo consumed once/round; after exhaustion no silent primary/secondary fire |
| Secondary-weapon trigger | UNKNOWN | weapon is represented but never silently selected |
| Mixed-unit Am rows | UNKNOWN | rejected as inconclusive; input ordering is never a rule |
| Slot/line retargeting | UNKNOWN | experimental no-retarget assumption; no `next()`-based transfer |
| Healing allocation/timing/eligibility | UNKNOWN | support never enters Am; strict stops, experimental applies no healing and declares it |
| Accuracy, non-standard renumbering, duration intervals | HYPOTHESIS/UNKNOWN | not fabricated |

## Experimental policies

Every experimental response emits applicable IDs in `assumptions` and `assumption_applied` events: `EXP-I-KILL-001`, `EXP-ROUND-FLOOR-001`, `EXP-CHRONOLOGY-001`, `EXP-RETARGET-NONE-001`, `EXP-RR-ROUND-NEAREST-001`, `EXP-AMMO-STOP-001`, and, when support is present, `EXP-HEAL-NONE-001`.

## Calibration fixtures

`ikariam_battle.calibration.BattleReportFixture` accepts game version, complete scenario/profile controls, round number, and observed slot casualties, damage percentage, and life percentage. Damage-percent observations map to integer intervals because displayed damage rounds up; life percentages can be retained separately for later inverse calibration. Fixtures compare replay with observations—they do not hard-code a winner.
